# Written by Carlos Talbot
# This script will expire backups for VMs in a given policy.
# TO execute you need to pass the following parameters:
# 
# python3 expire_by_policy.py -u<username> -p<password> -j<policy name> -s<controller IP/DNS> [-dTrue] [-nTrue]
#
# The last two parameters are optional. The first (-dTrue) will do a dry run through the VMs without expiring backups.
# The second (-nTrue) will delete Nutanix snapshots in addition to backups.
#
# 2022/08/26 Initial release
#

import datetime
import sys
import urllib.parse
import requests
import argparse
from requests.exceptions import Timeout

# Avoid security exceptions/warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# this function returns the results of a REST call with the entities section of the JSON data
# in one or more records
def huRestEnt(server, url, timeout, pagesize, returnRaw=False, maxitems=None):

    items = []
    pageNumber = 1
    while True:
        requestUrl = "https://%s:8443/rest/v1.0/%spageSize=%d&pageNumber=%d" %(server, url, pagesize, pageNumber)
        # make sure spaces, # and other special characters are encoded
        parseURL = urllib.parse.quote(requestUrl, safe=":/&?=")
        try:
            response = requests.get(parseURL,auth=(username,password), cert="",timeout=timeout,verify=False)
        except Exception as e:
            print('Timeout has been raised reaching ' + server)
            print(e)
            return
        if response.status_code == 401:
            print('Status:', response.status_code, 'Invalid username or password for controller ' + server)
            return                              
        if response.status_code != 200:
            print('Status:', response.status_code, 'Failed to retrieve REST results. Exiting.')
            exit(response.status_code)

        if returnRaw == True:
            return response
        
        data = response.json()
        items += data['entities']
        pagesize = (data['metadata']['pageSize'])

        # Exit the loop if we retrieved all of the items
        if len(items) == (data['metadata']['totalEntityCount']):
            break
        if (maxitems != None) and maxitems < len(items):
            break
        pageNumber += 1

    return items

# Submit REST Delete
def huDelete(server, url):
    header = {
       'Content-Type': 'application/json',
       'Accept': 'application/json, text/plain, */*'
    }
    requestUrl = "https://%s:8443/rest/v1.0/%s" %(server, url)
    ret=requests.delete(requestUrl,auth=(username,password), cert="", headers=header, verify=False, timeout=None)
    return ret.json()

def main(argv):
    global username
    global password

    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-s", "--server", help="HYCU controller IP/DNS name", required=True)
    myParser.add_argument("-j", "--policy", help="Policy to expire backups from", required=True)    
    myParser.add_argument("-d", "--dryrun", help="Advanced: True = just list which VMs will be expired", required=False)
    myParser.add_argument("-n", "--nutanix", help="Advanced: True = also delete Nutanix snapshosts", required=False)

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    policy=args.policy
    server=args.server
    nutanix_snaps=args.nutanix
    dryrun=None if not args.dryrun else (args.dryrun)

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    # find policy UUID
    endpoint = "policies?filter=name##" + policy + "&"
    data=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

    if not data:
        # can't find policy, exit
        print ("Can't find policy " + policy)            
        exit(1)

    policy_uuid = data[0]['uuid']
    print ("Policy name is " + policy + ", UUID is " + policy_uuid)

    # list all VMs
    endpoint = "vms?"
    vm_list=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

    if not vm_list:
        # can't find VMs, exit
        print ("Can't find VMs")            
        exit(1)

    if dryrun:
        print("#############  Skipping deletion, dry run #############")
    start_time = datetime.datetime.now()
    print("Current Time =", start_time)

    # Loop through VM list and pick out ones that are part of policy
    for vm in vm_list:
        if (vm['protectionGroupUuid'] == policy_uuid):
            vm_uuid = vm['uuid']
            vm_name = vm['vmName']
            vm_type = vm['externalHypervisorType']
            # type can be vSphere, KVM or VMware

            print ("vm name " + vm_name)
            print ("Hypervisor type " + vm_type)

            # get all backups for VM
            endpoint = "vms/" + vm_uuid + "/backups?"
            backup_list=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

            print("Erasing backups for VM - " + vm_name)
            # go through each backup (full or incremental) for a VM and delete them
            for vm_backup in backup_list:
                backup_uuid=vm_backup['uuid']
                backup_type=vm_backup['type']
                print (backup_uuid + " type " + backup_type)

                if not dryrun:
                    endpoint = "vms/%s/backup/%s?type=BACKUP_AND_COPY" %(vm_uuid, backup_uuid)
                    # Submit RESTful DELETE command
                    ret=huDelete(server, endpoint)
                    print (ret['message']['titleDescriptionEn'])                

            # are we deleting nutanix snapshots too?
            if nutanix_snaps:
                # Check if VM is on a Nutanix cluster
                if (vm_type == "KVM" or vm_type == "VMware"):
                    print("Erasing snapshots for VM - " + vm_name)
                    # get all snapshots for VM
                    endpoint = "vms/" + vm_uuid + "/snapshots?"
                    snapshot_list=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

                    # go through each snapshot for a VM and delete them
                    for vm_snapshot in snapshot_list:
                        snapshot_uuid=vm_snapshot['uuid']
                        print ("Snapshot " + snapshot_uuid)

                        if not dryrun:
                            endpoint = "vms/%s/backup/%s?type=SNAPSHOT" %(vm_uuid, snapshot_uuid)
                            # Submit RESTful DELETE command
                            ret=huDelete(server, endpoint)
                            print (ret['message']['titleDescriptionEn'])                

            print()

    end_time = datetime.datetime.now()
    print("Current Time =", end_time)
    print("Time elapsed in seconds =", end_time - start_time)    
    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

# Written by Carlos Talbot
# This script will add a VM to a given policy.
# To execute you need to pass the following parameters:
# 
# python3 assign_vm_to_policy.py -u<username> -p<password> -s<controller IP/DNS> -j<policy name> -v<VM NAME> [-b=True]
# The last parameter is optional and will trigger a backup of the VM.
# 
# 2022/11/1 Initial release

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

def huAssignVm(vmUUID, policyUUID, server, username, password, timeout):
    # Prepare the HTTP get request
    options = '{ "vmUuidList": ["%s"] }' %(vmUUID)


#    options = '{ "restoreSource": "AUTO"}'
    
        #endpoint = "policies/" + policy_uuid + "/assign?"

    requestUrl = "https://%s:8443/rest/v1.0/policies/%s/assign" %(server, policyUUID)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*'
    }
    response = requests.post(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, data=options, timeout=timeout)
    if response.status_code not in [200,201,202]:
        print('Status:', response.status_code, 'Failed to assign VM to policy.\n\nDetailed API response:' )
        print(response.text)
        exit()
    
    return response.json()

def backupVM(vmUUID, server, username, password, timeout):
    # Prepare the HTTP get request
    #options = '{ uuidList: ["%s"], "forceFull": false }' %(vmUUID)

    options = '{ "uuidList": ["%s"], "forceFull": "false" }'  %(vmUUID)   

    requestUrl = "https://%s:8443/rest/v1.0/schedules/backup" %(server)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*'
    }
    response = requests.post(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, data=options, timeout=timeout)
    if response.status_code not in [200,201,202]:
        print('Status:', response.status_code, 'Failed to assign VM to policy.\n\nDetailed API response:' )
        print(response.text)
        exit()
    
    return response.json()    

def main(argv):
    global username
    global password

    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-s", "--server", help="HYCU controller IP/DNS name", required=True)
    myParser.add_argument("-j", "--policy", help="Policy name", required=True)    
    myParser.add_argument("-v", "--vm", help="VM to add to policy", required=True)    
    myParser.add_argument("-b", "--backup", help="Trigger a backup after assigning to policy", required=False)    

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    policy=args.policy
    server=args.server
    vm_name=args.vm
    backup_vm=args.backup

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

    # find VM
    endpoint = "vms?filter=vmName##" + vm_name + "&"    
#    endpoint = "vms?"
    vm_data=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

    if not vm_data:
        # can't find VM, exit
        print ("Can't find VM " + vm_name)            
        exit(1)

    vm_uuid=vm_data[0]['uuid']
    ret=huAssignVm(vm_uuid, policy_uuid, server, username, password, timeout=300)
    print ("Assigned " + vm_name + "to policy " + policy)

    if backup_vm:
        ret=backupVM(vm_uuid, server, username, password, timeout=300)
        print ("Initiated backup of " + vm_name)

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

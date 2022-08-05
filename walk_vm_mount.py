# Written by Carlos Talbot (carlos.talbot@hycu.com)
# The following script will mount the most recent bacukp image for a given VM and walk the directory tree

# Written by Carlos Talbot (carlos.talbot@hycu.com)
# The following script will search backups of a VM for a key file within
# all the subdirectories of the VM.

import sys
import argparse
import this
import requests
import time
import datetime

# Avoid security exceptions/warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sleep_wait=2 # seconds to to wait for job execution

def huFindItemByValue(items, propName, propValue):
    for key in items:
        if items[key][propName] == propValue:
            return items[key]
    return None

def huRestGeneric(url, timeout, pagesize, returnRaw=False, maxitems=None):
    if pagesize > 0:
        items = []
        pageNumber = 1
        while True:
            requestUrl = "https://%s:8443/rest/v1.0/%spageSize=%d&pageNumber=%d" %(server, url, pagesize, pageNumber)
            response = requests.get(requestUrl,auth=(username,password), cert="",timeout=timeout,verify=False)
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
    else:
        requestUrl = "https://%s:8443/rest/v1.0/%s" %(server, url)
        response = requests.get(requestUrl,auth=(username,password), cert="",timeout=timeout,verify=False)
        if response.status_code != 200:
            print('Status:', response.status_code, 'Failed to retrieve REST results. Exiting.')
            exit(response.status_code)
        data = response.json()
        items = data['entities']
    return items

def huGetVMs(timeout, pagesize):
    """ Retrieves VM list and return a dictionary """
    dict = {}
    endpoint = "vms?forceSync=false&"

    data = huRestGeneric(endpoint, timeout, pagesize)
    for item in data:
        dict[item['uuid']] = item
    return dict

# check state of running job
def huGetJobStatus(jobUuid, timeout):
    """ Retrieves Job status """
    endpoint = "jobs/%s?" %(jobUuid)

    data = huRestGeneric(endpoint, timeout, 1)
    return data[0]['status']

# retrive all backups for a given VM
def huGetVMBackups(ntimeout, pageSize, vmuuid):
    endpoint = "vms/" + vmuuid + "/backups?orderBy=-restorePointInMillis&"
 
    data = huRestGeneric(endpoint, ntimeout, pageSize)
    return data

# check to see if VM mount is active
def huCheckMount(ntimeout, pageSize, vmuuid, backup_uuid):
    endpoint = "vms/" + vmuuid + "/backups/" + backup_uuid + "/mount?restoreSource=AUTO&"

    data = huRestGeneric(endpoint, ntimeout, pageSize)
    return data


# mount VM backup, wait for job to complete
def huMountBackup(timeout, vmuuid, backup_uuid):
    options = '{ "restoreSource": "AUTO"}'    

    requestUrl = "https://%s:8443/rest/v1.0/vms/%s/backups/%s/mount" %(server, vmuuid, backup_uuid)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*'
    }
    response = requests.post(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, data=options, timeout=timeout)
    if response.status_code not in [200,201,202]:
        print('Status:', response.status_code, 'Failed to mount backup with uuid %s.\n\nDetailed API response:' %(backup_uuid))
        print(response.text)
        exit()
    
    result=response.json()

    jobUuid = result['entities'][0]
    if jobUuid:
        status = 'EXECUTING';
        while status == 'EXECUTING':
            time.sleep (1)
            status = huGetJobStatus(server, username, password, jobUuid, timeout=timeout)
            print('Job status - %s' %(status))

        print('Job complete. Status: %s\n' %(status))
    else:
        print ("trouble mounting backup!")
        exit(1)    

    return result

# unmount VM backup, wait for job to complete
def huUnmountBackup(timeout, vmuuid, backup_uuid):
    #options = '{ "restoreSource": "AUTO"}'    

    requestUrl = "https://%s:8443/rest/v1.0/vms/%s/backups/%s/mount" %(server, vmuuid, backup_uuid)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*'
    }
    response = requests.delete(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, timeout=timeout)
    if response.status_code not in [200,201,202]:
        print('Status:', response.status_code, 'Failed to unmount backup with uuid %s.\n\nDetailed API response:' %(backup_uuid))
        print(response.text)
        exit()

    result=response.json()
    jobUuid = result['entities'][0]
 
    if jobUuid:
        status = 'EXECUTING';
        while status == 'EXECUTING':
            time.sleep (1)
            status = huGetJobStatus(server, username, password, jobUuid, timeout=timeout)
            print('Job status - %s' %(status))

        print('Job complete. Status: %s\n' %(status))
    else:
        print ("trouble unmounting backup!")
        exit(1)

    return result

# Retrieve the list of VMs from HYCU Rest API server (page by page)
def huFindVM(vmname, ntimeout, pageSize):
    vms = huGetVMs(ntimeout, pageSize)

    # Check if the given VM name is valid
    vm = huFindItemByValue(vms, 'vmName', vmname)
    if (vm == None):
        print('Status:', 'Cannot find VM "%s" in the list of HYCU VMs' %(args.vm))
        exit(1)

    print ("VM " + vm['vmName'] + " found. VM UUID is " + vm['uuid'])
    return vm

def huBrowseMount(mount_uuid, mountpath):
    endpoint = "mounts/" + mount_uuid + "/browse?filter=subType==2&orderBy=displayName&path=" + mountpath + "&"
    data = huRestGeneric(endpoint, timeout=100, pagesize=0)

    endpoint = "mounts/" + mount_uuid + "/browse?path=" + mountpath + "&"
    data = huRestGeneric(endpoint, timeout=100, pagesize=50)

    print ("Current directory " + mountpath)
    for i in data:
#        print (i['fullItemName'])
        # subtypes:
        # type 1: file
        # type 2: directory
        # type 9: symlink
        # type 10: symlink
        subType=i['subType']
        if subType == 1:
            print (i['displayName'])
        elif subType == 2 and i['displayName'] != "lost+found" :
            huBrowseMount(mount_uuid, mountpath + i['displayName'] + "/")

def main(argv):
    # Parse command line parameters VM and/or status
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-s", "--server", help="HYCU Server IP", required=True)
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-v", "--vm", help="VM to be searched up", required=True)    
    myParser.add_argument("-f", "--filename", help="filename to search", required=True)
    myParser.add_argument("-sf", "--statusfilter", choices=['EXECUTING', 'OK', 'WARNING', 'ERROR', 'FATAL', 'QUEUED', 'ABORTED'], help="Filter jobs", required=False)
    myParser.add_argument("-i", "--timeout", help="Advanced: REST Query timeout [default=5]", required=False)
    myParser.add_argument("-z", "--pagesize", help="Advanced: REST Query pagesize [default=None]", required=False)

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    args = myParser.parse_args(argv)

    global username
    global password
    global server
    username=args.username
    password=args.password
    server=args.server

    # REST call intializations
    nTimeout = 5 if not args.timeout else int(args.timeout)
    pageSize = None if not args.pagesize else int(args.pagesize)

    now = datetime.datetime.now()
    print("Current Time =", now)

    vm = huFindVM(args.vm, nTimeout, pageSize)

    # retrieve all backups for VM
    vmbackups = huGetVMBackups(nTimeout, pageSize, vm['uuid'])
    
    if not vmbackups:
        print ("No backups found!")
        exit (10)

    # get backup time from most recent backup
    backup_time = ((vmbackups[0]['restorePointInMillis']+500)/1000)
    backup_str = datetime.datetime.fromtimestamp(backup_time).strftime('%c')
    print ("Searching " + vmbackups[0]['type'] + " from " + backup_str + " on " + vmbackups[0]['primaryTargetName'])

    # check if VM has any mounts currently
    mount_state = huCheckMount(nTimeout, pageSize, vm['uuid'], vmbackups[0]['uuid'])
    if not mount_state[0]['mounted']:
        print (vm['vmName'] + " is not MOUNTED...mounting..")
        mount_data = huMountBackup(nTimeout, vm['uuid'], vmbackups[0]['uuid'])
        if not mount_data['entities'][0]:
            print ("Mount error!")
            exit(1)
        mount_uuid=mount_data['entities'][0]        
    else:
        print (vm['vmName'] + " is MOUNTED, resuing MountID....")
        mount_uuid=mount_state[0]['mountUuid']


    results = huBrowseMount(mount_uuid,"")

    #unmont bacup before exiting
#        mount_data = huUnmountBackup(args.server, args.username, args.password, nTimeout, vm['uuid'], vmbackups[0]['uuid'])

    now = datetime.datetime.now()
    print("Current Time =", now)

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

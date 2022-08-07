# Written by Carlos Talbot (carlos.talbot@hycu.com)
# The following script index backups for a VM to a specified mongodb.
# You can run the script using the following syntax:
#
# python index_backups.py -s<HYCU CTRL> -u<USERNAME> -p<PASSWORD> -v<VMNAME> -m<MONGODB CONN>
#
# For example python index_backups.py -s192.168.1.8 -uadmin -padmin -vEXCHANGE -m"mongodb://192.168.1.106:27017"
#
# You can use grub.cfg as a filename to search for within a Linux VM as the grub volume is searched early in the mount process
# For Windows you can use desktop.ini

from http import client
from sqlite3 import dbapi2
import sys
import argparse
import this
import requests
import time
import datetime
import urllib.parse

from pymongo import MongoClient
from pprint import pprint

# Avoid security exceptions/warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
            # make sure spaces, # and other special characters are encoded
            parseURL = urllib.parse.quote(requestUrl, safe=":/&?=")
            response = requests.get(parseURL,auth=(username,password), cert="",timeout=timeout,verify=False)
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
        # make sure spaces, # and other special characters are encoded
        parseURL = urllib.parse.quote(requestUrl, safe=":/&?=")
        response = requests.get(parseURL,auth=(username,password), cert="",timeout=timeout,verify=False)
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

# populate MongoDB with latest VM backup list
def hUpdateVMBackups(ntimeout, pageSize):
    # first drop exitsing backup collection (table)
    hycucol = hycudb["backups"]
    hycucol.drop()

    endpoint = "vms/backups?"

    data = huRestGeneric(endpoint, ntimeout, pageSize)
    for item in data:
        result=hycudb.backups.insert_one(item)   

# populate MongoDB with latest VM list
def hUpdateVMs(ntimeout, pageSize):
    # first drop exitsing VM collection (table)
    hycucol = hycudb["vms"]
    hycucol.drop()
    
    endpoint = "vms?"

    data = huRestGeneric(endpoint, ntimeout, pageSize)
    for item in data:
        result=hycudb.vms.insert_one(item)          

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
            time.sleep (5)
            status = huGetJobStatus(jobUuid, timeout=timeout)
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
            status = huGetJobStatus(jobUuid, timeout=timeout)
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
        print('Status:', 'Cannot find VM "%s" in the list of HYCU VMs' %(vmname))
        exit(1)

    print ("VM " + vm['vmName'] + " found. VM UUID is " + vm['uuid'])
    return vm

def huBrowseMount(mountpath):
#    endpoint = "mounts/" + mount_uuid + "/browse?filter=subType==2&orderBy=displayName&path=" + mountpath + "&"
#    data = huRestGeneric(endpoint, timeout=100, pagesize=0)

    endpoint = "mounts/" + mount_uuid + "/browse?path=" + mountpath + "&"
    data = huRestGeneric(endpoint, timeout=100, pagesize=50)

# write directory record to MongoDB
    for item in data:
        item.update({"backupUuid":backup_uuid})
        item.update({"vmUuid":vm_uuid})      
        result=hycudb.files.insert_one(item)

    print ("Current directory " + mountpath)
    for i in data:
        # subtypes:
        # type 1: file
        # type 2: Linux & Windows directory
        # type 9: symlink
        # type 10: symlink
        # type 18: Windows Drive
        subType=i['subType']
        if subType == 2 and i['displayName'] != "lost+found"  :
            huBrowseMount(mountpath + i['displayName'] + "/")
        elif subType == 18 and i['displayName'] != "System Reserved":
            huBrowseMount(mountpath + i['fullItemName'] + "/")

def main(argv):
    global username
    global password
    global server
    global search_file
    global mount_uuid
    global client
    global hycudb
    global backup_uuid
    global vm_uuid

    # A lot of global definitions in order to reduce variables on the stack during recurvise call
    # to browse the directory tree

    # Parse command line parameters VM and/or status
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-s", "--server", help="HYCU Server IP", required=True)
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-v", "--vm", help="VM to be searched up", required=True)    
    myParser.add_argument("-m", "--mongodb", help="Connection string to Mongodb", required=True)
    myParser.add_argument("-sf", "--statusfilter", choices=['EXECUTING', 'OK', 'WARNING', 'ERROR', 'FATAL', 'QUEUED', 'ABORTED'], help="Filter jobs", required=False)
    myParser.add_argument("-i", "--timeout", help="Advanced: REST Query timeout [default=5]", required=False)
    myParser.add_argument("-z", "--pagesize", help="Advanced: REST Query pagesize [default=None]", required=False)

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    server=args.server
  
    # REST call intializations
    nTimeout = 5 if not args.timeout else int(args.timeout)
    pageSize = 50 if not args.pagesize else int(args.pagesize)

# connect to MongoDB, change the << MONGODB URL >> to reflect your own connection string
    client = MongoClient(args.mongodb)
    hycudb=client.hycu

    #refersh VM backups list in MongoDB with latest
    hUpdateVMBackups(nTimeout, pageSize)
    #refersh VM list in MongoDB with latest
    hUpdateVMs(nTimeout, pageSize)    

    start_time = datetime.datetime.now()
    print("Current Time =", start_time)

    vm = huFindVM(args.vm, nTimeout, pageSize)

    # retrieve all backups for VM
    vmbackups = huGetVMBackups(nTimeout, pageSize, vm['uuid'])
    # save this UUID to store with files in DB
    vm_uuid=vm['uuid']
    
    if not vmbackups:
        print ("No backups found!")
        exit (1)
    # save this UUID to store with files in DB
    backup_uuid=vmbackups[0]['uuid']
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
        # grab mount id from checkmount
        mount_state = huCheckMount(nTimeout, pageSize, vm['uuid'], vmbackups[0]['uuid'])
        mount_uuid=mount_state[0]['mountUuid']        
    else:
        print (vm['vmName'] + " is MOUNTED, resuing MountID....")
        mount_uuid=mount_state[0]['mountUuid']

    # Time to walk the tree!
    results = huBrowseMount("")

    #unmount backup before exiting
    mount_data = huUnmountBackup(nTimeout, vm['uuid'], vmbackups[0]['uuid'])

    end_time = datetime.datetime.now()
    print("Current Time =", end_time)
    print("Time elapsed in seconds =", end_time - start_time)

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

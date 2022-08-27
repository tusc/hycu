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
# 2022/08/07 Initial release
# 2022/08/27 Updated to include snapshot as source

from http import client
#from sqlite3 import dbapi2
from pickle import TRUE
#from pickle import FALSE
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

def huRestGeneric(url, timeout, pagesize, returnRaw=False, maxitems=None):
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

# retrive all backups or snapshots for a given VM
def huGetVMImages(mounttype, ntimeout, pageSize, vmuuid):
    endpoint = "vms/" + vmuuid + "/" + mounttype + "?"
 
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

def huExpireOldFiles():
    hycucol_backups = hycudb["backups"]
    hycucol_files = hycudb["files"]

    # return all active unique backup UUIDs from the backups table
    backup_uuids = hycucol_backups.distinct('uuid')

    print("before uuid remove")
    col_count=hycucol_files.count_documents( {'backupUuid': {'$nin': backup_uuids}} )
    #if 
    #print ())
    print("after uuid remove")    
    # backup_uuids.remove("05fc727b-3277-4efe-bc10-a3e3d323a289")
    print (hycucol_files.count_documents( {'backupUuid': {'$nin': backup_uuids}} ))

    rec_count=hycucol_files.count_documents( {'backupUuid': {'$nin': backup_uuids}})
    print(f'removing {rec_count} records')

    # Remove all file records that belonged to an EXPIRED backup restore point
    # (i.e. backup UUID no longer in backups table)
    # We use the Python keyword $nin below to denote NOT IN. So return all file records with
    # a backup UUID NOT IN the Python list from above.
#    hycucol_files.remove( {'backupUuid': {'$nin': backup_uuids}})

# check to see if VM mount is active
def huCheckMount(mounttype,ntimeout, pageSize, vmuuid, backup_uuid):
# mountype can be backups or snapshots
    endpoint = "vms/" + vmuuid + "/" + mounttype + "/" + backup_uuid + "/mount?restoreSource=AUTO&"
    data = huRestGeneric(endpoint, ntimeout, pageSize)
    return data

# mount VM backup/snapshot, wait for job to complete
def huMount(mounttype, timeout, vmuuid, backup_uuid):
    options = '{ "restoreSource": "AUTO"}'    

    requestUrl = "https://%s:8443/rest/v1.0/vms/%s/%s/%s/mount" %(server, vmuuid, mounttype, backup_uuid)

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

# unmount VM backup/snapshot, wait for job to complete
def huUnmount(mounttype, timeout, vmuuid, backup_uuid):
    #options = '{ "restoreSource": "AUTO"}'    

    requestUrl = "https://%s:8443/rest/v1.0/vms/%s/%s/%s/mount" %(server, vmuuid, mounttype, backup_uuid)

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
    myParser.add_argument("-r", "--refresh", help="Advanced: refresh MongoDB [Default=False]", required=False)    

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    server=args.server
  
    # REST call intializations
    nTimeout = 60
    pageSize = 50
    refresh_db=None if not args.refresh else (args.refresh)

    # connect to MongoDB, change the << MONGODB URL >> to reflect your own connection string
    client = MongoClient(args.mongodb)
    hycudb=client.hycu

    if refresh_db:
        #refersh VM backups list in MongoDB with latest
        print("Please wait updating VM Backup list...")
        hUpdateVMBackups(nTimeout, pageSize)
        print("Please wait updating VM list...")
        #refersh VM list in MongoDB with latest
        hUpdateVMs(nTimeout, pageSize)    

        # expire old file entries in database
#        huExpireOldFiles()

    start_time = datetime.datetime.now()
    print("Current Time =", start_time)

    # find VM
    endpoint = "vms?filter=vmName##" + args.vm + "&"    
    vm=huRestGeneric(endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)
    if not vm:
        # can't find VM, exit
        print ("Can't find VM " + vm_name)            
        exit(1)

    vm_uuid=vm[0]['uuid']
    vm_type = vm[0]['externalHypervisorType']

    use_snap = None
    # Check to see if VM is on Nutanix, if so then try to retrive snapshot and use for mount.
    # Otherwise fall back to backup as source of mount.
    if (vm_type == "KVM" or vm_type == "VMware"):
        vmbackups = huGetVMImages("snapshots",nTimeout, pageSize, vm_uuid)
        if not vmbackups:
            # no snapshots available, use backup image as mount source
            vmbackups = huGetVMImages("backups", pageSize, vm_uuid)
        else:
            # we found a snapshot, will use as mount source
            use_snap = True
    else:
        # vSphere backup, not snapshot available 
        vmbackups = huGetVMImages("backups",nTimeout, pageSize, vm_uuid)

    if not vmbackups:
        print ("No backups found!")
        exit (1)

    if use_snap:
        mount_type="snapshots"
    else:
        mount_type="backups"
        
    # save this backup UUID to store with files in DB
    backup_uuid=vmbackups[0]['uuid']

    if (use_snap):
        # get backup time from most recent backup
        #backup_time = ((vmbackups[0]['restorePointInMillis']+500)/1000)
        #backup_str = datetime.datetime.fromtimestamp(backup_time).strftime('%c')
        print ("Searching snapshot " + backup_uuid)
    else:
        # get backup time from most recent backup
        backup_time = ((vmbackups[0]['restorePointInMillis']+500)/1000)
        backup_str = datetime.datetime.fromtimestamp(backup_time).strftime('%c')
        print ("Searching " + vmbackups[0]['type'] + " from " + backup_str + " on " + vmbackups[0]['primaryTargetName'])

    # check if VM has any mounts currently
    mount_state = huCheckMount(mount_type,nTimeout, pageSize, vm[0]['uuid'], vmbackups[0]['uuid'])
    if not mount_state[0]['mounted']:
        print (vm[0]['vmName'] + " is not MOUNTED...mounting..")
        mount_data = huMount(mount_type,nTimeout, vm[0]['uuid'], vmbackups[0]['uuid'])
        if not mount_data['entities'][0]:
            print ("Mount error!")
            exit(1)
        # grab mount id from checkmount
        mount_state = huCheckMount(mount_type,nTimeout, pageSize, vm[0]['uuid'], vmbackups[0]['uuid'])
        mount_uuid=mount_state[0]['mountUuid']        
    else:
        print (vm[0]['vmName'] + " is MOUNTED, resuing MountID....")
        mount_uuid=mount_state[0]['mountUuid']

    # Time to walk the tree!
    results = huBrowseMount("")

    #unmount backup before exiting
    mount_data = huUnmount(mount_type,nTimeout, vm[0]['uuid'], vmbackups[0]['uuid'])

    end_time = datetime.datetime.now()
    print("Current Time =", end_time)
    print("Time elapsed in seconds =", end_time - start_time)

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

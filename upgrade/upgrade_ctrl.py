# Written by Carlos Talbot
# This script will upgrade HYCU controllers and manager of managers.
# A simple json file is required for storing the IP or DNS name of all the contollers.
# 2022/08/12 Initial release
# 2022/08/13 Add option to specify filename
# 2022/08/18 Update to leverage async post method
# 2022/08/19 Updated to select most recent firmware image and optional dry run flag. Ensure controller is in running state
  
import json
#from datetime import datetime
import datetime
from pickle import TRUE
import sys
import urllib.parse
import requests
import multiprocessing
import time
import argparse
from requests.exceptions import Timeout

# Avoid security exceptions/warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# this function returns the results of a REST call with the entities section of the JSON data
# in one or more records
def huRestEnt(server, url, timeout, pagesize, returnRaw=False, maxitems=None):
    if pagesize > 0:
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
        try:
            response = requests.get(parseURL,auth=(username,password), cert="",timeout=timeout,verify=False)
        except Exception as e:
            print('Timeout has been raised reaching ' + server)
            print(e)
            return   

        if response.status_code != 200:
            print('Status:', response.status_code, 'Failed to retrieve REST results. Exiting.')
            exit(response.status_code)
        data = response.json()
        items = data['entities']
    return items

# this function returns the results of a REST call with the all of the JSON data for one record
def huRestGeneric(server, url, timeout):
    requestUrl = "https://%s:8443/rest/v1.0/%s" %(server, url)
    # make sure spaces, # and other special characters are encoded
    parseURL = urllib.parse.quote(requestUrl, safe=":/&?=")
    try:
        response = requests.get(parseURL,auth=(username,password), cert="",timeout=timeout,verify=False)
    except Exception as e:
        print('Timeout has been raised reaching ' + server)
        print(e)
        return    
    if response.status_code != 200:
        print('Status:', response.status_code, 'Failed to retrieve REST results. Exiting.')
        exit(response.status_code)
    return response.json()

# fuctino to submit POST as a thread via mutliprocess
def request_task(url, headers, username, password):
    # Submit image upgrade request, sit here indefinitely until killed by parent
    # when Controller state is no longer UPGRADING
    ret=requests.post(url,auth=(username,password), cert="", headers=headers, verify=False, timeout=None)

# Submit REST POST via thread asynchrounsly
def async_post(server, url):
    header = {
       'Content-Type': 'application/json',
       'Accept': 'application/json, text/plain, */*'
    }
    requestUrl = "https://%s:8443/rest/v1.0/%s" %(server, url)    
    process = multiprocessing.Process(target=request_task, args=(requestUrl, header, username, password))
    process.start()
    # keep track of newly created thread for later termination
    all_processes.append(process)

def main(argv):
    global username
    global password
    global all_processes
    all_processes = []
    server_list = []

    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-f", "--filename", help="name of JSON file with list of controllers", required=True)
    myParser.add_argument("-d", "--dryrun", help="Advanced: True = just list firmware versions available", required=False)    
    myParser.add_argument("-v", "--version", help="Advanced: specify firmware version [default=most recent]", required=False)

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    filename=args.filename
    version=None if not args.version else (args.version)
    dryrun=None if not args.dryrun else (args.dryrun)

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    # Opening JSON file
    f = open(filename)
    
    # returns JSON object as 
    # a dictionary
    data = json.load(f)
    
    start_time = datetime.datetime.now()
    print("Current Time =", start_time)

    # Loop through all the controller IPs that were read from the json file
    for i in data['ctrl_details']:
        server=i['address']

        # lets find out controller name and what version controller is running.
        endpoint = "administration/controller?"
        data=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)
        if data is None:
            # can't reach controller, go to next on the list            
            continue
        if (data[0]['backupControllerMode'] == 'BC'):
            ctrl_name=data[0]['controllerVmName']
        else:
            ctrl_name="Manager of Managers"            
        print ("Checking " + ctrl_name )
        print ("Controller type: " + data[0]['backupControllerMode'])        
        print ("Running version: " + data[0]['softwareVersion'] + " on this controller")

        print("Checking status of controller " + server)
        endpoint = "administration/controller/state?"
        response = huRestGeneric(server, endpoint, timeout=60)
        state = response['message']['titleDescriptionEn']
        print(state)
        if not ("RUNNING") in state:
            print ("Controller not in running state...skipping..")
            continue

        print("Please wait, checking for upgrade images...")
        endpoint = "upgrade/images?"
        data=huRestEnt(server, endpoint, timeout=60, pagesize=50, returnRaw=False, maxitems=None)

        # Data will be non-empty if there are new images that can be applied
        if (data):
            # -1 below denotes last element on list. This ensures most recent backup image is selected for upgrade
            # unless we pass --version flag to specify a particular version.
            firmware_idx=-1
            j=0
            for ctrl in data:
                if ctrl['name'] == version:
                    firmware_idx=j
                print ("Availabe image: " + ctrl['name'])
                j=j+1

            imageID=data[firmware_idx]['uuid']
            imageName=data[firmware_idx]['name']
            print ("Selected image " + imageName)

            if not dryrun:
                endpoint = "upgrade/%s/%s" %(imageID, imageName)
                # keep track of controller address to check state after upgrade
                server_list.append(server)
                # Submit RESTful POST command via thread and continue onto next controller                
                async_post(server, endpoint)
            else:
                print("Skipping upgrade, dry run...")

        else:
            print ("No upgrade available for this controller")
        print()

    # ensure that at least first contrller is in upgrade mode
    time.sleep(10)
    i=0
    # Loop through all threads until upgrades have completed
    for process in all_processes:
        server = server_list[i]
        print("Checking status of controller " + server)        
        while True:
            endpoint = "administration/controller/state?"
            # Check controller state
            response = huRestGeneric(server, endpoint, timeout=120)
            if response is None:
                # we hit a REST get timeout during VM shutdown/startup
                # retry
                print("Server in middle of shutdown/startup...retrying")
                time.sleep(5)
                continue
            state = response['message']['titleDescriptionEn']
            print(state)
            if not ("UPGRADING") in state:            
                # Controller state can be UPGRADING, STARTING or RUNNING
                # If state is the latter two than upgrade has completed, time to kill thread
                # and move onto the next controller
                print("killing thread for controller " + server)
                process.terminate()
                break
            # wait 30 seconds before we check state of controller
            time.sleep(30)             
        i=i+1

    f.close()
    print()
    if not dryrun:
        print("Upgrades have completed")
    end_time = datetime.datetime.now()
    print("Current Time =", end_time)
    print("Time elapsed in seconds =", end_time - start_time)    
    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

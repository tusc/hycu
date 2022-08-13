# Written by Carlos Talbot
# This script will upgrade HYCU controller, filers and managers.
# a simple json file is required for storing the IP addresses of all the contollers
  
import json
from pickle import TRUE
import sys
import urllib.parse
import requests
import threading
import time
import argparse

# Avoid security exceptions/warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def huRestGeneric(server, url, timeout, pagesize, returnRaw=False, maxitems=None):
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


def request_task(url, headers):
    ret=requests.post(url,auth=(username,password), cert="", headers=headers, verify=False, timeout=None)
    return ret

# Submit REST POST via thread asynchrounsly
def async_upgrade(url, headers):
    threading.Thread(target=request_task, args=(url, headers)).start()

# Submit REST POST and wait for return
def nonsync_upgrade(url, headers):
    ret=requests.post(url,auth=(username,password), cert="", headers=headers, verify=False, timeout=None)
    return ret

def main(argv):
    global username
    global password

    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-f", "--filename", help="name of JSON file with list of controllers", required=True)

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    filename=args.filename

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    # Opening JSON file
    f = open(filename)
    
    # returns JSON object as 
    # a dictionary
    data = json.load(f)

    # With async set to true, we do not wait for the restful API POST command and continue on to the next controller.
    async_mode=True
     
    # Loop through all the controller IPs that were read from the json file
    for i in data['ctrl_details']:
        server=i['address']

        # lets find out controller name and what version controller is running.
        endpoint = "administration/controller?"
        data=huRestGeneric(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)
        if (data[0]['backupControllerMode'] == 'BC'):
            ctrl_name=data[0]['controllerVmName']
        else:
            ctrl_name="Manager of Managers"            
        print ("Checking " + ctrl_name )
        print ("Controller type: " + data[0]['backupControllerMode'])        
        print ("Running version: " + data[0]['softwareVersion'] + " on this controller")

        print("Please wait, checking for upgrade images...")
        endpoint = "upgrade/images?"
        data=huRestGeneric(server, endpoint, timeout=60, pagesize=50, returnRaw=False, maxitems=None)

        # Data will be non-empty if there are new images that can be applied
        if (data):
            for i in data:    
                print ("Availabe image: " + i['name'])

            print ("Upgrading...")
            imageID=data[0]['uuid']
            imageName=data[0]['name']
            requestUrl = "https://%s:8443/rest/v1.0/upgrade/%s/%s" %(server, imageID, imageName)
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*'
            }
            if (async_mode):
                # Submit RESTful POST command via thread and continue onto next controller
                async_upgrade(requestUrl, headers)
                time.sleep(5)
            else:
                response = nonsync_upgrade(requestUrl, headers)
                if response.status_code not in [200,201,202]:
                    print('Status:', response.status_code, 'Failed to upgrade controller %s with uuid %s.\n\nDetailed API response:' %(ctrl_name, imageID))
                    print(response.text)
                    exit(1)
        else:
            print ("No upgrade available for this controller")
        print()

    f.close()

    print("Upgrades running in the background. Please hit ctrl-c to break out once all controllers have completed their upgrade.")
    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

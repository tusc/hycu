# Written by Carlos Talbot
# This script will clone a HYCU policy.
# TO execute you need to pass the following parameters:
# 
# python3 clone-policy.py -u<username> -p<password> -s<controller IP/DNS> -o<origianl policy> -n<new policy> [-c<NUMERIC> optional flag to create multiple policies]
#
# For example,
# to create one new policy from original:
# python3 clone-policy.py -uusername -p"MYPASSWORD" -shycuinst -o"Silver" -n"Silver Clone" [-c<NUMERIC> optional flag to create multiple policies]
# 
# to create 5 new polices from original:
# python3 clone-policy.py -uusername -p"MYPASSWORD" -shycuinst -o"Silver" -n"Silver Clone" -c5
#
# 2023/11/4 Initial release

import datetime
import sys
import urllib.parse
import requests
import argparse
import json
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
        requestUrl = "https://%s:8443/rest/v1.0/%s" %(server, url)
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

def create_policy(table, server, timeout):
    # Prepare the HTTP get request
    #options = json.dumps(table)
    options = table    

    requestUrl = "https://%s:8443/rest/v1.0/policies" %(server)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, json=options, timeout=timeout)

    return(response)

def main(argv):
    global username
    global password
 
    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-s", "--server", help="HYCU controller IP/DNS name", required=True)
    myParser.add_argument("-o", "--origpolicy", help="Current policy", required=True)    
    myParser.add_argument("-n", "--newpolicy", help="New policy", required=True)
    myParser.add_argument("-c", "--copies", help="Optional: -c=5 (create 5 new polices)", required=False)        

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    origpolicy=args.origpolicy
    newpolicy=args.newpolicy
    server=args.server
    copies=None if not args.copies else (int(args.copies))    

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    # find cloud account name
    endpoint = "policies?filter=name##" + origpolicy
    data=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

    if not data:
        print("Can't find cloud account " + origpolicy + "!")
        exit (1)
        # retrieve cloud account UUID
#       policy_uuid=data[0]['uuid'] 


    data[0]['name']=newpolicy
    # remove UUID from original policy
    del data[0]['uuid']
    #json_data=json.dumps(data)

    # create only one policy
    if not copies:
        response=create_policy(data[0], server, timeout=5)
        if response.status_code not in [200,201,202]:
            print("Status:", response.status_code, "Failed to create new policy.\n\nDetailed API response:" )
            print(response.text)
            exit(1)
        print("Successfully create new policy " + newpolicy)
    else:
    # create x number of policies
        for x in range(copies):
            data[0]['name']=origpolicy + " " + str(x+1)
            print ("Creating policy " + data[0]['name'])
            response=create_policy(data[0], server, timeout=5)
            if response.status_code not in [200,201,202]:
                print("Status:", response.status_code, "Failed to create new policy.\n\nDetailed API response:" )
                print(response.text)
                exit(1)
    exit()

if __name__ == "__main__":
    main(sys.argv[1:])

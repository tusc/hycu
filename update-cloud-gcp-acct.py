# Written by Carlos Talbot
# This script will update cloud account credentials for GCP.
# TO execute you need to pass the following parameters:
# 
# python3 update-cloud-gcp-acct.py -u<username> -p<password> -f<json file> -a<Cloud account name> -s<controller IP/DNS>
#
# JSON file includes the key from GCP
#
# 2023/10/30 Initial release


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

def validate_account(table, server, timeout):
    # Prepare the HTTP get request
    #options = json.dumps(table)
    options = table    

    requestUrl = "https://%s:8443/rest/v1.0/cloudAccounts/validate" %(server)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, json=options, timeout=timeout)

    return(response)

def update_cloud_account(table, server, account_uuid, timeout):
    # Prepare the HTTP get request
    #options = json.dumps(table)
    options = table    

    requestUrl = "https://%s:8443/rest/v1.0/cloudAccounts/%s" %(server, account_uuid)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.patch(requestUrl,auth=(username,password), cert="", headers=headers, verify=False, json=options, timeout=timeout)
    return (response)

def main(argv):
    global username
    global password
 
    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-s", "--server", help="HYCU controller IP/DNS name", required=True)
    myParser.add_argument("-a", "--account", help="Cloud account name", required=True)    
    myParser.add_argument("-f", "--filename", help="name of JSON file with GCP key info", required=True)    

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    filename=args.filename
    account=args.account
    server=args.server

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    # Open the JSON file
    f = open(filename)
    
    # returns JSON object as a dictionary
    file_data = json.load(f)

    # find cloud account name within HYCU controller
    endpoint = "cloudAccounts?filter=name##" + account
    data=huRestEnt(server, endpoint, timeout=5, pagesize=50, returnRaw=False, maxitems=None)

    if data:
        # retrieve cloud account UUID
       account_uuid=data[0]['uuid'] 
    else:
        print("Can't find cloud account " + account + "!")
        exit (1)

    #  Build the authentication text array that will be sent to HYCU to update cloud account.
    auth_text = {'type': file_data['type'] , 'project_id': file_data['project_id'], 
        'private_key_id': file_data['private_key_id'], 'private_key': file_data['private_key'], 'client_email': file_data['client_email'], 
        'client_id': file_data['client_id'],'auth_uri': file_data['auth_uri'], 'token_uri': file_data['token_uri'], 
        'auth_provider_x509_cert_url': file_data['auth_provider_x509_cert_url'], 'client_x509_cert_url': file_data['client_x509_cert_url'],
        'universe_domain': file_data['universe_domain']                                         
        }
    # Convert authentication text to JSON right away to avoid nested JSON errors later
    account_data=  { "type": "GCP", "name": account , "authenticationText": json.dumps(auth_text) }    

    # check to make sure GCP keys JSON data is valid
    response=validate_account(account_data, server, timeout=5)

    if response.status_code == 409:
        print("Cloud account " + account + " with private key id " + file_data['private_key_id'] + " already exists!")
        exit(1)
    if response.status_code not in [200,201,202]:
        print("Status:", response.status_code, "Failed to validate cloud account.\n\nDetailed API response:" )
        print(response.text)
        exit()

    print("Cloud account " + account + " with private key id " + file_data['private_key_id'] + " is valid, updating")

    # GCP Keys JSON file checks out, update cloud account in HYCU controller
    response=update_cloud_account(account_data, server, account_uuid, timeout=5)    

    if response.status_code not in [200,201,202]:
        print("Status:", response.status_code, "Failed to update cloud account.\n\nDetailed API response:" )
        print(response.text)
        exit(1)

    print("Cloud account " + account + " updated succesfully") 

if __name__ == "__main__":
    main(sys.argv[1:])

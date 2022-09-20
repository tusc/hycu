# Written by Carlos Talbot (carlos.talbot@hycu.com)
# The following script will look for a VM within all protection sets and trigger a backup of that VM
# You can run the script using the following syntax:
#
# gcp_backup_by_vms.py -v<VMNAME> -f<JSON FILE>
#
# For example python3 gcp_backup_by_vm.py -vfinance-dev-deploy -sgcpkeys.json
#
# 2022/09/20 Initial release

import sys
import json
import http
import ssl
from json import JSONDecodeError
import argparse
from google.oauth2 import service_account
from googleapiclient import discovery

REGISTRY_ENDPOINT = 'endpoints.hycu.com'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
CLIENT_ID = '225038073315-sbrhk8s4hgucmhk1hnd2h2t6ofp0ff5g.apps.googleusercontent.com'

def request_id_token(client_id, scopes, request_service_account):
    # Generate credentials
    credentials = service_account.Credentials.from_service_account_file(request_service_account, scopes=scopes)
    iam_credentials = discovery.build('iamcredentials', 'v1',credentials=credentials)
    with open(request_service_account) as f:
        data_file = json.load(f)
    email = data_file["client_email"]
    print("Generating ID token for Service Account '%s'..." % email)
    name = 'projects/-/serviceAccounts/' + email
    generate_id_token_request = {
    'includeEmail': True,
    'audience': client_id
    }
    request = iam_credentials.projects().serviceAccounts().generateIdToken(name=name, body=generate_id_token_request)
    response_generate_id_token = request.execute()
    return "Bearer %s" % response_generate_id_token["token"]

def get_manager_url(connection, header):
    url = "/api/v1/auth/currentAuthority"
    connection.request(method="GET", url=url, body={}, headers=header)
    r = connection.getresponse()
    output = json.loads(r.read())
    return output['items'][0]['subscriptions'][0]['managerUrl'].split('//')[1]

def get_all_protection_sets(connection, header):
    url = "/api/v2/management/protectionSets"
    connection.request(method="GET", url=url, body={}, headers=header)
    r = connection.getresponse()
    output = json.loads(r.read())

    return output['items']      

def get_all_protection_set_vms(connection, header, protect_uuid):
    url = "/api/v2/protectionSets/{}/vms".format(protect_uuid)

    connection.request(method="GET", url=url, body={}, headers=header)
    # catch any exceptions if protection set is empty
    try:
        r = connection.getresponse()
        output = json.loads(r.read())
        return output['items']
    except Exception as e:
        return

def backup_vm(protection_set_uuid, vm_uuid, connection, header):
    # Define the body
    body = {
            "list": [
                {
                "vmUuid": vm_uuid
                }
            ]
    }
    json_body = json.dumps(body)
    url = "/api/v2/protectionSets/{}/backups/vms".format(protection_set_uuid)
    connection.request(method="POST", url=url, body=json_body,headers=header)
    return connection.getresponse()

def print_response(response):
    print('Response status: %d' % response.status)
    temp = response.read()
    try:
        print_data = json.loads(temp)
        print(json.dumps(print_data, indent=4, sort_keys=True))
        return print_data
    except JSONDecodeError:
        print(temp)

def main(argv):
    # Parse command line parameters VM and/or status
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-v", "--vm", help="VM to be searched", required=True)
    myParser.add_argument("-f", "--file", help="JSON credentials file", required=True)           

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    args = myParser.parse_args(argv)
    VM_NAME=args.vm
    SERVICE_ACCOUNT_FILE=args.file

    # Establish connection to Registry
    registry_endpoint_connection = http.client.HTTPSConnection(REGISTRY_ENDPOINT)
    id_token = request_id_token(CLIENT_ID, SCOPES, SERVICE_ACCOUNT_FILE)
    print("Token:\n%s" % id_token)
    headers = {
            'Content-type' : 'application/json',
            'Authorization' : id_token
    }

    # Establish connection to Manager
    MANAGER_ENDPOINT = get_manager_url(registry_endpoint_connection, headers)
    print("Manager URL: " + MANAGER_ENDPOINT)
    manager_endpoint_connection = http.client.HTTPSConnection(MANAGER_ENDPOINT,context=ssl._create_unverified_context())

    # find all Protection sets
    prosets=get_all_protection_sets(manager_endpoint_connection,headers)
    for proset in prosets:
        print('Protectionset name: %s, Protectionset UUID: %s' %(proset['name'], proset['uuid']))
        # find all VMs in Protection Set
        vms=get_all_protection_set_vms(manager_endpoint_connection,headers,proset['uuid'])
        # check if VM list is empty
        if vms:
            for vm in vms:
                print('VM Name name: %s, VM UUID: %s' %(vm['name'], vm['uuid']))
                if vm['name'] == VM_NAME:
                    print ("Found VM to backup!")
                    r = backup_vm(proset['uuid'], vm['uuid'], manager_endpoint_connection, headers)
                    print_response(r)

    exit (0)

if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python
# Written by Carlos Talbot
# This script will clone a HYCU policy within Protege.
# TO execute you need to pass the following parameters:
#
# python3 ./clone_policy_protege.py  -u"username@gmail.com" -p"PASSW0RD" -a"accountid" -o<Original Policy> -n<New Policy> -s<Protection Set> -c[number of copies]
#
# 2023/12/15 Initial release

import requests
import json
import sys
import argparse

def clientId_lookup(HYCUAccountID):
    url = f"https://authentication.protege.hycu.com/api/v2/customerAccounts/{HYCUAccountID}/identityProviders/auth"
    response = requests.get(url)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)
    if (debug):
        print("*********************************************************************************************************************")
        print ("Performing the first GET request")
        print ("")
        print("curl --request GET --url https://authentication.protege.hycu.com/api/v2/customerAccounts/{HYCUAccountID}/identityProviders/auth")
        print("*********************************************************************************************************************")
        print("Output🟢")
        print(pretty_response)
        print("*********************************************************************************************************************")

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the "clientId" from the JSON content of the response
        data = response.json()
        client_id = data['items'][0]['clientId']
        print("*********************************************************************************************************************")
        print("`client_id` information found in the response JSON.")
        print("*********************************************************************************************************************")
    else:
        print("Request failed with status code:", response.status_code)  
        exit(1)

    return client_id

def cred_Authenticate(client_id, UserName, Password):
    url = "https://cognito-idp.us-east-1.amazonaws.com/"
    headers = {
        'Content-Type': 'application/x-amz-json-1.1',
        'x-amz-target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'x-amz-user-agent': 'aws-amplify/5.0.4 js',
    }
    data_arry = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": UserName,
            "PASSWORD": Password,
        },
        "ClientMetadata": {}
    }
    response = requests.post(url, headers=headers, json=data_arry)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)
    if (debug):    
        print("*********************************************************************************************************************")
        print ("Performing the POST request")
        print ("")
        print('''curl --request POST --url https://cognito-idp.us-east-1.amazonaws.com /
        --header 'Content-Type: application/x-amz-json-1.1' --header 'x-amz-target: AWSCognitoIdentityProviderService.InitiateAuth' --header 'x-amz-user-agent: aws-amplify/5.0.4 js' --data '{
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": "639dp09d9e4vfs6oe4n04ksnom",
        "AuthParameters": {
            "USERNAME": "Protégé_UserName",
            "PASSWORD": "Protégé_Password"
        },
        "ClientMetadata": {}
        }''')
        print("*********************************************************************************************************************")
        print("Output🟢")
        print(pretty_response)
        print("*********************************************************************************************************************")

    # ### 4.1 Extracting the "IdToken" value from the response JSON.
    # IDToken value is needed for the next step. 

    # Check if the request was successful
    if response.status_code == 200:
        try:
            # Extract the "IdToken" from the JSON content of the response
            data = response.json()
            IdToken = data["AuthenticationResult"]["IdToken"]
            print("`IdToken` information found in the response JSON.")
        except KeyError:
            print("'IdToken' not found in the response JSON.")
    else:
        print("Request failed with status code:", response.status_code)       
        exit(1)

    return IdToken

def bearer_token(IdToken):
    url = "https://authentication.protege.hycu.com/api/v2/authentication/token"
    headers = {
        "Authorization": f"Bearer {IdToken}"
    }
    response = requests.get(url, headers=headers)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)
    if (debug):    
        print("*********************************************************************************************************************")
        print ("Performing the second GET request")
        print ("")
        print('''curl --request GET --url https://authentication.protege.hycu.com/api/v2/authentication/token 
        --header "Authorization: Bearer "IdToken"''')
        print("*********************************************************************************************************************")
        print("Output🟢")
        print(pretty_response)
        print("*********************************************************************************************************************")

    # ### 5.1 Extracting "token" from the response JSON.

    # Token value is needed for the final step. 

    # Extract the "clientId" from the JSON content of the response
    data = response.json()
    raw_token = data["items"][0]["token"]
    # Split the token to remove "Bearer"
    token_parts = raw_token.split(" ")
    # Check if the token has at least two parts (Bearer and the token value)
    if len(token_parts) == 2:
        # Get the second part as the actual token
        token = token_parts[1]
    else:
        print("Invalid token format")
        exit(1)

    return(token)

def get_endpointUrl(bearer, HYCUAccountID):
    url = f"https://registry.protege.hycu.com/api/v2/customerAccounts/{HYCUAccountID}/manager"
    response = requests.get(url)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)
    if (debug):    
        print("*********************************************************************************************************************")
        print ("Performing the third GET request")
        print ("")
        print("curl --request GET --url https://registry.protege.hycu.com/api/v2/customerAccounts/{HYCUAccountID}/manager")
        print("*********************************************************************************************************************")
        print("Output🟢")
        print(pretty_response)
        print("*********************************************************************************************************************")

    # ### 6.1 Extracting "endpoint url" from the response JSON.

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the "clientId" from the JSON content of the response
        data = response.json()
        dedicated_URL = data['items'][0]['endpointUrl']
        print("*********************************************************************************************************************")
        print("`endpointUrl` information found in the response JSON.")
        print("*********************************************************************************************************************")
    else:
        print("Request failed with status code:", response.status_code)   
        exit(1)
    return dedicated_URL

def get_protectionSet(dedicated_URL, token, protectset ):
    # Define the URL and headers
#     endpoint = "policies?filter=name##" + origpolicy
 
    url = f"{dedicated_URL}/api/v2/protectionSets?filter=name%3D%3D{protectset}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Perform the GET request
    response = requests.get(url, headers=headers)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)

    # Check the response
    if response.status_code != 200:
        print(f"Request failed with status code: {response.status_code}")      
        exit(1)

    # return protectionSet UUID    
    return json_response['items'][0]['uuid']

def get_policy(dedicated_URL, token, protect_uuid, origpolicy):
    # Define the URL and headers
#     endpoint = "policies?filter=name##" + origpolicy
 
    url = f"{dedicated_URL}/api/v2/protectionSets/{protect_uuid}/policies?filter=name%3D%3D{origpolicy}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Perform the GET request
    response = requests.get(url, headers=headers)
    data = response.json()
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)

    # Check the response
    if response.status_code != 200:
        print(f"Request failed with status code: {response.status_code}")
        exit(1)

    # return policy UUID
    return json_response['items']   
    #return json_response['items'][0]['uuid']

def create_policy(dedicated_URL, token, protect_uuid, data):
    # Define the URL and headers

    url = f"{dedicated_URL}/api/v2/protectionSets/{protect_uuid}/policies"
    headers = {
       "Content-Type": "application/json",
       "Authorization": f"Bearer {token}"
    }

    response = requests.post(url, headers=headers, json=data)
    json_response = json.loads(response.text)
    pretty_response = json.dumps(json_response, indent=4)

    # Check the response
    if response.status_code not in [200,201,202]:
        print(f"Request failed with status code: {response.status_code}")
        print(f"Policy: {data['name']}")        
        print(f"Reason: {json_response['error']['message']}")        
        exit(1)

    return response

def main(argv):

    global debug

    debug=0

    # Parse command line parameters
    myParser = argparse.ArgumentParser(description="HYCU for Enterprise Clouds backup and archive")
    myParser.add_argument("-u", "--username", help="HYCU Username", required=True)
    myParser.add_argument("-p", "--password", help="HYCU Password", required=True)
    myParser.add_argument("-s", "--protectset", help="HYCU Protection Set", required=True)    
    myParser.add_argument("-a", "--accountID", help="HYCU AccountID", required=True)
    myParser.add_argument("-o", "--origpolicy", help="Current policy", required=True)    
    myParser.add_argument("-n", "--newpolicy", help="New policy", required=True)
    myParser.add_argument("-c", "--copies", help="Optional: -c=5 (create 5 new polices)", required=False)        

    args = myParser.parse_args(argv)
    username=args.username
    password=args.password
    accountID=args.accountID
    protectset=args.protectset
    origpolicy=args.origpolicy
    newpolicy=args.newpolicy
    copies=None if not args.copies else (int(args.copies)) 

    print ("accountid is " + accountID)   

    if len(sys.argv)==1:
        myParser.print_help()
        exit(1)

    client_id=clientId_lookup(accountID)

    IdToken=cred_Authenticate(client_id, username, password)

    bearer=bearer_token(IdToken)

    url=get_endpointUrl(bearer, accountID)

    # find protection set
    protect_uuid=get_protectionSet(url, bearer, protectset)

    if not protect_uuid:
       print("Can't find pretect set " + protectset + "!")
       exit (1)       

    # find original policy
    data=get_policy(url, bearer, protect_uuid, origpolicy)
    if not data:
       print("Can't find original policy " + origpolicy + "!")
       exit (1)       

    data[0]['name']=newpolicy
    # remove UUID from original policy
    del data[0]['uuid']
  
    # create only one policy
    if not copies:
        response=create_policy(url, bearer, protect_uuid, data[0])
        print("Successfully created new policy " + newpolicy)
    else:
    # create x number of policies
        for x in range(copies):
            data[0]['name']=newpolicy + "-" + str(x+1)
            response=create_policy(url, bearer, protect_uuid, data[0])
            print("Successfully created new policy " + data[0]['name'])
    exit()

if __name__ == "__main__":
    main(sys.argv[1:])

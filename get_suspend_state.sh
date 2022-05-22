#!/usr/bin/bash
#This script will check if the HYCU controller is in a suspended state.
#The three options that will return include: SUSPEND, SUSPEND_CLEANUP, and RESUME

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/administration/suspendMode" | jq -r .entities[]

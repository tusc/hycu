#!/usr/bin/bash
#This script will check the state of SSH access on the HYCU controller.

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

# a return of FALSE means SSH is enabled, TRUE mean SSH is disabled
curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/ssh/lock?pageSize=100" | jq -r ".entities[].sshLocked"

#!/usr/bin/bash
# This script will resume jobs on HYCU controller that were paused.
hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v
0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authoriza
on: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/administration/scheduler/start" | jq
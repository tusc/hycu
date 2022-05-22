#!/usr/bin/bash
#This script will enable or disable SSH access to the HYCU conrtroller. It is advised to run this remotely from another system since it will
#impact your SSH session on the controller.

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"
# set the next value to disable ssh access (true) or enable ssh access (false)
ssh_lock=false

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" -d "{
  \"sshLocked\": $ssh_lock
}" "https://$hycuctlr:8443/rest/v1.0/ssh/lock" | jq

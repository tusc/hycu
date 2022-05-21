#!/usr/bin/bash
hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"
# set the next value to block ssh access (true) or allow ssh access (false)
ssh_lock=false

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

#curl -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/ssh/lock?pageSize=100" | jq .sshLocked


curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" -d "{
  \"sshLocked\": $ssh_lock
}" "https://$hycuctlr:8443/rest/v1.0/ssh/lock" | jq

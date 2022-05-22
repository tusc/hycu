#!/usr/bin/bash
#This script will pause all HYCU backup controller activities. All currently running jobs are allowed to complete normally.

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# This variable determines how long to pause activities
# This must be in one of the following formats:
# "yyyy-MM-dd'T'HH:mm:ss.SSSX", "yyyy-MM-dd'T'HH:mm:ss.SSS", "EEE, dd MMM yyyy HH:mm:ss zzz", "yyyy-MM-dd"
time_until="2030-10-01"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" -d "{ \"standbyUntil\": \"$time_until\" }" "https://$hycuctlr:8443/rest/v1.0/administration/scheduler/standby" | jq

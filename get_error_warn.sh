#!/bin/bash
#This script is an example where you do not need a username and password to authenticate. It uses an API key that you generate from the HYCU UI.
#This script will not work unless you generate a key and save it in the script.
# the list is JSON list of errors and warnings within events.

hycuctlr="xxxxx.hycu.com"
APIkey="ZxxxxxxxxZw=="

curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIkey" "https://$hycuctlr:8443/rest/v1.0/events"  | jq  -r ".entities[] | select (.severity==\"ERROR\" or .severity==\"WARNING\") "

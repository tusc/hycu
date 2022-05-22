#!/usr/bin/bash
#This script is an example where you do not need a username and password to authenticate. It uses an API key that you generate from the UI.
#This script will not work unless you generate a key and save it in the script.

hycuctlr="192.168.1.80"

APIkey="bW12czh0ZjZjZjM5NnFjN2ZiNHRvdDgwaHZwaQ=="

curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIkey" "https://$hycuctlr:8443/rest/v1.0/users?pageSize=100"  | jq

#!/usr/bin/bash
hycuctlr="192.168.1.80"

# you need to generate an API key from the UI in order to use this bearer token
APIkey="bW12czh0ZjZjZjM5NnFjN2ZiNHRvdDgwaHZwaQ=="

curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIkey" "https://$hycuctlr:8443/rest/v1.0/users?pageSize=100"  | jq

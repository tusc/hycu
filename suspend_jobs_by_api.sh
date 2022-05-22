#!/usr/bin/bash
#This script will pause all HYCU backup controller activities. All currently running jobs are allowed to complete normally.

hycuctlr="192.168.1.80"

# You need to generate an API key from the UI in order to use this bearer token
# User needs Administrator role
APIKey="bW12czh0ZjZjZjM5NnFjN2ZiNHRvdDgwaHZwaQ=="

# This variable determines how long to pause activities
# This must be in one of the following formats:
# "yyyy-MM-dd'T'HH:mm:ss.SSSX", "yyyy-MM-dd'T'HH:mm:ss.SSS", "EEE, dd MMM yyyy HH:mm:ss zzz", "yyyy-MM-dd"
time_until="2030-10-01"

curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" -d "{ \"standbyUntil\": \"$time_until\" }" "https://$hycuctlr:8443/rest/v1.0/administration/scheduler/standby" | jq

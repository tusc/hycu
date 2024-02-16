#!/bin/bash
#This script is an example where you do not need a username and password to authenticate. It uses an API key that you generate from the HYCU UI.
#This script will not work unless you generate a key and save it in variable below. You will also need the UUID of the backup target that can be easily
#found in the HYCU UI when highlighting the target of interest.
#
# sample output should display the target name and % of capacity utilized:
#
# root@Tower:/mnt/user/hycu_scripts# ./get_target_pct.sh 
# Dell EMC
# 0.38076636253414103

hycuctlr="xxxx.hycu.com"
APIkey="XXxxxxxx"
Target_UUID="d0793426-1230-4532-8121-5c7900a1893a"

curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIkey" "https://$hycuctlr:8443/rest/v1.0/targets/$Target_UUID"  | jq -r ".entities[].name,.entities[].totalUtilizationPct"

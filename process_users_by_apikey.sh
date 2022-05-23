#!/usr/bin/bash
# This is a sample script that will go through all the user records and update the email field with a fake address.
# This can be modified for other use cases that require batch updates of user records.
# This script relies on an APIKey created from the UI. User logged into the UI needs Administrator role when generating the key.
hycuctlr="192.168.1.80"

APIKey="bW12czh0ZjZjZjM5NnFjN2ZiNHRvdDgwaHZwaQ=="

uuid_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0
/users?pageSize=100"  | jq -r ".entities[].uuid"`

for uuid in $uuid_list
do
        echo "Processing uuid $uuid"
        # Obtain the user record by UUID
        user_record=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0/users/$uuid"  | jq -r ".entities[]"`
        echo -n "Username is "
        echo $user_record | jq ".username"
        echo -n "email is "
        echo $user_record | jq ".email"
        # modify EMAIL field in record
        # UNCOMMENT the two lines below to allow changes to the user fields
#       new_record=`echo $user_record | jq ".email=\"testemail@null.com\""`
#       curl -s -X PATCH --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0/users/$uuid" -d "$new_record" |jq
done

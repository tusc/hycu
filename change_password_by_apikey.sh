#!/usr/bin/bash
hycuctlr="192.168.1.80"

# You need to generate an API key from the UI in order to use this bearer token
# User needs Administrator role
APIKey="bW12czh0ZjZjZjM5NnFjN2ZiNHRvdDgwaHZwaQ=="

# user account you want to change password
changeuser="testuser"
origpass="newadmin123"
newpass="newadmin456"

# Obtain the UUID for username
uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0/users?pageSize=100"  | jq ".entities[] | select (.username==\"$changeuser\")" | jq -r .uuid`

# Obtain the user record by UUID
user_record=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0/users/$uuid"  | jq ".entities[]"`

# append the password fields to end of user record
new_record=`echo $user_record |  jq '. += {"password":"'$newpass'", "oldpassword":"'$origpass'"}'`

# update user record with new password
curl -s -X PATCH --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $APIKey" "https://$hycuctlr:8443/rest/v1.0/users/$uuid" -d "$new_record" |jq

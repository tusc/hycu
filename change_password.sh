#!/usr/bin/bash
hycuctlr="192.168.1.80"
# admin account that will be updating record
adminuser="admin"
adminpass="newadmin"

# user account you want to change password
changeuser="testuser"
origpass="newadmin456"
newpass="newadmin123"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $adminuser:$adminpass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

# Obtain the UUID for username
uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/users?pageSize=100"  | jq ".entities[] | select (.username==\"$changeuser\")" | jq -r .uuid`

# Obtain the user record by UUID
user_record=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/users/$uuid"  | jq ".entities[]"`

# append the password fields to end of user record
new_record=`echo $user_record |  jq '. += {"password":"'$newpass'", "oldpassword":"'$origpass'"}'`

# update user record with new password
curl -s -X PATCH --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/users/$uuid" -d "$new_record" | jq

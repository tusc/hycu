#!/usr/bin/bash
# This script will run through all the credential groups and assign them a password as defined by the variable newpass
# This example can be used to modify the script to synchronize with 3rd party password vauls (e.g. CyberArk)
#
# You need to uncomment the last line in order to commit changes to the password field

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# set this to the new password for the creditional group
newpass="u*ye4#s"


credgrp_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/credentialgroups?pageSize=100"  | jq -r ".entities[].uuid"`

for cred_uuid in $credgrp_list
do
        echo "Processing Credential group $cred_uuid"
        # Obtain the cred group record by UUID
        cred_record=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/credentialgroups?pageSize=100"  | jq ".entities[] | select (.uuid==\"$cred_uuid\") | {name, username, password, sshAuthenticationType, protocol, sshPrivateKey, sshPrivateKeyPassphrase, port, winrmTransport} "  `

        echo -n "name is "
        echo $cred_record | jq ".name"
        echo -n "username is "
        echo $cred_record | jq ".username"

        # modify password field in record
        new_record=`echo $cred_record |  jq '. += {"password":"'$newpass'"}'`

        # UNCOMMENT the line below to allow changes to the user fields
        # append the password field to end of user record
#       curl -s -X PATCH --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/credentialgroups/$cred_uuid" -d "$new_record" | jq

done

#!/usr/bin/bash
# This script will update the credentials password for a given username
# You must make sure credentials name and username are properly filed in order to update record.
hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"

# Replace with the credentials you want to update
cred_name="oracle credentials"
cred_username="oracle"

# set this to the new password for the creditional group
newpass="newsecret"


# find credential group with the matching credential name and username
cred_record=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/credentialgroups?pageSize=100"  | jq -r ".entities[]| select ((.name==\"$cred_name\") and (.username==\"$cred_username\"))" `

if [ -z "$cred_record" ]
then
	echo "Credential name ($cred_name) and credential username ($cred_username) not found"
	exit 1
else
	# extract the uuid field
	cred_uuid=`echo $cred_record | jq -r .uuid`
	# extract just the necessary fields for for the REST PATCH call to change password
	cred_record=`echo $cred_record | jq "{name, username, password, sshAuthenticationType, protocol, sshPrivateKey, sshPrivateKeyPassphrase, port, winrmTransport}" `
fi

new_record=`echo $cred_record |  jq '. += {"password":"'$newpass'"}'`

# update credential with new password using REST PATCH call
curl -s -X PATCH --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/credentialgroups/$cred_uuid" -d "$new_record" | jq

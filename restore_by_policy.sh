#!/usr/bin/bash
# This script will run through all the VMs in a policy and perform a clone of the VMs.
# This can be changed to restore the VMs back to the source location.
#

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"
policy_name="Bronze"

#####
# Set the following variable to either CLONE or OVERWRITE which determines how the VMs are restored
restore_mode=CLONE
#restore_mode=OVERWRITE

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)


# retrive the policy UUID for the given name
policy_uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/policies?pageSize=100"  | jq -r ".entities[] | select (.name==\"$policy_name\") | .uuid"`

if [ -z "$policy_uuid" ]
then
        echo "Policy ($policy_name) not found"
        exit 1
fi

echo "Policy $policy_name has a UUID of $policy_uuid"

# Retrieve list of VMs in policy by UUID
vm_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms?pageSize=100" | jq -r ".entities[] | select (.protectionGroupUuid==\"$policy_uuid\") | .uuid"`

# Loop through each VM to be restored
for vm_uuid in $vm_list
do
        vm_name=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid?pageSize=100" | jq -r ".entities[].vmName"`

        echo "----------"
        echo "VM name is $vm_name, VM uuid is $vm_uuid"

        # Retrieve the most recent restore point
        backup_info=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid/backups?pageSize=100" | jq -r ".entities[0] | {uuid, type, primaryTargetName, common} "`

        backup_uuid=`echo $backup_info | jq -r ".uuid"`
        backup_type=`echo $backup_info | jq -r ".type"`
        backup_target=`echo $backup_info | jq -r ".primaryTargetName"`
        backup_created=`echo $backup_info | jq -r ".common.created" `
        # times are in EPOCH milliseconds, need to convert to seconds
        backup_time=`date -d @$((($backup_created + 500)/1000))`
        echo -e "Using $backup_type\t\tFROM $backup_target\tusing restore point $backup_time"

        if [[ $RESTORE_MODE == "CLONE" ]]; then
                clone_name="$vm_name""_`date +%s`"
                echo "restore name will be $clone_name"

                restore_rec='{  "vmName": "'$clone_name'", "create_Vm": true, "deleteOriginalVm": false, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": false, "backupUuid": "'$backup_uuid'"  }'
        else
                echo "!!!!!!!!!!!!!!!!!!!!!!!!"
                echo "OVERWRITING ORIGINAL VM!
                echo "restore name will be $vm_name"

                restore_rec='{  "vmName": "'$vm_name'", "create_Vm": true, "deleteOriginalVm": true, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": false, "backupUuid": "'$backup_uuid'"  }'
        fi


        # submit restore request
        rest_ret=`curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/restore" -d "$restore_rec" | jq ".message.titleDescriptionEn"`

        echo "$rest_ret"

done

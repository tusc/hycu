#!/usr/bin/bash
# This script will run through all the VMs in a policy and list the backups for each VM
#

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"
policy_name="Gold"

policy_uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/policies?pageSize=100"  | jq -r ".entities[] | select (.name==\"$policy_name\") | .uuid"`

if [ -z "$policy_uuid" ]
then
        echo "Policy ($policy_name) not found"
        exit 1
fi

echo "Policy $policy_name has a UUID of $policy_uuid"

# Retrieve list of VMs in policy by UUID
vm_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/vms?pageSize=100" | jq -r ".entities[] | select (.protectionGroupUuid==\"$policy_uuid\") | .uuid"`

if [ -z "$vm_list" ]
then
        echo "No VMs found for Policy ($policy_name)"
        exit 1
fi

for vm_uuid in $vm_list
do
        vm_name=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid?pageSize=100" | jq -r ".entities[].vmName"`

        echo "----------"
        echo "VM name is $vm_name, VM uuid is $vm_uuid"

        # Retrieve entire backup chain for given VM
        backup_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid/backups?pageSize=100" | jq -r ".entities[].uuid"`

        # Retreive info for each restore point
        for vm_backup in $backup_list
        do
                backup_info=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid/backup/$vm_backup?pageSize=100" | jq -r ".entities[] | { type, primaryTargetName, snapshotType, common }"`
                backup_type=`echo $backup_info | jq -r ".type"`
                backup_target=`echo $backup_info | jq -r ".primaryTargetName"`
                backup_consistent=`echo $backup_info | jq -r ".snapshotType"`
                backup_created=`echo $backup_info | jq -r ".common.created" `
                # times are in EPOCH milliseconds, need to convert to seconds
                backup_time=`date -d @$((($backup_created + 500)/1000))`
                echo -e "Backup TYPE $backup_type\tTARGET $backup_target\tCONSISTANCY $backup_consistent\tTIME $backup_time"
        done

done

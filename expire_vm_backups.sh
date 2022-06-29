#!/usr/bin/bash
#This script will run through all restore points for a given VM and expire them. Use carefully!
HYCU_CTLR="192.168.1.80"
USERNAME="admin"
PASSWD="newadmin"
VM_NAME="Oracle"

# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $USERNAME:$PASSWD | base64)" "https://$HYCU_CTLR:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)


# Retrieve list of VMs in policy by UUID
VM_UUID=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$HYCU_CTLR:8443/rest/v1.0/vms" | jq -r ".entities[] | select (.vmName | contains(\"$VM_NAME\")) | .uuid"`

if [ -z "$VM_UUID" ]; then
        echo "VM $VM_NAME not found"
        exit 1
fi

# Retrieve backup list for VM
backup_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$VM_UUID/backups?pageSize=100"  | jq -r ".entities[] | .uuid"`


if [ -z "$backup_list" ]; then
        echo "No backups found for $VM_NAME"
        exit 1
fi

echo "Expiring ALL backups for VM $VM_NAME!!!"

for backup_uuid in $backup_list
do
        echo "Deleting backup $backup_uuid"
        #del_ret=`curl -s -X DELETE --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header " Authorization: Bearer $btoken" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$VM_UUID/backup/$backup_uuid?type=BACKUP_AND_COPY" | jq ".message.titleDescriptionEn"`
        del_ret=`curl -s -X DELETE --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$VM_UUID/backup/$backup_uuid?type=BACKUP_AND_COPY" |  jq ".message.titleDescriptionEn"`
        echo $del_ret
done

#!/usr/bin/bash
# This script will run through all the VMs in a policy and perform a restore by cloning or overwriting the original VM.
# The only variable that needs to be configured is RESTORE_MODE and optionally RESTORE_DS if restoring to alternate datastore

hycuctlr="192.168.1.80"
username="admin"
pass="newadmin"
policy_name="Bronze"

################################
# Set the variable RESTORE_MODE to either CLONE or OVERWRITE which determines how the VMs are restored
# Uncomment RESTORE_DS if you want to restore to datastore other than the original location
# If left uncommented, VM will be restored to original datastore
#RESTORE_MODE=CLONE
RESTORE_MODE=OVERWRITE
#RESTORE_DS="VM_DS1"
#################################


# request bearer TOKEN
token=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $username:$pass | base64)" "https://$hycuctlr:8443/rest/v1.0/requestToken" | jq -r '.token'`

# convert TOKEN to base64
btoken=$(echo -n $token | base64)

# retrive the policy UUID for the given name
policy_uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/policies"  | jq -r ".entities[] | select (.name==\"$policy_name\") | .uuid"`

if [ -z "$policy_uuid" ]; then
        echo "Policy ($policy_name) not found"
        exit 1
fi

echo "Policy $policy_name has a UUID of $policy_uuid"


# Retrieve list of VMs in policy by UUID
vm_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms" | jq -r ".entities[] | select (.protectionGroupUuid==\"$policy_uuid\") | .uuid"`


# Loop through each VM to be restored
for vm_uuid in $vm_list
do
        vm_name=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid" | jq -r ".entities[].vmName"`

        echo "----------"
        echo "VM name is $vm_name, VM uuid is $vm_uuid"

        # Retrieve the most recent restore point

        backup_info=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid/backups?orderBy=-restorePointInMillis" | jq -r ".entities[0] | {uuid, type, primaryTargetName, hypervisorUuid, restorePointInMillis} "`

        backup_uuid=`echo $backup_info | jq -r ".uuid"`
        host_uuid=`echo $backup_info | jq -r ".hypervisorUuid"`
        backup_type=`echo $backup_info | jq -r ".type"`
        backup_target=`echo $backup_info | jq -r ".primaryTargetName"`
        backup_created=`echo $backup_info | jq -r ".restorePointInMillis" `
        # times are in EPOCH milliseconds, need to convert to seconds
        backup_time=`date -d @$((($backup_created + 500)/1000))`
        echo -e "Using $backup_type\t\tFROM $backup_target\tusing restore point $backup_time"

        ds_uuid=null
        # Restore to different datastore
        if [ ! -z "$RESTORE_DS" ]; then
                ds_uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/$vm_uuid/restoreLocations?backupUuid=$backup_uuid"  | jq -r ".entities[] |  select (.name | contains(\"$RESTORE_DS\")) | .externalId"`
                if [ -z "$ds_uuid" ]; then
                        echo "Datastore ($RESTORE_DS) not found"
                        exit 1
                fi
                echo "Restoring to alternative datastore $RESTORE_DS ($ds_uuid)"
        else
                echo "Restoring to original datastore"
        fi

        if [[ $RESTORE_MODE == "CLONE" ]]; then
                clone_name="$vm_name""_`date +%s`"
                echo "Will clone vm with new name $clone_name"

                if [ ! -z "$RESTORE_DS" ]; then
                        restore_rec='{  "vmName": "'$clone_name'", "create_Vm": true, "deleteOriginalVm": false, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": false, "containerId": "'$ds_uuid'", "backupUuid": "'$backup_uuid'"  }'
                else
                        restore_rec='{  "vmName": "'$clone_name'", "create_Vm": true, "deleteOriginalVm": false, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": false, "containerId": null, "backupUuid": "'$backup_uuid'"  }'
                fi

        else    # Overwritting the oringal VM
                echo "!!!!!!!!!!!!!!!!!!!!!!!!"
                echo "OVERWRITING ORIGINAL VM!"
                echo "restore name will be $vm_name"

                # grab all vnets the VM is part of
                readarray -t vnet_array < <(curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/backup/$backup_uuid/originalNetworks?uuid=$host_uuid" | jq -c  ".entities[] ")

                # loop through each vnet the VM is part of, extacting the minimum fields for restore REST api call
                vnet_list="[]"
                for vnet in "${vnet_array[@]}"
                do
                        net_mac=`echo "$vnet" | jq -r ".macAddress"`
                        net_name=`echo "$vnet" | jq -r ".virtualNetworkName"`
                        net_type=`echo "$vnet" | jq -r ".virtualNetworkType"`
                        net_uuid=`echo "$vnet" | jq -r ".virtualNetworkId"`

                        #build json array for vnet list
                        #the "'" is needed to ensure strings with spaces are correctly passed
                        vnet_list=`echo $vnet_list|  jq -r '. += [{"name":"'"$net_name"'", "uuid":"'"$net_uuid"'", "type":"'"$net_type"'", "macAddress":"'"$net_mac"'"}]'`
                done

                # final payload for restore REST request
                if [ ! -z "$RESTORE_DS" ]; then
                        restore_rec='{  "vmName": null, "vmUuid": "'$vm_uuid'", "hypervisorUuid": "'$host_uuid'", "backupUuid": "'$backup_uuid'", "containerId": "'$ds_uuid'", "createVm": true, "deleteOriginalVm": true, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": true, "startVgRestore": false, "targetVmUuid": null, "restoreDisk": null, "virtualNetworkList": '$vnet_list'  }'
                else
                        restore_rec='{  "vmName": null, "vmUuid": "'$vm_uuid'", "hypervisorUuid": "'$host_uuid'", "backupUuid": "'$backup_uuid'", "containerId": null, "createVm": true, "deleteOriginalVm": true, "powerOn": false, "restoreSource": "AUTO", "createVolumeGroup": false, "attachVolumeGroup": true, "startVgRestore": false, "targetVmUuid": null, "restoreDisk": null, "virtualNetworkList": '$vnet_list'  }'
                fi
        fi

#       # submit restore request
        rest_ret=`curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $btoken" "https://$hycuctlr:8443/rest/v1.0/vms/restore" -d "$restore_rec" | jq ".message.titleDescriptionEn"`
        echo "$rest_ret"
done

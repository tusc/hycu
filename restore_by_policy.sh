#!/usr/bin/bash
# Written by Carlos Talbot @ HYCU
# 2022/07/07 Initial release
# 2023/08/02 Updated to include COPYMODE
# This script will run through all the VMs in a policy and perform a restore by cloning or overwriting the original VM.
# The only variable that needs to be configured is RESTORE_MODE and optionally RESTORE_DS if restoring to alternate datastore

HYCU_CTLR="10.10.10.10"
USERNAME="user"
#PASSWD="XXXXXXX"
POLICY_NAME="Silver"

# Uncomment the variable below for a dry run
DRYRUN="TRUE"

# Restore from which copy?
# COPYMODE can equal, AUTO, BACKUP, COPY or ARCHIVE
# BACKUP = Primary backup
# COPY = Secondary copy
# ARCHIVE = GFS backup
COPYMODE="BACKUP"

# Set the variable RESTORE_MODE to either CLONE or OVERWRITE which determines how the VMs are restored
# Uncomment RESTORE_DS if you want to restore to datastore other than the original location
# If left commented, VM will be restored to original datastore
# If PASSWD is left commented, user will be prompted for password
RESTORE_MODE=CLONE
#RESTORE_DS="VM_DS2"

#################################

echo "Username: $USERNAME";
echo "CTLR: $HYCU_CTLR";
echo "POLICY_NAME: $POLICY_NAME";

# Check if PASSWORD is blank
if [ -z "$PASSWD" ]; then
        echo -n Enter password for HYCU user:
        read -s PASSWD
        echo
fi

# request bearer TOKEN
TOKEN=`curl -X POST -H "Accept: application/json" -sk -H "Authorization: Basic $(echo -n $USERNAME:$PASSWD | base64)" "https://$HYCU_CTLR:8443/rest/v1.0/requestToken" | jq -r '.token'`

if [ ! -n "$TOKEN" ]; then
        echo "Incorrect password!"
        exit 1
fi

# convert TOKEN to base64
BTOKEN=$(echo -n $TOKEN | base64)

# retrive the policy UUID for the given name
POLICY_UUID=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/policies"  | jq -r ".entities[] | select (.name==\"$POLICY_NAME\") | .uuid"`

if [ -z "$POLICY_UUID" ]; then
        echo "Policy ($POLICY_NAME) not found"
        exit 1
fi

echo "Policy $POLICY_NAME has a UUID of $POLICY_UUID"

# Retrieve list of VMs in policy by UUID
vm_list=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms" | jq -r ".entities[] | select (.protectionGroupUuid==\"$POLICY_UUID\") | .uuid"`

echo -n "COPYMODE is set to "
echo $COPYMODE

# Loop through each VM to be restored
for vm_uuid in $vm_list
do
        vm_name=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$vm_uuid" | jq -r ".entities[].vmName"`

        echo "----------"
        echo "VM name is $vm_name, VM uuid is $vm_uuid"

        # Retrieve the most recent restore point

        backup_info=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$vm_uuid/backups?orderBy=-restorePointInMillis" | jq -r ".entities[0] | {uuid, type, primaryTargetName, secondaryTargetName, hypervisorUuid, restorePointInMillis} "`

        backup_uuid=`echo $backup_info | jq -r ".uuid"`
        host_uuid=`echo $backup_info | jq -r ".hypervisorUuid"`
        backup_type=`echo $backup_info | jq -r ".type"`
        backup_target=`echo $backup_info | jq -r ".primaryTargetName"`
        second_target=`echo $backup_info | jq -r ".secondaryTargetName"`
        backup_created=`echo $backup_info | jq -r ".restorePointInMillis" `
        # times are in EPOCH milliseconds, need to convert to seconds
        backup_time=`date -d @$((($backup_created + 500)/1000))`
        case "$COPYMODE" in
                AUTO)
                        echo -e "Using $backup_type\t\tFROM AUTO\tusing restore point $backup_time"
                        ;;
                BACKUP)
                        echo -e "Using $backup_type\t\tFROM $backup_target\tusing restore point $backup_time"
                        ;;
                COPY)
                        echo -e "Using $backup_type\t\tFROM $second_target\tusing restore point $backup_time"
                        ;;
                *)
                        echo "DEFAULT MODE"
                        echo -e "Using $backup_type\t\tFROM $backup_target\tusing restore point $backup_time"
                        ;;
        esac

        ds_uuid=null
        # Restore to different datastore
        if [ ! -z "$RESTORE_DS" ]; then
                ds_uuid=`curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms/$vm_uuid/restoreLocations?backupUuid=$backup_uuid"  | jq -r ".entities[] |  select (.name | contains(\"$RESTORE_DS\")) | .externalId"`
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
                        restore_rec='{  "vmName": "'$clone_name'", "create_Vm": true, "deleteOriginalVm": false, "powerOn": false, "restoreSource": "'$COPYMODE'", "createVolumeGroup": false, "attachVolumeGroup": false, "containerId": "'$ds_uuid'", "backupUuid": "'$backup_uuid'"  }'
                else
                        restore_rec='{  "vmName": "'$clone_name'", "create_Vm": true, "deleteOriginalVm": false, "powerOn": false, "restoreSource": "'$COPYMODE'", "createVolumeGroup": false, "attachVolumeGroup": false, "containerId": null, "backupUuid": "'$backup_uuid'"  }'
                fi

        else    # Overwritting the oringal VM
                echo "!!!!!!!!!!!!!!!!!!!!!!!!"
                echo "OVERWRITING ORIGINAL VM!"
                echo "restore name will be $vm_name"

                # grab all vnets the VM is part of
                readarray -t vnet_array < <(curl -s -X GET --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms/backup/$backup_uuid/originalNetworks?uuid=$host_uuid" | jq -c  ".entities[] ")

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
                        restore_rec='{  "vmName": null, "vmUuid": "'$vm_uuid'", "hypervisorUuid": "'$host_uuid'", "backupUuid": "'$backup_uuid'", "containerId": "'$ds_uuid'", "createVm": true, "deleteOriginalVm": true, "powerOn": false, "restoreSource": "'$COPYMODE'", "createVolumeGroup": false, "attachVolumeGroup": true, "startVgRestore": false, "targetVmUuid": null, "restoreDisk": null, "virtualNetworkList": '$vnet_list'  }'
                else
                        restore_rec='{  "vmName": null, "vmUuid": "'$vm_uuid'", "hypervisorUuid": "'$host_uuid'", "backupUuid": "'$backup_uuid'", "containerId": null, "createVm": true, "deleteOriginalVm": true, "powerOn": false, "restoreSource": "'$COPYMODE'", "createVolumeGroup": false, "attachVolumeGroup": true, "startVgRestore": false, "targetVmUuid": null, "restoreDisk": null, "virtualNetworkList": '$vnet_list'  }'
                fi
        fi

        if [ ! -z "$DRYRUN" ]; then
                echo "just a dry run"
        else
       # submit restore request
                rest_ret=`curl -s -X POST --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/vms/restore" -d "$restore_rec" | jq ".message.titleDescriptionEn"`
                echo "$rest_ret"
        fi
done

# logout
curl -s -X DELETE --insecure --header "Content-Type: application/json" --insecure --header "Accept: application/json" --insecure --header "Authorization: Bearer $BTOKEN" "https://$HYCU_CTLR:8443/rest/v1.0/requestToken"  | jq -r

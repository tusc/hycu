import requests
import json

# Set the variables
hycu_url = 'https://xxxx.xxxx.com:8443'
username = 'admin'
password = 'admin'

# Create the session
session = requests.Session()
session.auth = (username, password)

# Get list of targets
targets_url = f'{hycu_url}/rest/v1.0/targets'
targets_response = session.get(targets_url)
targets_data = targets_response.json()

# Print report 
print(f'{"Target":30} {"Used Capacity":>15} {"Total Capacity":>15} {"Utilization %":>15}') 
for target in targets_data['entities']:
    free_capacity = target['freeSizeInBytes']
    total_capacity = target['totalSizeInBytes']
    used_capacity = total_capacity - free_capacity
    utilization = (used_capacity / total_capacity) * 100
    print(f'{target["name"]:30} {used_capacity:>15} {total_capacity:>15} {utilization:>15.2f}')

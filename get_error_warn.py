import time
import requests

# Set the variables
hycu_url = 'https://xxxx.xxxx.com:8443'
username = 'admin'
password = 'xxxxxxx'

def get_recent_jobs():
    url = f"{hycu_url}/rest/v1.0/jobs?pageSize=30"
    response = requests.get(url, auth=(username, password))
    return response.json()

def check_jobs(jobs):
    for job in jobs['entities']:
        if job["status"] in ["WARNING", "ERROR"]:
            print(f"Backup job {job['taskName']} completed with status {job['status']}")

while True:
    jobs = get_recent_jobs()
    check_jobs(jobs)
    time.sleep(300) # 5 minutes

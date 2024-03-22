import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
import urllib3
import re

# Replace with the actual credentials and hostname
hostname = "64.103.47.94"
username = "admin"
password = "C1sco12345"

# Suppress only the InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Calculate the time range for the last 30 minutes
end_time = datetime.now()
start_time = end_time - timedelta(minutes=30)

# Format the times as strings
start_time_str = start_time.strftime('%Y-%m-%d%%20%H:%M:%S')
end_time_str = end_time.strftime('%Y-%m-%d%%20%H:%M:%S')

# Overriding for testing purposes
start_time_str = "null"
end_time_str = "null"

# Construct the API URL
base_url = f"https://{hostname}/admin/API/mnt/Session/AuthList/"
url = f"{base_url}{start_time_str}/{end_time_str}"

print(url)

# Dictionary to store the output
sessions_data = {}

# Function to make API requests
def make_request(url, auth):
    response = requests.get(url, auth=auth, verify=False)
    if response.status_code == 200:
        return ElementTree.fromstring(response.content)
    else:
        print(f"Error fetching data: {response.status_code}")
        return None
def extract_step_latency(input_string):
    # Pattern to capture everything between !:StepLatency= and !:TLSCipher
    pattern = r"!:StepLatency=(.*?)!:TLSCipher"

    # Search for the pattern and extract the matched group
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)  # Returns the captured group, which is the content between the delimiters
    else:
        return "No match found"


# First API call to get the active sessions
root = make_request(url, (username, password))
if root is not None:
    for session in root.findall('.//activeSession'):
        user_name = session.find('user_name').text if session.find('user_name') is not None else 'Unknown'
        user_url = f"https://{hostname}/admin/API/mnt/Session/UserName/{user_name}"
        print(f"Fetching data for user: {user_name}")
        
        # Second API call for each user
        user_root = make_request(user_url, (username, password))
        
        if user_root is not None:
            # Convert the entire user_root XML to a string and print
            entire_response_as_string = ElementTree.tostring(user_root, encoding='unicode')
            #print(f"Full XML response for {user_name}:\n{entire_response_as_string}")

            other_attr_string = user_root.find('other_attr_string').text if user_root.find('other_attr_string') is not None else 'No data'
            
            step_latency = extract_step_latency(other_attr_string)
            
            sessions_data[user_name] = step_latency

# Displaying part of the dictionary containing username and step latencies
for user, latency in sessions_data.items():
    print(f"Username: {user}, Step Latency: {latency}")

# Optionally, save the data or further process it as needed

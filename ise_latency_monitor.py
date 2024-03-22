import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
import urllib3
import re
import csv
import os

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



def create_csv():

    file_exists = os.path.isfile('output.csv')
    
    if not file_exists:

        header = [str(i) for i in range(1, 201)]

        header.insert(0,"ClientLatency")
        header.insert(0,"TotalAuthenLatency")
        header.insert(0,"Timestamp")
        header.insert(0,"Username")
        
        
        # Write data to CSV
        with open('output.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)  # Writing header (optional)

       

def write_to_csv(input_string,username,auth_acs_timestamp):
    # Parsing the input string
    data_parts = input_string.split(":!:")
    step_latency_values = data_parts[0].split(";")
    total_auth_latency = data_parts[1].split("=")[1]
    client_latency = data_parts[2].split("=")[1]

    # Create a dictionary for all possible columns, initializing with a default value (e.g., 0 or '')
    data_dict = {str(i): '' for i in range(1, 201)}  # 200 columns + 1 for indexing from 1

    # Update the dictionary with actual values from the input string
    for item in step_latency_values:
        key, value = item.split("=")
        data_dict[key] = value

    # Adding TotalAuthenLatency and ClientLatency to the end of the dictionary
    data_dict['TotalAuthenLatency'] = total_auth_latency
    data_dict['ClientLatency'] = client_latency

    # Prepare data for CSV writing
    header = [str(i) for i in range(1, 201)]

   
    row = [data_dict[str(i)] for i in header]



    row.insert(0,str(client_latency))
    row.insert(0,str(total_auth_latency))
    row.insert(0,auth_acs_timestamp)
    row.insert(0,username)
    
    with open('output.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row)  # Writing header (optional)
    


    print("Data written to CSV successfully.")

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
        

            
            auth_acs_timestamp = user_root.find('auth_acs_timestamp').text
            
            print(auth_acs_timestamp)
        
            # Convert the entire user_root XML to a string and print
            entire_response_as_string = ElementTree.tostring(user_root, encoding='unicode')
            #print(f"Full XML response for {user_name}:\n{entire_response_as_string}")

            other_attr_string = user_root.find('other_attr_string').text if user_root.find('other_attr_string') is not None else 'No data'
            #print(other_attr_string)
            step_latency = extract_step_latency(str(other_attr_string))
            
            sessions_data[user_name] = {
                'step_latency': step_latency,
                'auth_acs_timestamp': auth_acs_timestamp
            }
            
            

create_csv()


# Displaying part of the dictionary containing username and step latencies
for user, data in sessions_data.items():
    step_latency = data['step_latency']
    auth_acs_timestamp = data['auth_acs_timestamp']
    print(f"Username: {user}, Step Latency: {step_latency}, Auth ACS Timestamp: {auth_acs_timestamp}")
    write_to_csv(step_latency, user, auth_acs_timestamp)
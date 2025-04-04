import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
import urllib3
import re
import csv
import os
import json
import configparser

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load configuration from settings.ini
config = configparser.ConfigParser()
config.read('settings.ini')

# Get credentials and settings
hostname = config['credentials']['hostname']
username = config['credentials']['username']
password = config['credentials']['password']
minutes = int(config['settings']['minutes'])
output_file = config['settings']['output_file']
debug_level = int(config['settings']['debug_level'])
limit = int(config['settings']['limit'])
ignore_short = config.getboolean('settings', 'ignore_short', fallback=False)  # New setting

# Calculate time range
end_time = datetime.now()
start_time = end_time - timedelta(minutes=minutes)
start_time_str = start_time.strftime('%Y-%m-%d%%20%H:%M:%S')
end_time_str = end_time.strftime('%Y-%m-%d%%20%H:%M:%S')

# For testing
start_time_str = "null"
end_time_str = "null"

# Construct API URL
base_url = f"https://{hostname}/admin/API/mnt/Session/AuthList/"
url = f"{base_url}{start_time_str}/{end_time_str}"

if debug_level >= 1:
    print(f"Querying: {url}")

# Function to make API requests
def make_request(url, auth):
    try:
        response = requests.get(url, auth=auth, verify=False)
        if response.status_code == 200:
            return ElementTree.fromstring(response.content)
        else:
            print(f"Error fetching {url}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed for {url}: {str(e)}")
        return None

def extract_step_latency(input_string):
    pattern = r"!:StepLatency=(.*?)!:TLSCipher"
    match = re.search(pattern, input_string)
    return match.group(1) if match else "No match found"

def create_csv():
    if not os.path.isfile(output_file):
        header = ["Username", "Timestamp", "TotalAuthenLatency", "ClientLatency", 
                 "ResponseTime", "StepID", "StepName", "StepTime"]
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)

def write_line_to_csv(user_name, auth_acs_timestamp, execution_steps, StepLatency, 
                    TotalAuthenLatency, ClientLatency, ResponseTime, StepNames):
    StepLatency.insert(0, 0)  # Padding to align with StepID and StepName
    row = [val for trio in zip(execution_steps, StepNames, StepLatency) for val in trio]
    row.insert(0, str(ResponseTime))
    row.insert(0, str(ClientLatency))
    row.insert(0, str(TotalAuthenLatency))
    row.insert(0, auth_acs_timestamp)
    row.insert(0, user_name)
    
    with open(output_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row)

def string_to_array(input_string):
    if not input_string:
        return []
    string_list = input_string.split(',')
    return [int(item) for item in string_list]

def string_to_dict(input_string):
    if not input_string or input_string == 'No data':
        return {}
    components = input_string.split(":!:")
    parsed_dict = {}
    for component in components:
        if "=" in component:
            key, value = component.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in parsed_dict:
                if isinstance(parsed_dict[key], list):
                    parsed_dict[key].append(value)
                else:
                    parsed_dict[key] = [parsed_dict[key], value]
            else:
                parsed_dict[key] = value
    return parsed_dict

def extract_values_to_array(input_string):
    if not input_string:
        return []
    components = input_string.split(';')
    values = []
    for component in components:
        if "=" in component:
            _, value = component.split("=")
            values.append(int(value))
    return values

create_csv()

with open('syslog_codes_to_descriptions.json', 'r') as file:
    message_dictionary = json.load(file)

# First API call to get active sessions
root = make_request(url, (username, password))
if root is not None:
    user_count = 0
    for session in root.findall('.//activeSession'):
        if user_count >= limit:
            if debug_level >= 1:
                print(f"Reached user limit of {limit} for sessions with valuable information. Stopping processing.")
            break
        
        user_name = session.find('user_name').text if session.find('user_name') is not None else 'Unknown'
        user_url = f"https://{hostname}/admin/API/mnt/Session/UserName/{user_name}"
        
        if debug_level >= 2:
            print(f"Fetching data for user: {user_name}")
        
        # Second API call for each user
        user_root = make_request(user_url, (username, password))
        
        if user_root is not None:
            auth_acs_timestamp = user_root.find('auth_acs_timestamp')
            auth_acs_timestamp = auth_acs_timestamp.text if auth_acs_timestamp is not None else 'N/A'
            
            execution_steps_elem = user_root.find('execution_steps')
            execution_steps = string_to_array(execution_steps_elem.text if execution_steps_elem is not None else '')
            
            # Skip short sessions if ignore_short is True
            if ignore_short and not execution_steps:
                if debug_level >= 3:
                    print(f"Skipping user {user_name}: No execution steps (short session).")
                continue
            
            other_attr_string_elem = user_root.find('other_attr_string')
            other_attr_string = other_attr_string_elem.text if other_attr_string_elem is not None else 'No data'
            other_attr_dict = string_to_dict(other_attr_string)
            
            TotalAuthenLatency = int(other_attr_dict.get('TotalAuthenLatency', 0))
            ClientLatency = int(other_attr_dict.get('ClientLatency', 0))
            ResponseTime = TotalAuthenLatency - ClientLatency if TotalAuthenLatency and ClientLatency else 0
            
            StepLatency = extract_values_to_array(other_attr_dict.get('StepLatency', ''))
            StepNames = [message_dictionary.get(str(item), "Not found") for item in execution_steps]
            
            if debug_level >= 3:
                print(f"User: {user_name}")
                print(f"Timestamp: {auth_acs_timestamp}")
                print(f"TotalAuthenLatency: {TotalAuthenLatency}")
                print(f"ClientLatency: {ClientLatency}")
                print(f"ResponseTime: {ResponseTime}")
                if execution_steps:
                    print("Steps:")
                    for step_id, step_name, step_time in zip(execution_steps, StepNames, StepLatency):
                        print(f"  StepID: {step_id}, StepName: {step_name}, StepTime: {step_time}")
                else:
                    print("No execution steps found.")
            
            # Only write and count if there are steps or if ignore_short is False
            write_line_to_csv(user_name, auth_acs_timestamp, execution_steps, StepLatency, 
                            TotalAuthenLatency, ClientLatency, ResponseTime, StepNames)
            user_count += 1
else:
    print("Failed to retrieve active sessions list")
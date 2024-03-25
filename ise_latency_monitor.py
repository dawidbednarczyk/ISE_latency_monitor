import requests
from datetime import datetime, timedelta
from xml.etree import ElementTree
import urllib3
import re
import csv
import os
import json

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
    print(url)
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

        header = []
        
        header.insert(0,"StepTime")
        header.insert(0,"StepName")
        header.insert(0,"StepID")
        header.insert(0,"ResponseTime")
        header.insert(0,"ClientLatency")
        header.insert(0,"TotalAuthenLatency")
        header.insert(0,"Timestamp")
        header.insert(0,"Username")
        
        # Write data to CSV
        with open('output.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)  # Writing header (optional)

def write_line_to_csv(user_name, auth_acs_timestamp, execution_steps, StepLatency, TotalAuthenLatency, ClientLatency, ResponseTime, StepNames):
    # Combine elements from the three lists: execution_steps, StepLatency, and StepNames

    StepLatency.insert(0,0)

    row = [val for trio in zip(execution_steps, StepNames, StepLatency) for val in trio]
    
    # Assuming the rest of the function writes this 'row' to a CSV file
    # The 'row' now includes data from execution_steps, StepLatency, and StepNames in that sequential order for each step

    row.insert(0,str(ResponseTime))
    row.insert(0,str(ClientLatency))
    row.insert(0,str(TotalAuthenLatency))
    row.insert(0,auth_acs_timestamp)
    row.insert(0,user_name)
    
    with open('output.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row)  # Writing header (optional)


def string_to_array(input_string):
    # Split the string into a list based on commas
    string_list = input_string.split(',')
    # Convert each item in the list to an integer
    integer_array = [int(item) for item in string_list]
    return integer_array

def string_to_dict(input_string):
    # Split the string into components based on the custom separator ":!:"
    components = input_string.split(":!:")

    # Initialize an empty dictionary to hold the parsed data
    parsed_dict = {}

    # Iterate over each component
    for component in components:
        if "=" in component:
            # Split each component into key and value based on the first "=" encountered
            key, value = component.split("=", 1)
            # Remove potential leading or trailing whitespaces from key and value
            key = key.strip()
            value = value.strip()
            # Assign the key-value pair to the dictionary
            # If a key already exists, append the value to the existing entry (as list if necessary)
            if key in parsed_dict:
                if isinstance(parsed_dict[key], list):
                    parsed_dict[key].append(value)
                else:
                    parsed_dict[key] = [parsed_dict[key], value]
            else:
                parsed_dict[key] = value

    return parsed_dict

def extract_values_to_array(input_string):
    # Split the string into components based on ";"
    components = input_string.split(';')
    # Initialize an empty list to hold the values
    values = []
    # Iterate over each component
    for component in components:
        if "=" in component:
            # Split each component into key and value based on "="
            _, value = component.split("=")
            # Append the value to the list as an integer
            values.append(int(value))
    return values


create_csv()


with open('syslog_codes_to_descriptions.json', 'r') as file:
    # Parse the JSON file and convert it into a Python dictionary
    message_dictionary = json.load(file)

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
            execution_steps = string_to_array(user_root.find('execution_steps').text)
            other_attr_string = user_root.find('other_attr_string').text if user_root.find('other_attr_string') is not None else 'No data'
            other_attr_dict = string_to_dict(other_attr_string)
            TotalAuthenLatency = int(other_attr_dict['TotalAuthenLatency'])
            ClientLatency = int(other_attr_dict['ClientLatency'])
            ResponseTime = TotalAuthenLatency - ClientLatency
            StepLatency = extract_values_to_array(other_attr_dict['StepLatency'])
            StepNames = [message_dictionary.get(str(item), "Not found") for item in execution_steps]
            #print(other_attr_dict)

            print(user_name)
            print(auth_acs_timestamp)
            print(TotalAuthenLatency)
            print(ClientLatency)
            print(ResponseTime)
            #print(execution_steps)
            #print(StepLatency)
            #print(StepNames)

            # Convert the entire user_root XML to a string and print
            #entire_response_as_string = ElementTree.tostring(user_root, encoding='unicode')
            #print(f"Full XML response for {user_name}:\n{entire_response_as_string}")


            write_line_to_csv(user_name,auth_acs_timestamp,execution_steps,StepLatency,TotalAuthenLatency,ClientLatency,ResponseTime,StepNames)
            


import requests
import json

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.4:5000/run/test_rainbow"

# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

try:
    # Send a POST request to the server with the JSON data
    print(f"Sending request to {URL}...")
    response = requests.post(URL, data="", headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        print("Success! The server received the request.")
        print("Server response:", response.json())
    else:
        print(f"Error! Status code: {response.status_code}")
        print("Server response:", response.text)

except requests.exceptions.ConnectionError as e:
    print(f"Failed to connect to the server at {URL}.")
    print("Please ensure the voice server is running and accessible.")
    print(f"Error details: {e}")
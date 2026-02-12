import requests
import json
from core_utils import CoreUtils

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.6:6000/say"

# The text you want the voice server to speak
utterance_text = "Hallo albrecht, my name is K6"

logger = CoreUtils.getLogger("test voice server")
# Create the data payload as a dictionary
payload = {
    "utterance": utterance_text
}

# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

try:
    # Send a POST request to the server with the JSON data
    logger.info(f"Sending request to {URL}...")
    response = requests.post(URL, data=json.dumps(payload), headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        logger.info("Success! The server received the request.")
        logger.info("Server response:", response.json())
    else:
        logger.info(f"Error! Status code: {response.status_code}")
        logger.info("Server response:", response.text)

except requests.exceptions.ConnectionError as e:
    logger.info(f"Failed to connect to the server at {URL}.")
    logger.info("Please ensure the voice server is running and accessible.")
    logger.info(f"Error details: {e}")
from venv import logger

import requests
import json
from core_utils import CoreUtils

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.1:5000/showText"


# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

class Matrix:
    def __init__(self):
        self.logger = CoreUtils.getLogger("matrix_display")

    def show_text(self, text):
        payload = {"message": text}
        try:
            # Send a POST request to the server with the JSON data
            self.logger.info(f"Sending request to {URL}...")
            response = requests.post(URL, data=json.dumps(payload), headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                self.logger.info("Server response:", response.json())
            else:
                self.logger.error(f"Error! Status code: {response.status_code}")
                self.logger.error("Server response:", response.text)

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Failed to connect to the server at {URL}.")
            self.logger.error("Please ensure the voice server is running and accessible.")
            self.logger.error(f"Error details: {e}")
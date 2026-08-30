import threading
import requests
import json
import queue
from core_utils import CoreUtils

# The URL of your Flask voice server
# Make sure to use the correct IP address and port
URL = "http://192.168.4.1:5000/displayText"


# The headers specify that you are sending JSON data
headers = {
    "Content-Type": "application/json"
}

class OledText:
    def __init__(self):
        # New: Setup for background display updates
        self.display_queue = queue.Queue(maxsize=1) # Only keep the latest message
        self.display_thread = threading.Thread(target=self._display_worker, daemon=True)
        self.display_thread.start()
        self.logger = CoreUtils.getLogger("oled_display")

    def show_text(self, text):
        self.logger.info(f"Queueing text for display: {text}")
        try:
            self.logger.info(f"Show text: {text}")
            self.display_queue.put_nowait(text)
        except queue.Full:
           # If the background thread is busy, skip this update to keep loop speed
           pass
        except requests.exceptions.ConnectionError as e:
           self.logger.error(f"Failed to connect to the Oled Server at {URL}.")
           self.logger.error(f"Error details: {e}")

    def _display_worker(self):
        """Background thread that handles slow network requests."""
        while True:
            try:
                # This blocks here until a message is put in the queue
                text = self.display_queue.get()
                self.logger.info(f"Display worker processing: {text}")
                self.display_oled(text)
                # Tell the queue we are done
                self.display_queue.task_done()
            except requests.exceptions.RequestException:
                # We don't want the background thread to crash the whole program
                self.logger.warning("OLED server unreachable or timed out.")
            except Exception as e:
                self.logger.error(f"Display worker error: {e}")
    
    def display_oled(self, text):
        payload = {"header":"Info", "message": text}
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
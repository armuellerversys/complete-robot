from flask import Flask, jsonify, request
import time
import os

# Import the speak function from our separate module
from ovos_client import speak

# This is required for the Flask server to run properly in a separate process
# from the OVOS bus client
if __name__ == "__main__":
    app = Flask(__name__)
else:
    app = Flask(__name__)

@app.route('/say', methods=['POST'])
def say_text():
    """Endpoint to trigger text-to-speech."""
    data = request.get_json()
    utterance = data.get('utterance', None)

    if not utterance:
        return jsonify({"status": "error", "message": "No 'utterance' provided"}), 400

    print(f"Received request to speak: '{utterance}'")
    speak(utterance)

    return jsonify({"status": "success", "message": "Speech request sent"}), 200

# We'll set up a startup message
startup_message = f"Start voice server: {os.environ.get('FLASK_RUN_HOST', '127.0.0.1')}"
print(startup_message)
print(f"Process-PID: {os.getpid()}")

if __name__ == '__main__':
    # You MUST set use_reloader=False to prevent the double-initialization error
    app.run(host='0.0.0.0', port=6000, use_reloader=False)
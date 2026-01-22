from flask import Flask, jsonify, request
import os
import time

COMMAND_FILE = "/home/ovos/python/voice-server/alternate/ovos_command.txt"

app = Flask(__name__)

@app.route('/say', methods=['POST'])
def say_text():
    """Endpoint to trigger text-to-speech."""
    data = request.get_json()
    utterance = data.get('utterance', None)

    if not utterance:
        return jsonify({"status": "error", "message": "No 'utterance' provided"}), 400

    print(f"Received request to speak: '{utterance}'")

    # Write the command to the file
    with open(COMMAND_FILE, "w") as f:
        f.write(f"speak:{utterance}")
    
    print(f"Commandfile written")
    # Wait for the daemon to process the command
    time.sleep(1) # You may need to adjust this depending on system load
    
    # Check if the file was processed (deleted)
    if not os.path.exists(COMMAND_FILE):
        return jsonify({"status": "success", "message": "Speech request sent to daemon"}), 200
    else:
        return jsonify({"status": "error", "message": "Daemon failed to process request"}), 500

if __name__ == '__main__':
    # You MUST set use_reloader=False to prevent the double-initialization error
    app.run(host='0.0.0.0', port=6000, use_reloader=False)
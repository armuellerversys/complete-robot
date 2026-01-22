from flask import Flask, jsonify, request
from ovos_bus_client.message import Message
from ovos_bus_client.client import MessageBusClient
import os
import time

app = Flask(__name__)
bus = MessageBusClient()

@app.route('/say', methods=['POST'])
def say_text():
    data = request.get_json()
    utterance = data.get('utterance', None)
    sound = data.get('sound', None) # New: name of the wav file in the sounds folder

    if not utterance and not sound:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    # 1. Play Sound Effect if requested
    if sound:
        # We point to the shared sounds folder inside the container
        sound_path = f"/home/ovos/sounds/{sound}"
        print(f"K9 playing sound effect: {sound}")
        if os.path.exists(sound_path):
            print("The file exists.")
            bus.emit(Message("mycroft.audio.play_sound", data={"uri": sound_path}))
        
            # Small delay to let the sound start before speaking
            time.sleep(0.5)
        else :
            print(f"The file {sound_path} not exists.")
            return jsonify({"status": "error file not found"}), 200

    # 2. Speak the utterance
    if utterance:
        print(f"K9 responding: '{utterance}'")
        bus.emit(Message("speak", data={"utterance": utterance, "lang": "en-us"}))

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    print("starting voice server")
    bus.run_in_thread() 
    app.run(host='0.0.0.0', port=6000, use_reloader=False)

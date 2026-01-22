import requests
import time

SERVER_BASE_URL = "http://192.168.4.4:5000/run/forward"
SERVER_MOVE_URL = "http://192.168.4.4:5001/control"

try:
    print(f"Handle_control: {SERVER_BASE_URL}!")
    print(f"Send base request http post-> {SERVER_MOVE_URL}")
    requests.post(SERVER_BASE_URL)

    input('Hello! Test-Forward -> Waiting \n')

    print(f"Send control request http post-> {SERVER_MOVE_URL}")
    payload ={"command": "set_forward", "speed": "80", "distance": "1200"}
    response = requests.post(SERVER_MOVE_URL, data=payload, timeout=4)
    print(f"Receive control request http return-> {response.status_code}")

except:
    print("Unable to reach the robot")
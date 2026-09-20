import threading
from evdev import InputDevice, categorize, ecodes

# Replace with the actual event node found in the previous step
GAMEPAD_PATH = '/dev/input/event5'

# Standardize axis ranges (typically 0 to 255 or -32768 to 32767 depending on controller)
AXIS_MAX = 32767

def scale_axis(value):
    """Normalizes raw stick input to a range of -1.0 to 1.0"""
    return round(value / AXIS_MAX, 2)

def gamepad_loop(device_path):
    try:
        gamepad = InputDevice(device_path)
        print(f"Connected to {gamepad.name}")
        
        for event in gamepad.read_loop():
            print(f"Event: {event.type}, Code: {event.code}, Value: {event.value}")
            # Handle Analog Stick Movement (ABS events)
            if event.type == ecodes.EV_ABS:
                # Absolute axis codes: 0=ABS_X (Left Stick X), 1=ABS_Y (Left Stick Y)
                if event.code == ecodes.ABS_Y:
                    steering = scale_axis(event.value)
                    print(f"Steering: {steering}")
                    set_steering(steering)  # Call your existing function
                    
                elif event.code == ecodes.ABS_RZ or event.code == ecodes.ABS_RY:
                    speed = scale_axis(event.value)
                    print(f"Speed: {speed}")
                    set_speed(speed)        # Call your existing function

            # Handle Button Presses (KEY events)
            elif event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_down:
                    if event.code == ecodes.BTN_SOUTH: # A button / Cross
                        stop_vehicle()      # Emergency stop or action

    except FileNotFoundError:
        print("Gamepad device path not found. Is it connected?")
    except PermissionError:
        print("Run script with root/sudo permissions or add user to 'input' group.")

# Start reading the controller in a background thread so it doesn't block main loop
controller_thread = threading.Thread(target=gamepad_loop, args=(GAMEPAD_PATH,), daemon=True)
controller_thread.start()

def set_steering(steering):
    # Implementation for setting steering
    print(f"Steering set to: {steering}")
    pass

def set_speed(speed):
    # Implementation for setting speed
    print(f"Speed set to: {speed}")
    pass

def stop_vehicle():
    # Implementation for stopping vehicle
    print("Vehicle stopped.")
    pass

# Keep main program running
while True:
    pass
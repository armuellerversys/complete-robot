#!/usr/bin/env python3

from evdev import InputDevice, list_devices, ecodes

# Find gamepads
devices = [InputDevice(path) for path in list_devices()]

gamepad = None

for device in devices:
    print(f"{device.path}: {device.name}")

    # Look for a device which has buttons and axes
    caps = device.capabilities()

    if ecodes.EV_KEY in caps and ecodes.EV_ABS in caps:
        if gamepad is None:
            gamepad = device

if gamepad is None:
    print("\nNo gamepad found!")
    exit(1)

print("\nUsing:")
print(f"  {gamepad.path}")
print(f"  {gamepad.name}")
print("\nPress buttons or move sticks.")
print("Press Ctrl+C to exit.\n")

for event in gamepad.read_loop():

    if event.type == ecodes.EV_KEY:
        key_name = ecodes.KEY.get(event.code, f"KEY_{event.code}")

        if event.value == 1:
            state = "PRESSED"
        elif event.value == 0:
            state = "RELEASED"
        else:
            state = f"VALUE={event.value}"

        print(
            f"BUTTON: code={event.code:3d} "
            f"name={key_name:20s} {state}"
        )

    elif event.type == ecodes.EV_ABS:
        abs_name = ecodes.ABS.get(event.code, f"ABS_{event.code}")

        print(
            f"AXIS:   code={event.code:3d} "
            f"name={abs_name:10s} value={event.value}"
        )
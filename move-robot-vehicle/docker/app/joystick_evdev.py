from evdev import InputDevice, categorize, ecodes

DEVICE = "/dev/input/event5"

device = InputDevice(DEVICE)

print("Device:", device.name)
print("Path:", device.path)
print("Phys:", device.phys)
print()
print("Capabilities:")
print(device.capabilities(verbose=True))
print()
print("Listening for events...")
print("Move sticks and press buttons.")
print("Ctrl-C to exit.")
print()

for event in device.read_loop():

    if event.type == ecodes.EV_ABS:
        print(
            "ABS:",
            categorize(event)
        )

    elif event.type == ecodes.EV_KEY:
        print(
            "KEY:",
            categorize(event)
        )
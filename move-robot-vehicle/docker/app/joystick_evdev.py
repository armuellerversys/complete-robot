from evdev import InputDevice, categorize, ecodes

DEVICE = "/dev/input/event5"
# Axis normalization configuration
AXIS_MAX = 32767
DEADZONE = 0.1

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

def normalize_axis(value):
        """Converts raw analog input (-32768 to 32767) to floating scale (-1.0 to 1.0)"""
        norm = value / AXIS_MAX
        if abs(norm) < DEADZONE:
            return 0.0
        return norm

for event in device.read_loop():

    if event.type == ecodes.EV_ABS:
        #print( f"ABS:  {categorize(event)} - Value: {event.value}")
        #if event.code == ecodes.ABS_Y:
        #    axis_y = normalize_axis(event.value)
        #    print("Axis Y:", axis_y)
        if event.code == ecodes.ABS_X:
           axis_x = normalize_axis(event.value)
           print("Axis X:", axis_x)

    elif event.type == ecodes.EV_KEY:
        print("KEY:", categorize(event))

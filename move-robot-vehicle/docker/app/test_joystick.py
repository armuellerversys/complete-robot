from evdev import InputDevice, list_devices

for path in list_devices():
    dev = InputDevice(path)
    print(path, ":", dev.name)
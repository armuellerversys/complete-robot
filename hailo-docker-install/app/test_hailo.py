import hailo_platform.pyhailort as h
print(h.__file__)
print([x for x in dir(h) if "Stream" in x])
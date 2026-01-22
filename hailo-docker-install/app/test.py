import time
#import debugpy
#debugpy.listen(('0.0.0.0', 5678))


from hailo_platform import VDevice; 
v = VDevice()
print(dir(v))
p = v.get_physical_devices()[0]; 
print(dir(p))


while True:
    print ('Hello, world!')
    time.sleep(5)
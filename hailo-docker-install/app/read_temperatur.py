import debugpy
debugpy.listen(('0.0.0.0', 5678))

import time
import argparse as ap
from hailo_platform import PcieDevice
from hailo_platform import PowerMeasurementTypes, DvmTypes
from hailo_platform.pyhailort.control_object import PcieHcpControl

device_infos = PcieDevice.scan_devices()
targets = [PcieDevice(device_info=di) for di in device_infos]
temps_t = [PcieHcpControl(device_info=di) for di in device_infos]

def run_single(filename):
    try:
        with open(filename, 'w') as FH:
            while True:
                for i, target in enumerate(targets):
                    ##current = target.control.power_measurement(DvmTypes.AUTO, PowerMeasurementTypes.POWER)
                    temp = temps_t[i].get_chip_temperature().ts0_temperature
                    #print('[{}:{}] {:.3f}W {:.3f}C'.format(device_infos[i].bus_id,device_infos[i].dev_id, current, temp), end='\r')
                    #FH.write('[{}:{}] {:.3f}W {:.3f}C\n'.format(device_infos[i].bus_id,device_infos[i].dev_id, current, temp))
                    print(f"Temperature: {temp}")
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print('-I- Received keyboard intterupt, exiting')


if __name__ == "__main__":
    input("continue, enter")
    run_single("hailo_device.log")

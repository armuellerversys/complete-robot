#!/usr/bin/env python3

import time
import argparse as ap
from hailo_platform import PcieDevice
from hailo_platform import PowerMeasurementTypes, DvmTypes, MeasurementBufferIndex
from hailo_platform.pyhailort.control_object import PcieHcpControl

device_infos = PcieDevice.scan_devices()
targets = [PcieDevice(device_info=di) for di in device_infos]
temps_t = [PcieHcpControl(device_info=di) for di in device_infos]

def _run_periodic(filename, delay):
    for i, target in enumerate(targets):
        target.control.stop_power_measurement()
        target.control.set_power_measurement(MeasurementBufferIndex.MEASUREMENT_BUFFER_INDEX_0, DvmTypes.AUTO, PowerMeasurementTypes.POWER)
        target.control.start_power_measurement()
    try:
        with open(filename, 'w') as FH:
            while True:
                for i, target in enumerate(targets):
                    time.sleep(delay)
                    power = target.control.get_power_measurement(MeasurementBufferIndex.MEASUREMENT_BUFFER_INDEX_0, should_clear=True).average_value
                    temp = temps_t[i].get_chip_temperature().ts0_temperature
                    print('[{}:{}] {:.3f}W {:.3f}C'.format(device_infos[i].bus,device_infos[i].device, power, temp), end='\r')
                    FH.write('[{}:{}] {:.3f}W {:.3f}C\n'.format(device_infos[i].bus,device_infos[i].device, power, temp))
    except KeyboardInterrupt:
        print('-I- Received keyboard intterupt, exiting')

    for i, target in enumerate(targets):
        target.control.stop_power_measurement()

def _run_single(filename):
    try:
        with open(filename, 'w') as FH:
            while True:
                for i, target in enumerate(targets):
                    current = target.control.power_measurement(DvmTypes.AUTO, PowerMeasurementTypes.POWER)
                    temp = temps_t[i].get_chip_temperature().ts0_temperature
                    print('[{}:{}] {:.3f}W {:.3f}C'.format(device_infos[i].bus_id,device_infos[i].dev_id, current, temp), end='\r')
                    FH.write('[{}:{}] {:.3f}W {:.3f}C\n'.format(device_infos[i].bus_id,device_infos[i].dev_id, current, temp))
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print('-I- Received keyboard intterupt, exiting')

if __name__ == "__main__":
    parser = ap.ArgumentParser()
    parser.add_argument('--mode', help='Choose the measurement mode [periodic|single]', type=str, default='periodic')
    parser.add_argument('--delay', help='Choose the measurement delay for the periodic mode', type=int, default='1')
    parser.add_argument('--out', help='Output file', type=str, default='current_temp_readouts.txt')
    args = parser.parse_args()
    if args.mode == 'periodic':
        _run_periodic(args.out, args.delay)
    else:
        _run_single(args.out)

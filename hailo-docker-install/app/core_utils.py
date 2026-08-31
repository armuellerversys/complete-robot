import logging
import socket
import psutil

class CoreUtils:
    def __init__(self):
        self.logger = self.getLogger()

    @staticmethod
    def getLogger(name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # CHECK if logger already has handlers before adding a new one
        if not logger.handlers: 
            # create console handler with a higher log level
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
            ch.setFormatter(formatter)
            
            # add the handler to the logger
            logger.addHandler(ch)
            
        return logger

    @staticmethod
    def get_lan_ip():
        # Try to find LAN IP dynamically
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # This IP is never actually contacted; it's just to determine the local IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            return ip

    @staticmethod
    def get_cpu_temp():
        try:
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                return temps['cpu_thermal'][0].current
        except Exception:
            pass
        return 0.0

    @staticmethod
    def get_cpu_percent():
        return psutil.cpu_percent()

    @staticmethod
    def get_ram_available():
        return psutil.virtual_memory().available

    @staticmethod
    def get_ram_percentage():
        return psutil.virtual_memory().percent


    
class RobotStopException(Exception):
    """Custom exception to break out of all control loops immediately."""
    pass  
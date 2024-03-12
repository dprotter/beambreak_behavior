import time
import sys
from concurrent.futures import ThreadPoolExecutor
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    print('RPi.GPIO not found')
    from .Fake_handlers import Fake_GPIO, Fake_timestamp_writer
    GPIO = Fake_GPIO()

import queue

# from adafruit docs:
import time
import board
import busio
import digitalio as dio
from adafruit_mcp230xx.mcp23017 import MCP23017
from functools import partial

# Initialize the I2C bus:
i2c = busio.I2C(board.SCL, board.SDA)

mcp = MCP23017(i2c)  # MCP23017


class IR_beambreak:
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup', timestamp_writer = None):
        ''''''
        self.timestamp_writer = timestamp_writer if not timestamp_writer == None else Fake_timestamp_writer()
        self.pin_number = pin_number
        self.pu_pd = pullup_pulldown    
        self.pin = mcp.get_pin(pin_number)
        self.pin.direction = dio.Direction.INPUT
        self.pin.pull = dio.Pull.UP if self.pu_pd == 'pullup' else dio.Pull.DOWN
        self.blocked_value = 1    
    
    def callback(self, func_list):
        if not isinstance(func_list, list):
            func_list = [func_list]
        
        for func in func_list():
            func()
    
    def is_blocked(self):
        return self.pin.value == self.blocked_value
        
    
        
class interrupt_tester:
    def __init__(self, pin_list):
        ''''''
        
    def print_interrupt(port):
        """Callback function to be called when an Interrupt occurs."""
        for pin_flag in mcp.int_flag:
            print("Interrupt connected to Pin: {}".format(port))
            print("Pin number: {} changed to: {}".format(pin_flag, self.pin_dict[pin_flag].value))
        mcp.clear_ints()
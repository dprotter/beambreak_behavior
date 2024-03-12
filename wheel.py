import time as time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)


class Wheel:
    
    def __init__(self, pin, id) -> None:
        self.pin = pin
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.ID = id
        self.reads = 0
    
    def setup_callback(self):
        GPIO.add_event_detect(self.pin, GPIO.RISING, callback = self.iterate)
    
    def iterate(self):
        self.reads += 1
        print(f'{self.ID}: {self.reads}')
    
    def get_ID(self):
        return self.ID
    
    
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
try: 
    from adafruit_servokit import ServoKit
    SERVO_KIT = ServoKit(channels=16)
except Exception as e:
    print(e)
    print('servokit not found')
    SERVO_KIT = None
    
import queue
import inspect

thread_executor = ThreadPoolExecutor(max_workers = 20)

def thread_it(func):
        '''simple decorator to pass function to our thread distributor via a queue. 
        these 4 lines took about 4 hours of googling and trial and error.
        the returned 'future' object has some useful features, such as its own task-done monitor. '''
        
        def pass_to_thread(self, *args, **kwargs):
            bound_args = inspect.signature(func).bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            bound_args_dict = bound_args.arguments

            new_kwargs = {k:v for k, v in bound_args_dict.items() if k not in ('self')}
            #print(f'submitting {func}')
            future = thread_executor.submit(func, self, **new_kwargs)
            return future
        return pass_to_thread
    
class FakeTimestampManager:
    def __init__(self, *args, **kwargs):
        ''''''
        
    
    def write_timestamp(self, *args, **kwargs):
        print(f'writing a timestamp {args} {kwargs}')
        pass
    
class IR_beambreak:
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup', timestamp_writer = None):
        ''''''
        self.timestamp_writer = timestamp_writer if not timestamp_writer == None else FakeTimestampManager()
        self.pin_number = pin_number
        self.pu_pd = pullup_pulldown    
        self.pin = pin_number
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.testing = False
    
    def stop_testing(self):
        self.testing = False
    def set_callback(self, func):
         GPIO.add_event_detect(self.pin, GPIO.FALLING, callback = func)
        
    '''def callback(self, func_list):
        if not isinstance(func_list, list):
            func_list = [func_list]
        
        for func in func_list():
            func()'''
    
    def is_blocked(self):
        return self.pin.value == self.blocked_value
    def clear_callback(self):
        GPIO.remove_event_detect(self.pin)
    @thread_it
    def test_IR_with_LED(self, LED):        
        print('beginning LED test')
        self.testing = True
        try:
            while self.testing:
                if GPIO.input(self.pin) == 0:
                    
                    LED.set_on()
                else:
                    LED.set_off()
                time.sleep(0.05)
        except:
            LED.set_off()
            print(f'done with IR test for pin {self.pin}')
        LED.set_off()
                    
class Button:
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup', timestamp_writer = None):
        ''''''
        self.timestamp_writer = timestamp_writer if not timestamp_writer == None else FakeTimestampManager()
        self.pin = pin_number
        self.pu_pd = pullup_pulldown 
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.blocked_value = 1    
    
    def set_callback(self, func, bouncetime = 500):
         GPIO.add_event_detect(self.pin, GPIO.FALLING, callback = func)
    def clear_callback(self):
        GPIO.remove_event_detect(self.pin)

class Beambreak_LED_Button_Combo:
    def __init__(self, beambreak, led, button, id, timestamp_writer = None, screen_writer = None):
        self.ID = id
        self.traversal_counts = 0
        self.beambreak = beambreak
        self.LED = led
        self.button = button
        self.timestamp_writer = timestamp_writer if not timestamp_writer == None else FakeTimestampManager()
        self.write_to_screen = self.write_to_screen if screen_writer == None else screen_writer.write
        self.exit = False
    
    def set_exit_to_true(self):
        self.exit = True
    
    def exit_state(self):
        self.beambreak.set_callback(self.set_exit_to_true)
        self.LED.flash(frequency = 0.5, interrupt_func = self.exit_func)
        
    def exit_func(self):
        return self.exit
    
    def entry_state(self, reward_time = 45):
        ''''''
        print('entry state')
        self.reward_time = reward_time
        self.LED.set_on()
        self.button.set_callback(self.ready_state)
    
    def ready_state(self, channnel):
        self.beambreak.clear_callback()
        self.button.clear_callback()
        print('ready state')
        self.write_to_screen(f'traversal_counts for {self.ID}: {self.traversal_counts}')
        self.timestamp_writer.write_timestamp((self.ID, time.time(), 'reset'))
        self.LED.set_off()
        self.beambreak.set_callback(self.beam_broken_state)

    def beam_broken_state(self, channel):
        self.beambreak.clear_callback()
        self.button.clear_callback()
        print('beam_broken state')
        self.traversal_counts += 1
        self.write_to_screen(f'traversal_counts for {self.ID}: {self.traversal_counts}')
        self.timestamp_writer.write_timestamp((self.ID, time.time(), 'beam break'))
        
        start = time.time()
        while time.time() - start < self.reward_time:
            time.sleep(0.1)
        self.LED.set_on()
        self.button.set_callback(self.ready_state)
    
    def write_to_screen(self, message):
        print(f'beambreak {self.ID}:\n{message}\n\n')  

class LED:
    def __init__(self, HAT_pin):
        ''''''
        self.channel = SERVO_KIT._pca.channels[HAT_pin]
        self.output_on = self.set_active_HAT
        self.output_off = self.set_inactive_HAT
        self.type = 'HAT'
        self.set_on = self.set_active_HAT
        self.set_off = self.set_inactive_HAT
        
    def set_active_HAT(self, percent = 100):
        self.active = True
        self.channel.duty_cycle = self.hat_PWM_hex_from_percent(percent)
        
    def hat_PWM_hex_from_percent(self, percent = 100, int_bit = 16, max_value = None):
        vals = {16:65535, 12: 4095, 8: 255}
        if max_value:
            max_value = max_value
        else:
            try:
                max_val = vals[int(int_bit)]
            except:
                print(f'expected a int_bit value of 8, 12, or 16, but received: {int_bit}. you may also pass a max_value for your PWM generator directly as max_value')
        integer = int(percent * max_val / 100)
        return integer
        
    def set_inactive_HAT(self):
        self.active = False
        self.channel.duty_cycle = 0
    
    @thread_it
    def flash(self, frequency, interrupt_func):
        '''given a frequency in seconds, flash on for 1/2, off for 1/2 of that 
        frequency until interrupt_func returns True'''
        half_freq = frequency/2
        while not interrupt_func():
            self.set_on()
            start = time.time()
            while (time.time() - start) < half_freq:
                if interrupt_func():
                    break
                else:
                    time.sleep(0.1)
            self.set_off()
            start = time.time()
            if not interrupt_func():
                while (time.time() - start) < half_freq:
                    if interrupt_func():
                        break
                    else:
                        time.sleep(0.1)
        self.set_off()
            
            
        

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
        print('using fake timestamp writer')
        
    def create_file(self, *args, **kwargs):
        pass
    
    def write_timestamp(self, *args, **kwargs):
        print(f'writing a timestamp {args} {kwargs}')
        pass
    
class IR_beambreak:
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup', timestamp_writer = None):
        ''''''
        self.pin_number = pin_number
        self.pu_pd = pullup_pulldown    
        self.pin = pin_number
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.testing = False
        self.blocked_value = 0
    
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
        return GPIO.input(self.pin) == self.blocked_value
    
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
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup'):
        ''''''
        self.pin = pin_number
        self.pu_pd = pullup_pulldown 
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.blocked_value = 1    
    
    def set_callback(self, func, bouncetime = 1000):
        print(f'setting callback on {self.pin}')
        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback = func)
    def clear_callback(self):
        GPIO.remove_event_detect(self.pin)

class Two_Beambreak_LED_Button_Combo:
    def __init__(self, beambreak_1, beambreak_2, led, button, box_ID, notes_1 = None, notes_2 = None, timestamp_writer = None, screen_writer = None):
        self.ID = box_ID
        self.traversal_counts = {1:0, 2:0}
        self.beambreak_1 = beambreak_1
        self.beambreak_2 = beambreak_2
        self.LED = led
        self.button = button
        self.timestamp_writer = FakeTimestampManager() if not timestamp_writer else timestamp_writer
        self.write_to_screen = self.write_to_screen if screen_writer == None else screen_writer.write
        self.exit = False
        self.notes_1 = notes_1 if notes_1 else ''
        self.notes_2 = notes_2 if notes_2 else ''
        
        self.started = False
        
        self.header_list = ['ID', 'beam', 'elapsed_time', 'event','count', 'latency','notes']
        self.timestamp_writer.create_file(self.header_list)
        self.state = None
    
    def shut_down(self, channel = None):
        '''func to finish this IR pair run. turn off LEDs and set exit attribute to true'''
        self.LED.set_off()
        self.set_exit_to_true()
        
    def set_exit_to_true(self, channel = None):
        self.exit = True
    
    def exit_state(self):
        ''''''
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.state = 'exit'
        self.button.clear_callback()
        self.button.set_callback(self.shut_down)
        self.LED.set_on()
        
    def exit_func(self):
        return self.exit
    
    def entry_state(self, reward_time = 45):
        ''''''
        print('entry state')
        if self.beambreak_1.is_blocked():
            print(f'box {self.name} beambreak 1 is blocked')
        
        if self.beambreak_1.is_blocked():
            print(f'box {self.name} beambreak 2 is blocked')
        
        if self.beambreak_1.is_blocked() or self.beambreak_2.is_blocked():
            print('waiting for beambreaks to be unblocked')
            while self.beambreak_1.is_blocked() or self.beambreak_2.is_blocked():
                time.sleep(0.5)
        
        self.state = 'entry'
        self.reward_time = reward_time
        self.LED.set_on()
        self.button.set_callback(self.begin)
    
    def check_state(self, state_query):
        return self.state == state_query
    
    def begin(self, channel = None):
        self.button.clear_callback()
        self.start_time = time.time()
        self.started = True
        self.ready_state(channel)
        
    def ready_state(self, channel = None):
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        self.LED.set_off()
        print('ready state')
        self.state = 'ready'
        self.write_to_screen(f'traversal_counts for {self.ID}: {self.traversal_counts}')
        self.timestamp_writer.write_timestamp((self.ID, '', time.time() - self.start_time, 'reset', ''))
        self.latency_from = time.time()
        
        self.beambreak_1.set_callback(func=lambda x: self.beam_broken_state(1, self.notes_1))
        self.beambreak_2.set_callback(func=lambda x: self.beam_broken_state(2, self.notes_2))

    def beam_broken_state(self, beam_ID, notes = None):
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        self.traversal_counts[beam_ID] += 1
        print(f'\n\ntraversal_count +=1 for {beam_ID}\n{self.ID} {1} {self.notes_1}: {self.traversal_counts[1]} | {self.ID} {2} {self.notes_2}: {self.traversal_counts[2]}\n\n')
        'box_ID, beam_ID, time (since start), event, latency, notes'
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time , f'{beam_ID} traversal',self.traversal_counts[beam_ID], time.time()-self.latency_from, notes))
        
        start = time.time()
        self.state = 'reward'
        while time.time() - start < self.reward_time:
            time.sleep(0.1)
        print(f'{self.ID} reward period over')
        self.LED.flash(frequency = 0.5, interrupt_func = self.LED.interrupt_LED)
        self.button.set_callback(self.ready_state)
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time, 'reward_period_end','', '', notes))
    
    def write_to_screen(self, message):
        print(f'\n{self.ID}: {message}\n')
        
class LED:
    def __init__(self, HAT_pin):
        ''''''
        self.channel = SERVO_KIT._pca.channels[HAT_pin]
        self.output_on = self.set_active_HAT
        self.output_off = self.set_inactive_HAT
        self.type = 'HAT'
        self.set_on = self.set_active_HAT
        self.set_off = self.set_inactive_HAT
        self.is_active = False
        
        
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
    
    def flash_on(self, percent = 100):
        self.channel.duty_cycle = self.hat_PWM_hex_from_percent(percent)
        
    def flash_off(self):
        self.channel.duty_cycle = 0
    
    def is_active(self):
        return self.active
    
    def interrupt_LED(self):
        '''return True when attribute self.active is False to interrupt ongoing flashing'''
        
        return not self.active
    
    @thread_it
    def flash(self, frequency, interrupt_func, percent = 100, ):
        '''given a frequency in seconds, flash on for 1/2, off for 1/2 of that 
        frequency until interrupt_func returns True'''
        
        
        half_freq = frequency/2
        self.active = True
        while not interrupt_func():
            self.flash_on(percent = percent)
            start = time.time()
            while (time.time() - start) < half_freq:
                if interrupt_func():
                    break
                else:
                    time.sleep(0.1)
            
            self.flash_off()
            start = time.time()
            if not interrupt_func():
                while (time.time() - start) < half_freq:
                    if interrupt_func():
                        break
                    else:
                        time.sleep(0.1)
        
        self.set_off()
            
            
        

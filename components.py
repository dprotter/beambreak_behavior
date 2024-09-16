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
from functools import partial
import functools as functools

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

def confirm_state_before_callback_execution(self_obj, callback_func, state_func, failure_func = None):
        '''simple wrapper to confirm ir beambreak before executing a callback'''
        
        cycles_required = 2

        failure_cycles = 20
        
        success_rate_limit = 0.9
        for i in range(cycles_required):
            if not state_func():
                if isinstance(callback_func, functools.partial):
                    print(f'\ncallback func {callback_func.func.__name__} triggered, but could not confirm signal --> polling for {failure_cycles} expecting {success_rate_limit} match')
                else:
                     print(f'\ncallback func {callback_func.__name__} triggered, but could not confirm signal --> polling for {failure_cycles} expecting {success_rate_limit} match')
                break
            else:
                time.sleep(0.015)
        if i == cycles_required-1:
            callback_func()
        else:
            failure_list = [state_func() for _ in range(failure_cycles)]
            measured_rate = sum(failure_list)/failure_cycles
            print(f'failure of conformation state success rate = {measured_rate}\n')
            if measured_rate >= success_rate_limit:
                callback_func()
            elif not failure_func is None:
                
                
                if isinstance(failure_func, functools.partial):
                    print(f'utilizing failure function {failure_func.func.__name__}')
                else:
                    print(f'utilizing failure function {failure_func.__name__}')
                failure_func()
            else:
                pass
            





            
        


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
    
    def __init__(self, pin_number, pullup_pulldown = 'pullup', 
                 timestamp_writer = None, ID = None, notes = None):
        ''''''
        self.pin_number = pin_number
        self.pu_pd = pullup_pulldown    
        self.pin = pin_number
        GPIO.setup(self.pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        self.testing = False
        self.blocked_value = 0
        self.ID = ID
        self.name = notes
        self.start_time = 0
        self.beam_break_count = 0
        self.timestamp_writer = FakeTimestampManager() if not timestamp_writer else timestamp_writer
        self.notes = notes if notes else ''

    def begin(self, start_time):
        self.start_time = start_time
        self.testing = True
    
    def stop_testing(self):
        self.testing = False
        
    def set_callback(self, func, edge = 'falling', failure_func = None):
        self.clear_callback()
        if edge == 'rising':
            wrapper = partial(confirm_state_before_callback_execution,  callback_func = func, state_func = self.is_unblocked, failure_func = failure_func)
            GPIO.add_event_detect(self.pin, GPIO.RISING, callback = wrapper, bouncetime = 100)
        elif edge == 'falling':
            wrapper = partial(confirm_state_before_callback_execution,  callback_func = func, state_func = self.is_blocked, failure_func = failure_func)
            GPIO.add_event_detect(self.pin, GPIO.FALLING, callback = wrapper, bouncetime = 100)
        else:
            raise Exception(f'edge must be "falling" or "rising" but was {edge}')
    
    def is_blocked(self):
        return GPIO.input(self.pin) == self.blocked_value
    
    def is_unblocked(self):
        return GPIO.input(self.pin) != self.blocked_value
    
    def record_durations(self):
        '''will block program exit until round trip from begin_duration -> submit_duration -> record_durations'''
        #print(f'enter record durations on  {self.pin}')
        self.clear_callback()
        
        if self.testing:
             #can enter in a blocked state if state func was not confirmed by wrapper of set_callback
            if self.is_blocked():
                #print('\n\nentering record durations in a blocked state\n\n')
                #directly check state with confirm_state func. go to begin_duration with current time. return to this func if state is not confirmed
                confirm_state_before_callback_execution(self_obj = self, callback_func=partial(self.begin_duration), 
                                                        state_func = self.is_blocked, 
                                                        failure_func = self.record_durations)
            else:
                #if not blocked, set callback as usual 
                #print(f'setting callback for begin_duration as usual on {self.pin}')
                self.set_callback(func=partial(self.begin_duration), 
                                    edge = 'falling', 
                                    failure_func = self.record_durations)
        else:
            self.clear_callback()
    
    def begin_duration(self, incoming_time = None):
        '''this function can take an incoming time for recovery if a rising edge cannot be confirmed before
        moving to "submit_duration" '''
        #for 2 beambreak behavior rig ['ID', 'beam', 'elapsed_time', 'event','count', 'latency','notes']
        self.clear_callback()
        
        if incoming_time is None:
            incoming_time = time.time()
        
        #can enter in an unblocked state
        if self.is_unblocked():
            #print('\n\nentering begin_duration in an unblocked state\n\n')
            #directly check state with confirm_state func. go to begin_duration with current time. return to this func if state is not confirmed
            partial_in_case_of_callback_failure = partial(self.begin_duration, incoming_time)
            confirm_state_before_callback_execution(self_obj = self, callback_func=partial(self.submit_duration, incoming_time), 
                                                    state_func = self.is_unblocked, 
                                                    failure_func = partial_in_case_of_callback_failure)
        else:
            print(f'begin duration on ir pin{self.pin}')
            self.timestamp_writer.write_timestamp((self.ID, self.name, incoming_time - self.start_time, 
                                                'beam_break_initiation', self.beam_break_count, 
                                                '', self.notes))

            #set the callback with rising edge detection. if it fails, return to the start of begin_duration and check beam there
            partial_in_case_of_callback_failure = partial(self.set_callback, partial(self.submit_duration, incoming_time), edge = 'rising', 
                                            failure_func = partial(self.begin_duration, incoming_time))
            self.set_callback(func=partial(self.submit_duration, incoming_time), edge = 'rising', 
                                            failure_func = partial_in_case_of_callback_failure)
            
    
    def submit_duration(self, incoming_time):
        self.clear_callback()
        #can enter in an unblocked state if state func was not confirmed by wrapper of set_callback
        now = time.time()
        duration = now - incoming_time
        self.beam_break_count+=1
        print(f'submit duration {duration} count {self.beam_break_count} on ir pin{self.pin} / {self.notes}\n')
        #for 2 beambreak behavior rig ['ID', 'beam', 'elapsed_time', 'event','count', 'latency','notes']
        self.timestamp_writer.write_timestamp((self.ID, self.name, now - self.start_time, 
                                               'beam_break_duration', self.beam_break_count, 
                                               duration, self.notes))
        
        self.record_durations()
        
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
        if pullup_pulldown == 'pullup':
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.pressed_val = 0
            
        elif pullup_pulldown == 'pulldown':
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.pressed_val = 1    
    
    def is_pressed(self):
        return GPIO.input(self.pin) == self.pressed_val
    
    def set_callback(self, func, bouncetime = 100):
        print(f'setting callback on {self.pin}')
        wrapper = partial(confirm_state_before_callback_execution, callback_func = func, state_func = self.is_pressed)
        GPIO.add_event_detect(self.pin, GPIO.FALLING, callback = wrapper, bouncetime = bouncetime)

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
        print(f'{self.ID} shut down')
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
        print(f'{self.ID} in exit state')
        self.LED.flash(frequency = 0.2, interrupt_func = self.LED.interrupt_LED)
        
    def exit_func(self):
        return self.exit
    
    @thread_it
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
        self.latency_from = time.time()
        self.button.set_callback(self.begin)
    
    def check_state(self, state_query):
        return self.state == state_query
    
    def begin(self, channel = None):
        self.button.clear_callback()
        self.start_time = time.time()
        self.started = True
        self.ready_state(channel)
    
    @thread_it
    def reward_cancel_state(self, beam_ID, notes):
        print('reward canceled state')
        self.state = 'reward_canceled'
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time, 'reward_canceled', '', time.time()-self.latency_from, notes))
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        self.ready_state()

    def ready_state(self, channel = None):
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        self.LED.set_off()
        print('ready state')
        self.state = 'ready'
        #self.write_to_screen(f'traversal_counts for {self.ID}: {self.traversal_counts}')
        self.timestamp_writer.write_timestamp((self.ID, '', time.time() - self.start_time, 'reset', '', time.time()-self.latency_from, ''))
        self.latency_from = time.time()
        
        self.beambreak_1.set_callback(func=partial(self.beam_broken_state, 1, self.notes_1))
        self.beambreak_2.set_callback(func=partial(self.beam_broken_state, 2, self.notes_2))

    @thread_it
    def beam_broken_state(self, beam_ID, notes = None):
        self.LED.set_on()
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        
        self.traversal_counts[beam_ID] += 1
        print(f'\n\ntraversal_count +=1 for {beam_ID}\n{self.ID} {1} {self.notes_1}: {self.traversal_counts[1]} | {self.ID} {2} {self.notes_2}: {self.traversal_counts[2]}\n\n')
        'box_ID, beam_ID, time (since start), event, latency, notes'
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time , f'{beam_ID} traversal',self.traversal_counts[beam_ID], time.time()-self.latency_from, notes))
        self.button.set_callback(func=partial(self.reward_cancel_state, beam_ID, notes))
        start = time.time()
        self.state = 'reward'
        self.latency_from = time.time()
        while time.time() - start < self.reward_time and self.state == 'reward':
            time.sleep(0.1)
        if self.state == 'reward':
            print(f'{self.ID} reward period over')
            self.LED.flash(frequency = 0.5, interrupt_func = self.LED.interrupt_LED)
            self.button.clear_callback()
            self.button.set_callback(self.ready_state)
            self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time, 'reward_period_end','', '', notes))
            self.latency_from = time.time()
        
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
            
            
class Four_Beambreak_LED_Button_Combo:
    def __init__(self, beambreak_1, beambreak_2, beambreak_3, beambreak_4, led, button, box_ID, notes_1 = None, notes_2 = None, notes_3 = None, notes_4 = None, timestamp_writer = None, screen_writer = None):
        self.ID = box_ID
        self.traversal_counts = {1:0, 2:0}
        
        #these are traversal beambreaks
        self.beambreak_1 = beambreak_1
        self.beambreak_2 = beambreak_2
        
        #these are top-of-wall beambreaks
        self.beambreak_3 = beambreak_3
        self.beambreak_4 = beambreak_4
        self.beambreak_3.ID = self.ID
        self.beambreak_4.ID = self.ID
        self.all_breaks =[self.beambreak_1, self.beambreak_2, self.beambreak_3, self.beambreak_4]
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
        print(f'{self.ID} shut down')
        self.LED.set_off()
        self.set_exit_to_true()
        
    def set_exit_to_true(self, channel = None):
        self.exit = True
    
    def exit_state(self):
        ''''''
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.beambreak_3.clear_callback()
        self.beambreak_4.clear_callback()
        self.state = 'exit'
        self.button.clear_callback()
        self.button.set_callback(self.shut_down)
        print(f'{self.ID} in exit state')
        self.LED.flash(frequency = 0.2, interrupt_func = self.LED.interrupt_LED)
        
    def exit_func(self):
        return self.exit
    
    @thread_it
    def entry_state(self, reward_time = 45):
        ''''''
        print('entry state')
        
        if any([b.is_blocked() for b in self.all_breaks]):
            blocked = [b.name for b in self.all_breaks]
            print(f'blocked beams: {blocked}')
            
            if any([b.is_blocked() for b in self.all_breaks]):
                print('waiting for beambreaks to be unblocked')
                while any([b.is_blocked() for b in self.all_breaks]):
                    print([f'{b.is_blocked()}:{b.ID}\{b.pin}' for b in self.all_breaks])
                    time.sleep(0.5)
        
        self.state = 'entry'
        self.reward_time = reward_time
        self.LED.set_on()
        self.latency_from = time.time()
        self.button.set_callback(self.begin)
    
    def check_state(self, state_query):
        return self.state == state_query
    
    def begin(self, channel = None):
        self.button.clear_callback()
        self.start_time = time.time()
        self.started = True
        self.beambreak_3.begin(self.start_time)
        self.beambreak_4.begin(self.start_time)
        
        self.ready_state(channel)
    
    @thread_it
    def reward_cancel_state(self, beam_ID, notes):
        print('reward canceled state')
        self.state = 'reward_canceled'
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time, 'reward_canceled', '', time.time()-self.latency_from, notes))
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        self.ready_state()

    def ready_state(self, channel = None):
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.beambreak_3.record_durations()
        self.beambreak_4.record_durations()
        self.button.clear_callback()
        self.LED.set_off()
        print('ready state')
        self.state = 'ready'
        #self.write_to_screen(f'traversal_counts for {self.ID}: {self.traversal_counts}')
        self.timestamp_writer.write_timestamp((self.ID, '', time.time() - self.start_time, 'reset', '', time.time()-self.latency_from, ''))
        self.latency_from = time.time()
        
        self.beambreak_1.set_callback(func=partial(self.beam_broken_state, 1, self.notes_1))
        self.beambreak_2.set_callback(func=partial(self.beam_broken_state, 2, self.notes_2))

    @thread_it
    def beam_broken_state(self, beam_ID, notes = None):
        self.LED.set_on()
        self.beambreak_1.clear_callback()
        self.beambreak_2.clear_callback()
        self.button.clear_callback()
        
        self.traversal_counts[beam_ID] += 1
        print(f'\n\ntraversal_count +=1 for {beam_ID}\n{self.ID} {1} {self.notes_1}: {self.traversal_counts[1]} | {self.ID} {2} {self.notes_2}: {self.traversal_counts[2]}\n\n')
        'box_ID, beam_ID, time (since start), event, latency, notes'
        self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time , f'{beam_ID} traversal',self.traversal_counts[beam_ID], time.time()-self.latency_from, notes))
        self.button.set_callback(func=partial(self.reward_cancel_state, beam_ID, notes))
        start = time.time()
        self.state = 'reward'
        self.latency_from = time.time()
        while time.time() - start < self.reward_time and self.state == 'reward':
            time.sleep(0.1)
        if self.state == 'reward':
            print(f'{self.ID} reward period over')
            self.beambreak_3.clear_callback()
            self.beambreak_4.clear_callback()
            
            self.LED.flash(frequency = 0.5, interrupt_func = self.LED.interrupt_LED)
            self.button.clear_callback()
            self.button.set_callback(self.ready_state)
            self.timestamp_writer.write_timestamp((self.ID, beam_ID, time.time() - self.start_time, 'reward_period_end','', '', notes))
            self.latency_from = time.time()
        
    def write_to_screen(self, message):
        print(f'\n{self.ID}: {message}\n')
        

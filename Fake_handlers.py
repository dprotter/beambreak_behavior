class Fake_GPIO:
    def __init__(self):
        self.IN = 1
        self.OUT = 0
        self.PUD_UP = 1
        self.PUD_DOWN = 1
    def setup(self, *args,**kwargs):
        pass
    
    def input(self, pin):
        return 3

class Fake_pigpio:
    def pi():
        return Fake_pigpio_funcs()
class Fake_pigpio_funcs:
        def __init__(self):
            '''i just want to exist in peace.'''
        def set_PWM_duty_cycle(self, pin, value):
            '''just here to receive values'''
        def set_PWM_frequency(self, pin, value):
            '''just here to receive values'''

class Fake_timestamp_writer:
    def write_timestamp(*args, **kwargs):
        print(f'Fake_timestamp_writer received {args}\n{kwargs}')
    
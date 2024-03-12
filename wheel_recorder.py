from wheel import Wheel
import datetime as datetime
import os as os
import time as time
import csv
import RPi.GPIO as GPIO


save_location = '~/'
wheels_pins = [11]
animal_nums = [500] #going to make this procedurally at runtime
time_interval = 0.1 #50ms between recording. note that the wheel will still iterate
duration = 30 #30 sec for testing

def precise_sleeper(duration, get_now=time.perf_counter):
    now = get_now()
    end = now + duration
    while now < end:
        now = get_now()

def make_filepath(save_location, animal_nums):
    date = datetime.now()
    file = f'{date.month}_{date.day}_{date.year}__{date.hour}_{date.minute}__'
    for animal in sorted(animal_nums):
        file += f'{animal}_'
    return os.path.join(save_location, file)

def create_csv(filepath, animal_nums):
    with open(filepath, 'w+') as f:
        writer = csv.writer(f)
        writer.writerow(['time']+sorted(animal_nums))

def make_row(start_time, wheel_dict):
    wheel_ids = sorted(wheel_dict.keys())
    row = [wheel_dict[id].reads for id in wheel_ids]
    return [round(time.time() - start_time, 4) ] + row

def write_row(filepath, row):
     with open(filepath, 'a+') as f:
        writer = csv.writer(f)
        writer.writerow(row)
        

wheels = {animal:Wheel(pin, animal) for pin, animal in zip(wheels_pins, animal_nums)}
filepath = make_filepath(save_location, animal_nums)
create_csv(filepath, animal_nums)


start_time = time.time()
[wheel.setup_callback for _, wheel in wheels.items()]

while time.time() - start_time < duration:
    row = make_row(start_time, wheels)
    write_row(filepath, row)
    precise_sleeper(time_interval)
    
GPIO.cleanup()
print('done!')
    

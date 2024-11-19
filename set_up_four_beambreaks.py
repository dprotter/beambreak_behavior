import argparse
import os
from box import Box
parser = argparse.ArgumentParser(description='input io info')
parser.add_argument('--yaml_in', '-i',type = str, 
                    help = 'where is the csv experiments file?',
                    action = 'store')
from recording_classes import TimestampManager, default_generate_output_fname
from components import Four_Beambreak_LED_Button_Combo, IR_beambreak, Button, LED
import yaml
import datetime
import pdb
import time
from components import GPIO
from tabulate import tabulate
args = parser.parse_args()

def make_beambreak_pair(yaml_file, box_id, timestamp_writer):
    if 'side_notes' in yaml_file['animals'][box_id]:
        note_1 = yaml_file['animals'][box_id]['side_notes']['ir_1']
        note_2 = yaml_file['animals'][box_id]['side_notes']['ir_2']
        note_3 = yaml_file['animals'][box_id]['side_notes']['ir_3']
        note_4 = yaml_file['animals'][box_id]['side_notes']['ir_4']

    else:
        note_1 = f"pin {yaml_file['hardware'][box_id]['ir_1']['pin']}"
        note_2 = f"pin {yaml_file['hardware'][box_id]['ir_2']['pin']}"
        note_3 = f"pin {yaml_file['hardware'][box_id]['ir_3']['pin']}"
        note_4 = f"pin {yaml_file['hardware'][box_id]['ir_4']['pin']}"

    button = Button(yaml_file['hardware'][box_id]['button'])
    led = LED(yaml_file['hardware'][box_id]['led'])
    ir_1 = IR_beambreak(yaml_file['hardware'][box_id]['ir_1'])
    ir_2 = IR_beambreak(yaml_file['hardware'][box_id]['ir_2'])
    ir_3 = IR_beambreak(yaml_file['hardware'][box_id]['ir_3'], timestamp_writer = timestamp_writer, notes = note_3)
    ir_4 = IR_beambreak(yaml_file['hardware'][box_id]['ir_4'], timestamp_writer = timestamp_writer, notes = note_4)
    
    
        
    
    
    return Four_Beambreak_LED_Button_Combo(
                                          beambreak_1 = ir_1, 
                                          beambreak_2 = ir_2,
                                          beambreak_3 = ir_3, 
                                          beambreak_4 = ir_4,  
                                          led = led, 
                                          button = button, 
                                          box_ID = box_id, 
                                          notes_1 = note_1, 
                                          notes_2 = note_2,
                                          notes_3 = note_3, 
                                          notes_4 = note_4, 
                                          timestamp_writer = timestamp_writer)
    
    
    

if args.yaml_in:
    yaml_file = args.yaml_in
if not os.path.isfile(yaml_file):
    print('not a valid yaml. double check that filepath! see ya.')
    exit()

with open(yaml_file, 'r') as f:
    config_dict = yaml.safe_load(f)

#save the config file, timestamped just in case
date = datetime.datetime.now()
fpath = config_dict['software']['save_path']
config_filename = default_generate_output_fname('config', date)

with open(os.path.join(fpath,config_filename)+'.yaml', 'w') as outfile:
    yaml.dump(config_dict, outfile)
    

#start making boxes
boxes = []

for box_ID in config_dict['hardware'].keys():
    box = Box(box_ID)
    filename = default_generate_output_fname(config_dict['animals'][box_ID]['focal'], date)+'.csv'
    writer = TimestampManager(fpath, filename)
    beambreak_pair = make_beambreak_pair(config_dict, box_ID, writer)

    box.add_component(beambreak_pair, 'ir_pair')
    boxes += [box]
    

time.sleep(1)
def print_pin_status(box_list):
    num_IRs = len(box_list)*2

    print("\033c", end="")
    
    status = []
    for box in box_list:
        ir1 = box.ir_pair.beambreak_1
        ir2 = box.ir_pair.beambreak_2
        ir3 = box.ir_pair.beambreak_3
        ir4 = box.ir_pair.beambreak_4

        
        status += [[box.name, 'ir_1', ir1.is_blocked(), 'ir_3', ir3.is_blocked(), 'ir_2', ir2.is_blocked(), 'ir_4', ir4.is_blocked()]]
    print(tabulate(status, headers = ['box', 'ir', 'status', 'ir', 'status','ir', 'status', 'ir', 'status']))
    time.sleep(0.05)

try:
    while True:
        print_pin_status(boxes)
        time.sleep(0.05) 

except KeyboardInterrupt:
    print('\n\ncleaning up')
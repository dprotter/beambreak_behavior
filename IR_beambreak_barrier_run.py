import argparse
import os
from box import Box
parser = argparse.ArgumentParser(description='input io info')
parser.add_argument('--yaml_in', '-i',type = str, 
                    help = 'where is the csv experiments file?',
                    action = 'store')
from recording_classes import TimestampManager, default_generate_output_fname
from components import Two_Beambreak_LED_Button_Combo, IR_beambreak, Button, LED
import yaml
import datetime
import pdb
import time
from components import GPIO
import csv
args = parser.parse_args()

def make_beambreak_pair(yaml_file, box_id, timestamp_writer):
    button = Button(yaml_file['hardware'][box_id]['button'])
    led = LED(yaml_file['hardware'][box_id]['led'])
    ir_1 = IR_beambreak(yaml_file['hardware'][box_id]['ir_1'])
    ir_2 = IR_beambreak(yaml_file['hardware'][box_id]['ir_2'])
    
    if 'side_notes' in yaml_file['animals'][box_id]:
        note_1 = yaml_file['animals'][box_id]['side_notes']['ir_1']
        note_2 = yaml_file['animals'][box_id]['side_notes']['ir_2']
        
    else:
        note_1, note_2 = None, None
    
    return Two_Beambreak_LED_Button_Combo(beambreak_1 = ir_1, 
                                          beambreak_2 = ir_2, 
                                          led = led, 
                                          button = button, 
                                          box_ID = box_id, 
                                          notes_1 = note_1, 
                                          notes_2 = note_2, 
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
    box.ir_pair.entry_state(reward_time = config_dict['software']['reward_period'])
    boxes += [box]

i = 0  
while any([not b.ir_pair.started for b in boxes]):
    i+=1
    if i%15 == 0:
        print('waiting to start')
    time.sleep(0.1)
print('done waiting to start')
cycle = time.time()
while any([cycle - b.ir_pair.start_time < config_dict['software']['total_time'] for b in boxes]) or any([not b.ir_pair.exit for b in boxes]):
    [b.ir_pair.exit_state() for b in boxes if cycle - b.ir_pair.start_time > config_dict['software']['total_time'] if not b.ir_pair.state == 'reward' if not b.ir_pair.state == 'exit']
    time.sleep(0.250)
    cycle = time.time()
    
GPIO.cleanup()


header = ['box', 'animal', 'IR_1_traversals','IR_1_notes', 'IR_2_traversals','IR_2_notes', 'novel_ID']


summary_file = default_generate_output_fname('summary',date) + '.csv'
summary_fpath = os.path.join(fpath, summary_file)
with open(summary_fpath, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(header)

for box in boxes:
    ir = box.ir_pair
    data=[box.name, 
            config_dict['animals'][box.name]['focal'], 
            ir.traversal_counts[1], 
            ir.notes_1,
            ir.traversal_counts[2],
            ir.notes_2,
            config_dict['animals'][box.name]['novel']]
    
    with open(summary_fpath, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(data)





    
    
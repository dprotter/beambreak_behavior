
from components import *

class Box:
    
    def __init__(self, filepath, animal_number, box_ID, timestamp_writer = None):
        self.file = filepath
        self.animal = animal_number
        self.box_ID = box_ID
        self.timestamp_writer = timestamp_writer if timestamp_writer else self.fake_writer

        
        
    

from components import *

class Box:
    
    def __init__(self, name):
        self.name = name
    
    def add_component(self, component, name):
        setattr(self, name, component)
        

        
        
    
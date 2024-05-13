class TimestampSaver:
    
    def __init__(self, header, filepath, delimeter = ','):
        self.fp = filepath
        self.delimter = delimeter
        #list of values in header
        self.header = header
    
    def create_file(self):
        with open(self.fp, 'x') as f:
            header_string =  self.delimter.join(str(bit) for bit in self.header)
            f.write(header_string)            
    
    def write_line(self, line):
        with open(self.fp, 'a') as f:
            line_string =  self.delimter.join(str(bit) for bit in line)
            f.write(line_string)
            
    
    
    
    
    
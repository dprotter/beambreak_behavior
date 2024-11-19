from components import thread_it, thread_executor
import os
import queue

def default_generate_output_fname(vole, date, vole_2 = None, title = ''):
        
        if vole_2:
            fdate = f'{date.month}_{date.day}_{date.year}___{date.hour}_{date.minute}_{date.second}_'
            fname = f'{vole}_{vole_2}_{fdate}_{title}'
        else:
            fdate = f'{date.month}_{date.day}_{date.year}___{date.hour}_{date.minute}_{date.second}_'
            fname = f'{vole}_{fdate}_{title}'
        
        return fname
        
        
class TimestampManager:
    def __init__(self, path, fname, delimeter = ','):
        ''''''
        print('making a timestamp writer')
        self.delimter = delimeter
        #list of values in header

        self.fp = os.path.join(path, fname)
        self.queue = queue.Queue()
        self.writing = False
        
    
    def create_file(self, header):
        with open(self.fp, 'x') as f:
            header_string =  self.delimter.join(str(bit) for bit in header)
            f.write(header_string+'\n')            
    
    def shut_down(self):
        if not self.queue.empty():
            self._write_timestamp()
            self.queue.join()
            
    def write_timestamp(self, line):
        line_string =  self.delimter.join(str(bit) for bit in line)+'\n'
        self.queue.put(line_string)
        if not self.writing:
            self._write_timestamp()
            
        
    @thread_it 
    def _write_timestamp(self):
        self.writing = True
        with open(self.fp, 'a') as f:
            while not self.queue.empty():
                f.write(self.queue.get())
        self.writing = False
                
    
        
    
    
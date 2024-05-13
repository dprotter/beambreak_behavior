from components import IR_beambreak, LED
import time as time

led = LED(0)
test_beam = IR_beambreak(20)
test_beam.test_IR_with_LED(led)
start = time.time()
try:
    while time.time() - start <5:
        time.sleep(0.05)
except:
    led.set_off()
    
test_beam.stop_testing()  



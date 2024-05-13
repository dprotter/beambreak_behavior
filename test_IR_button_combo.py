from components import IR_beambreak, LED, Beambreak_LED_Button_Combo, Button
import time as time

led = LED(0)
test_beam = IR_beambreak(20)
button = Button(4)
box_side= Beambreak_LED_Button_Combo(test_beam, led, button, id = 'test')
box_side.entry_state(reward_time = 4)
start = time.time()
try:
    while time.time() - start <45:
        time.sleep(0.05)
except:
    led.set_off()

box.exit_state()



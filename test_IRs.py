from components import IR_beambreak, LED


led = LED(0)
test_beam = IR_beambreak(20)
test_beam.test_IR_with_LED(led)
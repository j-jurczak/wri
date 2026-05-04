#!/usr/bin/env python3
from ev3dev2.motor import MoveTank, MediumMotor, SpeedPercent, OUTPUT_B, OUTPUT_C, OUTPUT_D
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.button import Button
from time import sleep

drive = MoveTank(OUTPUT_B, OUTPUT_C)
dripper = MediumMotor(OUTPUT_D)

left_sensor = ColorSensor('in1')
right_sensor = ColorSensor('in4')
btn = Button()

BASE_SPEED = -20      
KP = 0.6
BLACK_THRESHOLD = 10
LEFT_THRESHOLD_DOWN = 14
RIGHT_THRESHOLD_DOWN = 18
LEFT_THRESHOLD_UP = 25
RIGHT_THRESHOLD_UP = 40
TURNING_TIME = 1.5

def follow_line():
    print("Program Running... Press the back button to stop.")
    
    left_sensor.mode = 'COL-COLOR'
    right_sensor.mode = 'COL-COLOR'

    while not btn.backspace:
        left_val = left_sensor.color
        right_val = right_sensor.color
        #print("left_val=", left_val)
        #print("right_val=", right_val)
        #sleep(0.25)
        #continue
        left_black, right_black = left_val == 1, right_val == 1
        left_start, right_start = left_val == 3, right_val == 3
        left_end, right_end = left_val == 4, right_val == 4
        down = True
        if left_start and right_start and down:
            print("podnoszenia haka", left_val, right_val)
            dripper.on_for_degrees(SpeedPercent(10), 10)
            drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
            sleep(TURNING_TIME)
            drive.off()
            down = False
        elif left_end and right_end and not down:
            print("opuszczanie haka", left_val, right_val)
            dripper.on_for_degrees(SpeedPercent(-10), 10)
            down = True
        elif left_start and down or left_end and not down:
            #print("left color")
            drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
        elif right_start and down or right_end and not down:
            #print("right color")
            drive.on(left_speed=BASE_SPEED, right_speed=-BASE_SPEED)
        elif left_black and not right_black:
            #print("left")
            drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
        elif not left_black and right_black:
            #print("right")
            drive.on(left_speed=BASE_SPEED, right_speed=-BASE_SPEED)
        else:
            #print("forward")
            drive.on(left_speed=BASE_SPEED*KP, right_speed=BASE_SPEED*KP)
        


    drive.off()
    print("Program Stopped.")

if __name__ == "__main__":
    follow_line()

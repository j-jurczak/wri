#!/usr/bin/env python3
from ev3dev2.motor import MoveTank, OUTPUT_B, OUTPUT_C
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.button import Button

drive = MoveTank(OUTPUT_B, OUTPUT_C)

left_sensor = ColorSensor('in1')
right_sensor = ColorSensor('in4')
btn = Button()

BASE_SPEED = -20      
KP = 0.6
BLACK_THRESHOLD = 15
WHITE_THRESHOLD = 70  

def follow_line():
    print("Program Running... Press the back button to stop.")
    
    left_sensor.mode = 'COL-REFLECT'
    right_sensor.mode = 'COL-REFLECT'

    while not btn.backspace:
        left_val = left_sensor.reflected_light_intensity
        right_val = right_sensor.reflected_light_intensity

        left_black, right_black = left_val < BLACK_THRESHOLD, right_val < BLACK_THRESHOLD


        
        if left_black and not right_black:
            print("left")
            drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
        elif not left_black and right_black:
            print("right")
            drive.on(left_speed=BASE_SPEED, right_speed=-BASE_SPEED)
        else:
            print("forward")
            drive.on(left_speed=BASE_SPEED*KP, right_speed=BASE_SPEED*KP)
        


    drive.off()
    print("Program Stopped.")

if __name__ == "__main__":
    follow_line()

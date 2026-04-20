#!/usr/bin/env python3
from ev3dev2.motor import MoveTank, OUTPUT_B, OUTPUT_C
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.button import Button

drive = MoveTank(OUTPUT_B, OUTPUT_C)

left_sensor = ColorSensor('in1')
right_sensor = ColorSensor('in4')
btn = Button()

BASE_SPEED = -35      
KP = 1.2              # Steering sensitivity
BLACK_THRESHOLD = 20  
WHITE_THRESHOLD = 70  

def follow_line():
    print("Program Running... Press the back button to stop.")
    
    left_sensor.mode = 'COL-REFLECT'
    right_sensor.mode = 'COL-REFLECT'

    while not btn.backspace:
        left_val = left_sensor.reflected_light_intensity
        right_val = right_sensor.reflected_light_intensity

        if left_val < BLACK_THRESHOLD and right_val < BLACK_THRESHOLD:
            drive.on(left_speed=BASE_SPEED, right_speed=BASE_SPEED)
            continue 

        error = left_val - right_val
        
        adjustment = error * KP

        left_wheel_speed = BASE_SPEED - adjustment
        right_wheel_speed = BASE_SPEED + adjustment

        left_wheel_speed = max(-100, min(100, left_wheel_speed))
        right_wheel_speed = max(-100, min(100, right_wheel_speed))

        drive.on(left_speed=left_wheel_speed, right_speed=right_wheel_speed)

    drive.off()
    print("Program Stopped.")

if __name__ == "__main__":
    follow_line()

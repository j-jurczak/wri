#!/usr/bin/env python3

# Standard imports for ev3dev2
from ev3dev2.motor import MoveSteering, OUTPUT_B, OUTPUT_C, SpeedPercent
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.button import Button
from time import sleep

# Motors on Ports B and C
drive = MoveSteering(OUTPUT_B, OUTPUT_C)
# Sensors on Ports 1 and 4
left_sensor = ColorSensor('in1')
right_sensor = ColorSensor('in4')
btn = Button()

BASE_SPEED = 30       # Cruise speed (percent)
KP = 1.5              # Proportional Gain (Sensitivity of steering)
BLACK_THRESHOLD = 25  # Light intensity below this is considered 'Black'
WHITE_THRESHOLD = 70  # Light intensity above this is considered 'White'

def follow_line():
    print("Program Running... Press the back button to stop.")
    
    # Set sensors to reflected light mode
    left_sensor.mode = 'COL-REFLECT'
    right_sensor.mode = 'COL-REFLECT'

    while not btn.backspace:
        # Read the brightness (0 to 100)
        left_val = left_sensor.reflected_light_intensity
        right_val = right_sensor.reflected_light_intensity

        if left_val < BLACK_THRESHOLD and right_val < BLACK_THRESHOLD:
            drive.on(steering=0, speed=SpeedPercent(BASE_SPEED))
            continue

        error = left_val - right_val
        
        steering_value = error * KP

        if steering_value > 100:
            steering_value = 100
        elif steering_value < -100:
            steering_value = -100

        drive.on(steering=steering_value, speed=SpeedPercent(BASE_SPEED))

    drive.off()
    print("Program Stopped.")

if __name__ == "__main__":
    follow_line()

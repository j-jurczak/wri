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
TURNING_TIME = 2
TURN = 0.9
HOOK_TIME = 0.5
EXIT_COLOR = 1


def turn_right():
    drive.on(left_speed=BASE_SPEED, right_speed=-BASE_SPEED)
    sleep(TURN)

def turn_left():
    drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
    sleep(TURN)

def turn_180():
    drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
    sleep(TURNING_TIME)

def load_dziada():
    print("podnoszenia dziada")
    dripper.on_for_degrees(SpeedPercent(-20), 45)
    sleep(HOOK_TIME)
    dripper.off()

def unload_dziada():
    print("opuszczenia dziada")
    drive.off()
    dripper.on_for_degrees(SpeedPercent(20), 45)
    sleep(HOOK_TIME)
    dripper.off()

def follow_line():
    print("Program Running... Press the back button to stop.")
    
    left_sensor.mode = 'COL-COLOR'
    right_sensor.mode = 'COL-COLOR'
    loaded = False
    after_turn = False
    memturn = 0 # 1 - right, 2 - left


    while not btn.backspace:
        #r,g,b = left_sensor.rgb
        #rr,rg,rb = right_sensor.rgb
        left_val = left_sensor.color
        right_val = right_sensor.color
        left_black, right_black = left_val == 1, right_val == 1
        left_start, right_start = left_val == 3, right_val == 3
        left_end, right_end = left_val == 5, right_val == 5
        # load_dziada()
        # sleep(3)
        # unload_dziada()
        #print("Left_val:", left_val, ", Right_val:", right_val, ", ", loaded)
        #print("R: ", r, "\tG: ", g, "\tB: ", b)
        #print("R: ", rr, "\tG: ", rg, "\tB: ", rb)
        #sleep(1)
        #continue
        if left_start and right_start and not loaded:
            print("Loaded on")
            load_dziada()
            loaded = True
            after_turn = False
            turn_180()
        elif not after_turn and not loaded and left_start and not right_start:
            turn_left()
            memturn = 1
            after_turn = True
        elif not after_turn and not loaded and right_start and not left_start:
            turn_right()
            memturn = 2
            after_turn = True
        elif left_end and right_end and loaded:
            print("Loaded on")
            unload_dziada()
            loaded = False
            after_turn = False
            drive.on(left_speed=-BASE_SPEED, right_speed=-BASE_SPEED)
            sleep(1.5)
            break
        elif not after_turn and loaded and left_end and not right_end:
            turn_left()
            after_turn = True
        elif not after_turn and loaded and right_end and not left_end:
            turn_right()
            after_turn = True
        elif left_black and not right_black:
            #print("left")
            drive.on(left_speed=-BASE_SPEED, right_speed=BASE_SPEED)
        elif not left_black and right_black:
            #print("right")
            drive.on(left_speed=BASE_SPEED, right_speed=-BASE_SPEED)
        elif left_black and right_black:
            if memturn == 1:
                turn_right()
            elif memturn == 2:
                turn_left()
            
            memturn = 0
            drive.on(left_speed=BASE_SPEED*KP, right_speed=BASE_SPEED*KP)
        else:
            #print("forward")
            drive.on(left_speed=BASE_SPEED*KP, right_speed=BASE_SPEED*KP)
        


    drive.off()
    print("Program Stopped.")

if __name__ == "__main__":
    follow_line()

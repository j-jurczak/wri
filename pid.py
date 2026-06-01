#!/usr/bin/env python3
"""
PID line follower for EV3 (ev3dev2) with:
  - True PID steering (replaces the old bang-bang corrections)
  - Single sensor mode (RGB-RAW) so we read BRIGHTNESS (for PID) and
    COLOUR (for green/red markers) at the same time, with no slow mode switching
  - Debounced colour markers -> a single bad reading can't trigger a load/turn
  - Fail-safes: motors always stop on exit, sensor-read glitches are tolerated,
    anti-windup, speed clamping, stall safety, optional calibration

The load/unload/junction state machine from the original is preserved.
"""

from ev3dev2.motor import MoveTank, MediumMotor, SpeedPercent, OUTPUT_B, OUTPUT_C, OUTPUT_D
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.button import Button
from time import sleep, time

# ---------------- Hardware ----------------
drive = MoveTank(OUTPUT_B, OUTPUT_C)
dripper = MediumMotor(OUTPUT_D)
left_sensor = ColorSensor('in1')
right_sensor = ColorSensor('in4')
btn = Button()

# ---------------- Tunables ----------------
# Straight-line cruise speed. Negative = forward on this build.
BASE_SPEED = -20

# PID gains. Error is (right_reflect - left_reflect) on a 0..100 scale.
# Tune order: KP first, then KD to kill the wobble, KI last (usually 0).
KP = 0.5
KI = 0.0
KD = 1.0
INTEGRAL_CLAMP = 50          # anti-windup
REFLECT_ALPHA = 0.6          # 0..1 low-pass on brightness (higher = snappier)

# Colour classification from RGB-RAW. Run the on-robot calibration (UP button)
# to fit these to YOUR track and lighting; these are only fallback defaults.
BLACK_TOTAL = 60             # r+g+b below this  -> black line
WHITE_TOTAL = 250            # r+g+b above this  -> white floor
GREEN_RATIO = 0.45           # g/total above this (and g largest) -> green
RED_RATIO   = 0.50           # r/total above this (and r largest) -> red

# A colour must be seen this many times in a row before we act on it.
CONFIRM_COUNT = 3

# Line-following / junction detection
DARK = 15                    # reflect below this on BOTH sensors = junction/cross
STALL_TIME = 3.0             # seconds stuck on black -> safety stop (jam / fault)

# Action timings (unchanged behaviour)
TURNING_TIME = 2.0           # 180 turn
TURN = 0.9                   # 90-ish turn
HOOK_TIME = 0.5

# Brightness reference points (overwritten by calibrate())
CAL = {'L_black': 40.0, 'L_white': 300.0,
       'R_black': 40.0, 'R_white': 300.0}


# ---------------- Helpers ----------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def read_rgb(sensor, last):
    """Read RGB; on any sensor glitch reuse the last good value instead of crashing."""
    try:
        r, g, b = sensor.rgb
        return (r, g, b)
    except Exception:
        return last


def reflect(total, black, white):
    """Map raw brightness to a stable 0..100 'reflectance' using calibration."""
    if white <= black:
        return total
    return clamp((total - black) * 100.0 / (white - black), 0.0, 100.0)


def classify(r, g, b):
    """Return 'black' | 'white' | 'green' | 'red' | 'unknown' from raw RGB."""
    total = r + g + b
    if total < BLACK_TOTAL:
        return 'black'
    rn, gn = r / total, g / total
    if g > r and g > b and gn >= GREEN_RATIO:
        return 'green'
    if r > g and r > b and rn >= RED_RATIO:
        return 'red'
    if total >= WHITE_TOTAL:
        return 'white'
    return 'unknown'


class Confirm:
    """Debounce a noisy colour stream: only changes the stable value after
    CONFIRM_COUNT identical new readings, so one bad frame is ignored."""
    def __init__(self, n):
        self.n = n
        self.stable = 'unknown'
        self.cand = None
        self.cnt = 0

    def update(self, val):
        if val == self.stable:
            self.cand, self.cnt = None, 0
        else:
            if val == self.cand:
                self.cnt += 1
            else:
                self.cand, self.cnt = val, 1
            if self.cnt >= self.n:
                self.stable, self.cand, self.cnt = val, None, 0
        return self.stable


class PID:
    def __init__(self, kp, ki, kd, clamp_i):
        self.kp, self.ki, self.kd, self.clamp_i = kp, ki, kd, clamp_i
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.last = 0.0

    def step(self, error):
        self.integral = clamp(self.integral + error, -self.clamp_i, self.clamp_i)
        deriv = error - self.last
        self.last = error
        return self.kp * error + self.ki * self.integral + self.kd * deriv


# ---------------- Manoeuvres ----------------
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
    print("podnoszenie dziada")
    dripper.on_for_degrees(SpeedPercent(-20), 45)
    sleep(HOOK_TIME)
    dripper.off()


def unload_dziada():
    print("opuszczanie dziada")
    drive.off()
    dripper.on_for_degrees(SpeedPercent(20), 45)
    sleep(HOOK_TIME)
    dripper.off()


# ---------------- Calibration ----------------
def _wait_enter(msg):
    print(msg)
    while not btn.enter:
        sleep(0.02)
    while btn.enter:
        sleep(0.02)


def _avg_totals(n=20):
    lt = rt = 0.0
    for _ in range(n):
        lt += sum(read_rgb(left_sensor, (0, 0, 0)))
        rt += sum(read_rgb(right_sensor, (0, 0, 0)))
        sleep(0.02)
    return lt / n, rt / n


def calibrate():
    _wait_enter("Both sensors on WHITE floor, then press CENTER")
    CAL['L_white'], CAL['R_white'] = _avg_totals()
    _wait_enter("Both sensors on BLACK line, then press CENTER")
    CAL['L_black'], CAL['R_black'] = _avg_totals()
    print("Calibration done:", CAL)


# ---------------- Main loop ----------------
def follow_line():
    print("Running. Hold BACK to stop.")
    left_sensor.mode = 'RGB-RAW'
    right_sensor.mode = 'RGB-RAW'

    pid = PID(KP, KI, KD, INTEGRAL_CLAMP)
    l_conf, r_conf = Confirm(CONFIRM_COUNT), Confirm(CONFIRM_COUNT)

    loaded = False
    after_turn = False
    memturn = 0                 # 1 = last junction turned right, 2 = left
    last_l = last_r = (0, 0, 0)
    l_ref_f = r_ref_f = 100.0   # filtered brightness
    dark_since = None

    try:
        while not btn.backspace:
            # --- read both sensors (glitch tolerant) ---
            last_l = read_rgb(left_sensor, last_l)
            last_r = read_rgb(right_sensor, last_r)

            l_ref = reflect(sum(last_l), CAL['L_black'], CAL['L_white'])
            r_ref = reflect(sum(last_r), CAL['R_black'], CAL['R_white'])
            l_ref_f = REFLECT_ALPHA * l_ref + (1 - REFLECT_ALPHA) * l_ref_f
            r_ref_f = REFLECT_ALPHA * r_ref + (1 - REFLECT_ALPHA) * r_ref_f

            l_color = l_conf.update(classify(*last_l))
            r_color = r_conf.update(classify(*last_r))

            l_green, r_green = l_color == 'green', r_color == 'green'
            l_red,   r_red   = l_color == 'red',   r_color == 'red'

            # re-arm junction turns once we've fully left any marker
            on_marker = l_color in ('green', 'red') or r_color in ('green', 'red')
            if after_turn and not on_marker:
                after_turn = False

            both_dark = l_ref_f < DARK and r_ref_f < DARK

            # ---------- state machine (priority order) ----------
            if (not loaded) and l_green and r_green:
                print("START reached -> load")
                load_dziada()
                loaded = True
                after_turn = False
                turn_180()
                pid.reset()

            elif (not loaded) and (not after_turn) and l_green and not r_green:
                turn_left();  memturn = 1; after_turn = True; pid.reset()

            elif (not loaded) and (not after_turn) and r_green and not l_green:
                turn_right(); memturn = 2; after_turn = True; pid.reset()

            elif loaded and l_red and r_red:
                print("END reached -> unload")
                drive.on(left_speed=-BASE_SPEED, right_speed=-BASE_SPEED)
                sleep(0.6)
                drive.off()
                unload_dziada()
                loaded = False
                after_turn = False
                drive.on(left_speed=-BASE_SPEED, right_speed=-BASE_SPEED)
                sleep(1.5)
                break

            elif loaded and (not after_turn) and l_red and not r_red:
                turn_left();  after_turn = True; pid.reset()

            elif loaded and (not after_turn) and r_red and not l_red:
                turn_right(); after_turn = True; pid.reset()

            elif both_dark:
                # cross / perpendicular line: use memory of last junction, with
                # a stall safety so we never spin forever on a black patch
                if dark_since is None:
                    dark_since = time()
                elif time() - dark_since > STALL_TIME:
                    print("Stall safety: stopped (stuck on black / sensor fault)")
                    break
                if memturn == 1:
                    turn_right()
                elif memturn == 2:
                    turn_left()
                memturn = 0
                pid.reset()
                drive.on(left_speed=BASE_SPEED, right_speed=BASE_SPEED)

            else:
                # ---------- normal PID line tracking ----------
                dark_since = None
                error = r_ref_f - l_ref_f          # >0 -> drift right -> steer left
                corr = pid.step(error)
                drive.on(left_speed=clamp(BASE_SPEED + corr, -100, 100),
                         right_speed=clamp(BASE_SPEED - corr, -100, 100))

    finally:
        # fail-safe: whatever happens, leave the robot stopped
        drive.off()
        dripper.off()
        print("Stopped.")


if __name__ == "__main__":
    left_sensor.mode = 'RGB-RAW'
    right_sensor.mode = 'RGB-RAW'
    print("UP = calibrate first | CENTER = start with current values")
    while True:
        if btn.up:
            while btn.up:
                sleep(0.02)
            calibrate()
            break
        if btn.enter:
            while btn.enter:
                sleep(0.02)
            break
        sleep(0.03)
    follow_line()

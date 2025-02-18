from flask import Flask, render_template, jsonify, request
import RPi.GPIO as GPIO
import time
import MFRC522
import os
from smbus2 import SMBus
from RPLCD.i2c import CharLCD

# Setup GPIO
GPIO.setmode(GPIO.BOARD)

IR1_PIN = 7   # IR sensor 1
IR2_PIN = 11  # IR sensor 2
SERVO_PIN = 13  # Servo motor

GPIO.setup(IR1_PIN, GPIO.IN)
GPIO.setup(IR2_PIN, GPIO.IN)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Servo motor setup
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(7.5)  # 90 degrees position (initial position)

# RFID Setup
MIFAREReader = MFRC522.MFRC522()

# I2C LCD Setup
lcd = CharLCD('PCF8574', 0x27)

# Flask Setup
app = Flask(__name__)

# Slot management
total_slots = 4
reserved_slots = 0
reservations = {}

def display_welcome():
    lcd.clear()
    lcd.write_string("Welcome!")
    time.sleep(2)

def display_slots():
    lcd.clear()
    lcd.write_string(f"Slots: {total_slots - reserved_slots}/{total_slots}")
    time.sleep(2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_slots', methods=['GET'])
def get_slots():
    return jsonify({'available_slots': total_slots - reserved_slots})

@app.route('/reserve_slot', methods=['POST'])
def reserve_slot():
    global reserved_slots
    uid = request.json.get('uid')

    if reserved_slots < total_slots and uid not in reservations:
        reservations[uid] = True
        reserved_slots += 1
        lcd.clear()
        lcd.write_string(f"Reserved UID: {uid}")
        time.sleep(2)
        display_slots()
        return jsonify({'message': f"Reservation Successful for UID: {uid}"}), 200

    lcd.clear()
    lcd.write_string("No slots available")
    time.sleep(2)
    return jsonify({'message': 'No slots available or UID already reserved'}), 400

@app.route('/cancel_reservation', methods=['POST'])
def cancel_reservation():
    global reserved_slots
    uid = request.json.get('uid')

    if uid in reservations:
        del reservations[uid]
        reserved_slots -= 1
        lcd.clear()
        lcd.write_string(f"Canceled UID: {uid}")
        time.sleep(2)
        display_slots()
        return jsonify({'message': f"Reservation Canceled for UID: {uid}"}), 200

    lcd.clear()
    lcd.write_string("No reservation found")
    time.sleep(2)
    return jsonify({'message': 'No reservation found for this UID'}), 400

@app.route('/rfid_read', methods=['GET'])
def rfid_read():
    """ Read UID from the RFID scanner """
    status, uid = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

    if status == MIFAREReader.MI_OK:
        status, uid = MIFAREReader.MFRC522_Anticoll()
        if status == MIFAREReader.MI_OK:
            uid_str = ''.join(map(str, uid))
            lcd.clear()
            lcd.write_string(f"UID: {uid_str}")
            time.sleep(2)
            return jsonify({'uid': uid_str})

    lcd.clear()
    lcd.write_string("No UID detected")
    time.sleep(2)
    return jsonify({'uid': None})

@app.route('/add_card', methods=['POST'])
def add_card():
    uid = request.json.get('uid')
    lcd.clear()
    lcd.write_string(f"Card Added UID: {uid}")
    time.sleep(2)
    return jsonify({'message': f"Card Added Successfully for UID: {uid}"}), 200

@app.route('/servo_open', methods=['POST'])
def servo_open():
    servo.ChangeDutyCycle(5)  # Open the gate
    time.sleep(1)
    servo.ChangeDutyCycle(7.5)  # Return to 90 degrees (closed)
    return jsonify({'message': 'Gate opened'})

@app.route('/servo_close', methods=['POST'])
def servo_close():
    servo.ChangeDutyCycle(10)  # Close the gate
    time.sleep(1)
    servo.ChangeDutyCycle(7.5)  # Return to 90 degrees (closed)
    return jsonify({'message': 'Gate closed'})

@app.route('/ir_check', methods=['GET'])
def ir_check():
    if GPIO.input(IR1_PIN) == GPIO.LOW:
        return jsonify({'entry': True})
    if GPIO.input(IR2_PIN) == GPIO.LOW:
        return jsonify({'exit': True})
    return jsonify({'entry': False, 'exit': False})

if __name__ == '__main__':
    try:
        display_welcome()
        display_slots()
        app.run(host='0.0.0.0', port=5000)
    finally:
        GPIO.cleanup()

# Arduino Sensor and Parking Gate Projects

Arduino practice projects from the August 11 IoT lesson. The section starts with a basic HC-SR04 ultrasonic-sensor test and then applies the sensor to an automated parking gate with a servo motor and beeper.

## Projects

```text
arduino_project/
├── sensortest/
│   └── sensortest.ino        Basic HC-SR04 echo-duration test
├── parking_gate/
│   ├── parking_gate.ino      Main setup and control loop
│   ├── Sensor.h/.cpp         Distance measurement and state confirmation
│   ├── GateMotor.h/.cpp      Servo-controlled gate movement
│   └── Beeper.h/.cpp         Single- and double-beep patterns
└── README.md
```

### Sensor test

[`sensortest/sensortest.ino`](sensortest/sensortest.ino) sends a trigger pulse to an HC-SR04 sensor, reads the returned echo with a 30 ms timeout, and prints the raw echo duration to the Serial Monitor every 300 ms.

This sketch is useful for checking the ultrasonic sensor and its wiring before assembling the complete gate project. The printed `value` is the echo duration in microseconds, not a distance in centimetres.

### Parking gate

[`parking_gate/parking_gate.ino`](parking_gate/parking_gate.ino) combines three modules:

- `Sensor` measures distance, classifies readings, and filters unstable measurements.
- `GateMotor` opens and closes a servo-operated barrier.
- `Beeper` signals gate events without using blocking beep delays.

When an object remains in the detection zone long enough to be confirmed, the system beeps once and opens the gate. After the area remains clear, it beeps twice and closes the gate.

## Hardware

- Arduino-compatible board, such as an Arduino Uno
- HC-SR04 ultrasonic distance sensor
- Hobby servo motor
- Active beeper or buzzer module
- Breadboard and jumper wires
- Suitable power supply

## Pin connections

| Component | Component pin | Arduino pin |
| --- | --- | --- |
| HC-SR04 | `TRIG` | Digital 2 |
| HC-SR04 | `ECHO` | Digital 3 |
| Servo | Signal | Digital 5 |
| Beeper | Signal | Digital 6 |
| All modules | Ground | `GND` |

Connect each module's power pin according to its rated voltage. A servo can draw more current than the Arduino regulator can reliably supply, especially while moving or under load. Use an appropriate external supply when necessary and connect its ground to the Arduino ground.

## Parking-gate logic

The sensor module classifies measured distances as follows:

| Reading | Distance or condition | Effect |
| --- | --- | --- |
| `IN_ZONE` | 2-150 cm | Evidence that a car is present |
| `BORDERLINE` | More than 150 cm and less than 170 cm | Pauses presence and clearance decisions |
| `OUTSIDE_ZONE` | 170-400 cm | Evidence that the area is clear |
| `NO_ECHO` | No echo within 30 ms | Treated as possible clearance after a short grace period |
| `INVALID` | Less than 2 cm or more than 400 cm | Resets unconfirmed timing evidence |

Presence and clearance each require approximately one second of continuous evidence. A missing echo has a 250 ms grace period so that a brief sensor dropout does not immediately discard a confirmed presence state.

The gate starts in the closed position:

- Closed angle: 10 degrees
- Open angle: 80 degrees
- Car confirmed: one beep, then open
- Area confirmed clear: two beeps, then close

## Running a sketch

1. Connect the components and the Arduino board.
2. Open either `sensortest/sensortest.ino` or `parking_gate/parking_gate.ino` in the Arduino IDE.
3. Select the correct board and serial port.
4. Verify and upload the sketch.
5. Open the Serial Monitor at **9600 baud**.

The parking-gate sketch uses Arduino's standard `Servo` library. Keep all `.h`, `.cpp`, and `.ino` files in the `parking_gate` directory so the Arduino IDE builds them together.

Example diagnostic output:

```text
distance_cm=42.7  reading=IN_ZONE  presence_ms=1001  clear_ms=0  condition=CAR_PRESENT
ACTION: car confirmed
MOTOR: gate opening
```

## Adjusting the project

Hardware-specific values are defined near the top of each module:

- Detection distances and confirmation times: `parking_gate/Sensor.cpp`
- Servo pin and open/closed angles: `parking_gate/GateMotor.cpp`
- Beeper pin and pattern timing: `parking_gate/Beeper.cpp`

Calibrate the distance thresholds and servo angles for the actual placement and mechanics of the gate before regular use.

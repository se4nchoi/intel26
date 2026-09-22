# DC Motor PWM Speed & 3-Button Direction Control

> **Date**: 2026-09-22  
> **Topic**: DC Motor Control via PWM & 3-Button State Machine (`STOP` $\rightarrow$ `CW` $\rightarrow$ `CCW`)  
> **Target Hardware**: Arduino UNO, L298N Motor Driver, DC Motor, Variable Resistor (10k Potentiometer), 3x Push Buttons, Breadboard Power Supply  

---

## 1. System Architecture & Operation

### 1.1 Priority Logic Flow & STOP Safety Latch
The control loop processes button inputs with safety lockout:
1. **`if (stop_pressed)`**: **STOP (Pin 4) Toggle Latch**:
   * **Press 1**: Motor stops immediately and enters **`STOP LOCKED`**. Pressing Forward or Reverse is safely ignored.
   * **Press 2**: Releases the latch to **`STOP UNLOCKED / READY`**, enabling Forward and Reverse again.
2. **`else if (forward_pressed)`**: **CW / Forward (Pin 2)** switches rotation to Clockwise (only when not latched).
3. **`else if (reverse_pressed)`**: **CCW / Reverse (Pin 3)** switches rotation to Counter-Clockwise (only when not latched).

### 1.2 Variable Resistor (PWM Speed Control)
* Wiper pin connected to **Pin A5**.
* `analogRead(POT)` samples $0 \sim 1023$ ($0\text{V} \sim 5\text{V}$).
* `map(..., 0, 1023, 0, 255)` maps this directly to 8-bit PWM on **Pin 10 (`ENA`)**, adjusting motor speed continuously in real time.

---

## 2. Complete Wiring Diagram

```text
               +--------------------------------------------+
               |                ARDUINO UNO                 |
               +--------------------------------------------+
                 |       |       |       |        |       |
                 |       |       |       |        |       +-- 5V  -----> Potentiometer Leg 1
                 |       |       |       |        +---------- GND -----> Breadboard GND Rail
                 |       |       |       +------------------- A5  <----- Potentiometer Leg 2 (Wiper)
                 |       |       +--------------------------- Pin 10 ~ - ENA (PWM)
                 |       +----------------------------------- Pin 9 ---- IN1
                 +------------------------------------------- Pin 8 ---- IN2

      Arduino Pin 4 (SW_STOP)    ──────── [ Push Button 1 ] ──────── GND
      Arduino Pin 2 (SW_FORWARD) ──────── [ Push Button 2 ] ──────── GND
      Arduino Pin 3 (SW_REVERSE) ──────── [ Push Button 3 ] ──────── GND
```

### 2.1 Breadboard Power Supply & Motor Driver Wiring

```text
 [ Breadboard Power Supply ]                   [ L298N Motor Driver ]
   V+ (+5V or +12V Rail)   ────────────────────> [ 12V / VCC Terminal ]
   GND Rail                ──────────┬─────────> [ GND Terminal ]
                                     │
   Arduino GND             ──────────┘ (Common Ground - Mandatory!)

 [ L298N Output Terminals ]
   OUT1 ───────────────────> DC Motor Wire 1
   OUT2 ───────────────────> DC Motor Wire 2
```

> [!WARNING]
> **Power Rail Setting**:
> * Set your breadboard power supply jumper to **`5V`** for standard hobby DC motors.
> * If your motor is rated 12V and runs too slow on 5V, switch the jumper to **`12V`**.
> * Avoid **20V** to protect the L298N board regulator and the motor coils.

> [!IMPORTANT]
> **Pull off the `ENA` jumper cap!**
> Ensure the small black jumper on `ENA` is removed so that Arduino Pin 10 can control speed via PWM.

---

## 3. Pin Connection Summary

| Arduino UNO Pin | Module / Component | Signal Name | Description |
| :---: | :---: | :---: | :--- |
| **Pin 10 (PWM)** | L298N Driver | **ENA** | Motor speed via 8-bit PWM (`analogWrite`, 0 ~ 255) |
| **Pin 9** | L298N Driver | **IN1** | Direction Control 1 |
| **Pin 8** | L298N Driver | **IN2** | Direction Control 2 |
| **Pin 4** | Push Button 1 | **SW_STOP** | Immediate Motor Stop (Priority 1) |
| **Pin 2** | Push Button 2 | **SW_FORWARD** | Clockwise / Forward Rotation (Priority 2) |
| **Pin 3** | Push Button 3 | **SW_REVERSE** | Counter-Clockwise / Reverse (Priority 3) |
| **Pin A5** | Variable Resistor | **POT** | Center wiper pin ($0\text{V} \sim 5\text{V} \rightarrow 0 \sim 1023$) |
| **5V** | Potentiometer | **VCC** | Outer pin of potentiometer (+5V rail) |
| **GND** | Breadboard / Driver | **GND** | **Common Ground** (Arduino + Breadboard Power + Driver) |

---

## 4. How to Deploy

1. Copy the code in [`dc_motor_pwm.c`](./dc_motor_pwm.c) into your Arduino IDE sketch.
2. Select **Tools > Board > Arduino Uno** and the proper **COM Port**.
3. Upload to Arduino.
4. Open the **Serial Monitor** at **9600 baud** to view real-time feedback when buttons are pressed and the variable resistor is turned.

# Stepper Motor (28BYJ-48) & Push Button Control Notes

> **Date**: 2026-09-21  
> **Topic**: Arduino Stepping Motor Control (28BYJ-48 + ULN2003) & Push Button Circuit Analysis  
> **Target Hardware**: Arduino UNO, ULN2003 Driver Board, 28BYJ-48 Stepper Motor (5V), 4-Pin Tactile Switches  

---

## 1. Hardware Overview & Pin Mapping

### 1.1 Motor & Driver (28BYJ-48 + ULN2003)
The **28BYJ-48** is a unipolar 5-wire 4-phase stepper motor featuring an internal gear reduction ratio of approximately **64:1**.

| ULN2003 Input | Arduino UNO Pin | Motor Wire Color | Role |
| :---: | :---: | :---: | :--- |
| **IN1** | **Pin 8** | Blue | Coil / Phase A |
| **IN2** | **Pin 9** | Pink | Coil / Phase B |
| **IN3** | **Pin 10** | Yellow | Coil / Phase C |
| **IN4** | **Pin 11** | Orange | Coil / Phase D |
| **5V-12V (+)** | **5V** | Red (Common) | Common power rail |
| **GND (-)** | **GND** | - | Common ground |

---

## 2. Push Button Circuit Theory: Pull-Up vs. Pull-Down

### 2.1 The Fundamental Rule: Never Connect a Switch Without a Resistor
Connecting a push button directly between **5V and GND** without a resistor causes a **Dead Short** when pressed, resulting in overcurrent that resets the microcontroller and can burn the USB port.

### 2.2 Pull-Down Circuit (Active-HIGH)
Used with standard `pinMode(pin, INPUT)`:
```text
  +5V ──────── [ Push Button ] ────────┬──────── Arduino Pin (D2 / D3)
                                       │
                                 [ 10kΩ Resistor ]
                                       │
                                      GND
```
* **Unpressed (Idle)**: 10k resistor drains voltage to GND $\rightarrow$ Reads **`LOW` (0V)**.
* **Pressed**: Button connects 5V directly to the pin $\rightarrow$ Reads **`HIGH` (5V)**.
* **Why it failed earlier**: If the pin connects to the GND side of the resistor instead of the junction, or if 5V is missing from the switch, the pin remains stuck at `LOW`.

### 2.3 Pull-Up Circuit & `INPUT_PULLUP` (Active-LOW)
Used with `pinMode(pin, INPUT_PULLUP)`:
```text
  [ ATmega328P Chip Internal ]           [ External Breadboard ]
          Internal 5V 
               │
       [ 20kΩ Resistor ] 
               │
          Arduino D2 ──────────────────── [ Push Button ] ── GND
```
* **Unpressed (Idle)**: Internal 20k pull-up holds pin at **`HIGH` (5V)**.
* **Pressed**: Button grounds the pin $\rightarrow$ Reads **`LOW` (0V)**.
* **Advantages**: No external breadboard resistors needed, zero risk of short circuit, fewer jumper wires.

### 2.4 Floating Pins & Debouncing
* An unconnected digital input has an impedance $>100\text{ M}\Omega$ and acts like an antenna picking up 60Hz ambient EMI, rapidly oscillating between HIGH and LOW.
* **Software Debounce Filter**: A 25–30ms stability window filters out contact bounce and motor coil back-EMF noise.

---

## 3. Excitation Modes Comparison (여자 방식 비교)

| Characteristic | 1-Phase (1상 여자 / Wave Drive) | 2-Phase (2상 여자 / Full-Step) | 1-2 Phase (1-2상 / Half-Step) |
| :--- | :--- | :--- | :--- |
| **Active Coils** | 1 coil at a time | **2 adjacent coils at a time** | Alternates 1 and 2 coils |
| **Step Sequence** | 4 steps per cycle (`% 4`) | 4 steps per cycle (`% 4`) | **8 steps per cycle (`% 8`)** |
| **Torque** | Weak ($1.0\times$) | **Strongest ($\approx 1.414\times$)** | High |
| **Steps / Revolution** | 2048 steps | 2048 steps | **4096 steps (2x resolution)** |
| **Step Angle** | $0.176^\circ$ | $0.176^\circ$ | **$0.088^\circ$ (Half-step)** |
| **Vibration & Noise** | Noticeable clunking | High torque, mechanical resonance | **Whisper quiet, ultra-smooth** |
| **Safe Step Delay** | $\ge 3\text{ms}$ | $\ge 3\text{ms}$ (stalls at 2ms) | **$1\text{ms} \sim 2\text{ms}$** |

### 3.1 Why 2-Phase Full-Step Stalls at 2ms
* At `2ms`, the stepping frequency is $500\text{ Hz}$. Starting instantly at 500 Hz exceeds the 28BYJ-48's **pull-in frequency** (기동 주파수 한계).
* The rotor's physical inertia ($J$) and the coil inductance ($L/R$ time constant) prevent the rotor from accelerating instantaneously to 500 Hz without an acceleration ramp, causing the motor to buzz and stall.
* **Half-Step** moves only half the mechanical angle per step, significantly reducing per-step acceleration inertia, allowing it to run smoothly at `2ms`.

---

## 4. Source Files Description

* **[step_motor.c](step_motor.c)**: Base stepper motor driver with button debouncing and toggle (latch) forward/reverse control.
* **[step_motor_2phase.c](step_motor_2phase.c)**: 2-Phase Full-Step excitation program (4-step sequence, 2048 steps/rev, 3ms delay, maximum holding torque).
* **[step_motor_half_step.c](step_motor_half_step.c)**: 1-2 Phase Half-Step excitation program (8-step sequence, 4096 steps/rev, 2ms delay, ultra-smooth motion).

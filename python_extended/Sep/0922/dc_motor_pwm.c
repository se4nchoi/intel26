#include <Arduino.h>

// ============================================================================
// 0922: DC Motor Control with PWM Speed & 3 Direction Buttons
// ============================================================================
// Hardware Setup:
//   - Arduino UNO / Nano
//   - L298N / L293D Motor Driver
//   - DC Motor connected to OUT1 & OUT2
//   - Breadboard Power Supply (5V or 12V rail to Motor Driver VCC/GND)
//   - 3x Push Buttons:
//       * SW_STOP    (D4): Immediate Motor Stop (Priority 1)
//       * SW_FORWARD (D2): Run Clockwise / Forward (Priority 2)
//       * SW_REVERSE (D3): Run Counter-Clockwise / Reverse (Priority 3)
//   - 1x Variable Resistor (Potentiometer 10k) on A5 for continuous PWM speed
// ============================================================================

// -------------------------------------------------------------
// Pin Definitions
// -------------------------------------------------------------
const int ENA = 10;           // PWM Speed Control (Timer1 Pin ~10)
const int IN1 = 9;            // H-Bridge Direction Control 1
const int IN2 = 8;            // H-Bridge Direction Control 2

const int SW_FORWARD = 2;     // Push Button 1: Clockwise / Forward (CW)
const int SW_REVERSE = 3;     // Push Button 2: Counter-Clockwise / Reverse (CCW)
const int SW_STOP    = 4;     // Push Button 3: Stop

const int POT        = A5;    // Variable Resistor (Potentiometer Wiper)

// -------------------------------------------------------------
// Button Wiring Mode: External Pull-Down Network (Active-HIGH)
// -------------------------------------------------------------
// Wiring: 5V -> PB -> (Arduino Pin + 10kΩ Resistor) -> GND
//   - Idle / Released : LOW  (0, pulled down to GND by 10kΩ resistor)
//   - Pressed         : HIGH (1, connected to +5V through push button)
//   - pinMode         : INPUT
#define BUTTON_PRESSED   HIGH
#define BUTTON_RELEASED  LOW
#define PIN_MODE_BUTTON  INPUT

// -------------------------------------------------------------
// Motor States
// -------------------------------------------------------------
enum MotorState {
  STATE_STOP = 0,
  STATE_CW   = 1,   // Forward / Clockwise
  STATE_CCW  = 2    // Reverse / Counter-Clockwise
};

MotorState current_state = STATE_STOP;

// -------------------------------------------------------------
// Debounce & Telemetry Settings
// -------------------------------------------------------------
const unsigned long DEBOUNCE_MS        = 50;  // 50ms filter to reject motor coil noise spikes
const unsigned long TELEMETRY_INTERVAL = 1500; // Serial report interval (ms)

struct DebouncedButton {
  int pin;
  int debounced_val;
  int last_raw_val;
  unsigned long last_change_time;
};

DebouncedButton btn_stop    = {SW_STOP,    BUTTON_RELEASED, BUTTON_RELEASED, 0};
DebouncedButton btn_forward = {SW_FORWARD, BUTTON_RELEASED, BUTTON_RELEASED, 0};
DebouncedButton btn_reverse = {SW_REVERSE, BUTTON_RELEASED, BUTTON_RELEASED, 0};

// Telemetry values
int current_pot_adc  = 0;
int current_pwm_duty = 0;
unsigned long last_telemetry_time = 0;

// -------------------------------------------------------------
// Function Prototypes
// -------------------------------------------------------------
bool is_button_pressed(DebouncedButton &btn, unsigned long now);
void update_motor_drive(MotorState state, int speed);
void stop_motor();
void report_telemetry(unsigned long now);

// ============================================================================
// Setup
// ============================================================================
void setup() {
  // Initialize Serial Monitor
  Serial.begin(9600);
  delay(100);

  Serial.println("\n========================================================");
  Serial.println("  [0922] DC MOTOR PWM SPEED & 3-BUTTON CONTROLLER");
  Serial.println("========================================================");
  Serial.println("Controls:");
  Serial.println("  - SW_STOP    (D4): STOP (Highest Priority)");
  Serial.println("  - SW_FORWARD (D2): Run Clockwise / Forward");
  Serial.println("  - SW_REVERSE (D3): Run Counter-Clockwise / Reverse");
  Serial.println("  - POT        (A5): Speed Control via PWM (0% ~ 100%)");
  Serial.println("========================================================\n");

  // Motor Driver Outputs
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  // Variable Resistor (Potentiometer) Analog Input
  pinMode(POT, INPUT);

  // Push Button Inputs
  pinMode(SW_STOP,    PIN_MODE_BUTTON);
  pinMode(SW_FORWARD, PIN_MODE_BUTTON);
  pinMode(SW_REVERSE, PIN_MODE_BUTTON);

  // Read initial states
  btn_stop.debounced_val    = digitalRead(SW_STOP);
  btn_stop.last_raw_val     = btn_stop.debounced_val;
  btn_forward.debounced_val = digitalRead(SW_FORWARD);
  btn_forward.last_raw_val  = btn_forward.debounced_val;
  btn_reverse.debounced_val = digitalRead(SW_REVERSE);
  btn_reverse.last_raw_val  = btn_reverse.debounced_val;

  // Safe initial motor state
  stop_motor();
}

// ============================================================================
// Main Loop
// ============================================================================
void loop() {
  unsigned long now = millis();

  // 1. Read Variable Resistor (0 ~ 1023) -> Convert to 8-bit PWM (0 ~ 255)
  current_pot_adc  = analogRead(POT);
  current_pwm_duty = map(current_pot_adc, 0, 1023, 0, 255);
  current_pwm_duty = constrain(current_pwm_duty, 0, 255);

  // 2. Scan Buttons with Debouncing
  bool stop_pressed    = is_button_pressed(btn_stop, now);
  bool forward_pressed = is_button_pressed(btn_forward, now);
  bool reverse_pressed = is_button_pressed(btn_reverse, now);

  static unsigned long last_action_time = 0;
  const unsigned long COOLDOWN_MS = 250; // Lockout window to prevent cross-talk triggers

  // 3. Button Events with 250ms Cross-talk Lockout
  if (now - last_action_time > COOLDOWN_MS) {
    if (stop_pressed) {
      last_action_time = now;
      current_state = STATE_STOP;
      Serial.println("\n>>> [STOP] Motor STOPPED <<<");
    } else if (forward_pressed) {
      last_action_time = now;
      current_state = STATE_CW;
      Serial.println("\n>>> [FORWARD] Running Clockwise (CW) <<<");
    } else if (reverse_pressed) {
      last_action_time = now;
      current_state = STATE_CCW;
      Serial.println("\n>>> [REVERSE] Running Counter-Clockwise (CCW) <<<");
    }
  }

  // 4. Drive Motor with current state and real-time PWM speed
  update_motor_drive(current_state, current_pwm_duty);

  // 5. Periodic status output to Serial Monitor
  report_telemetry(now);
}

// ============================================================================
// Helper Implementations
// ============================================================================

/**
 * Non-blocking button debouncer that detects single click / press events.
 */
bool is_button_pressed(DebouncedButton &btn, unsigned long now) {
  int raw = digitalRead(btn.pin);

  if (raw != btn.last_raw_val) {
    btn.last_change_time = now;
    btn.last_raw_val = raw;
  }

  if ((now - btn.last_change_time) > DEBOUNCE_MS) {
    if (raw != btn.debounced_val) {
      btn.debounced_val = raw;
      if (btn.debounced_val == BUTTON_PRESSED) {
        return true; // Detected press edge
      }
    }
  }
  return false;
}

/**
 * Commands L298N driver inputs and PWM duty cycle.
 */
void update_motor_drive(MotorState state, int speed) {
  switch (state) {
    case STATE_CW:
      digitalWrite(IN1, HIGH);
      digitalWrite(IN2, LOW);
      analogWrite(ENA, speed);
      break;

    case STATE_CCW:
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      analogWrite(ENA, speed);
      break;

    case STATE_STOP:
    default:
      stop_motor();
      break;
  }
}

/**
 * De-energizes motor pins to safely coast / stop.
 */
void stop_motor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  analogWrite(ENA, 0);
}

/**
 * Sends live monitoring info to Serial Monitor.
 * Displays Potentiometer A5 ADC, calculated Voltage, and PWM Duty.
 */
void report_telemetry(unsigned long now) {
  if (now - last_telemetry_time < TELEMETRY_INTERVAL) {
    return;
  }
  last_telemetry_time = now;

  // Calculate equivalent analog voltage (0.00V ~ 5.00V)
  float voltage = current_pot_adc * (5.0 / 1023.0);

  Serial.print("[POT A5] ADC: ");
  if (current_pot_adc < 1000) Serial.print(" ");
  if (current_pot_adc < 100)  Serial.print(" ");
  Serial.print(current_pot_adc);
  Serial.print(" / 1023 | Voltage: ");
  Serial.print(voltage, 2);
  Serial.print("V | PWM: ");
  if (current_pwm_duty < 100) Serial.print(" ");
  Serial.print(current_pwm_duty);
  Serial.print(" (");
  int percent = (current_pwm_duty * 100) / 255;
  if (percent < 10) Serial.print(" ");
  Serial.print(percent);
  Serial.print("%) | Motor: ");
  if (current_state == STATE_CW)        Serial.print("CW  ");
  else if (current_state == STATE_CCW) Serial.print("CCW ");
  else                                 Serial.print("STOP");

  // Live Button Pin States (1 = Pressed/HIGH, 0 = Idle/LOW in External Pull-Down)
  Serial.print(" | Buttons [STOP(D4):");
  Serial.print(digitalRead(SW_STOP));
  Serial.print(" FWD(D2):");
  Serial.print(digitalRead(SW_FORWARD));
  Serial.print(" REV(D3):");
  Serial.print(digitalRead(SW_REVERSE));
  Serial.println("]");
}

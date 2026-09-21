#include <Arduino.h>

// -------------------------------------------------------------
// Pin Configuration
// -------------------------------------------------------------
// Stepper Driver Pins (ULN2003 IN1 ~ IN4)
const int pins[4] = {8, 9, 10, 11};

// Push Button Pins (Breadboard with standard Pull-Down resistors)
// Standard INPUT mode (Active-HIGH):
//   - Unpressed (Idle) : LOW  (0, pulled down to GND via 10k resistor)
//   - Pressed          : HIGH (1, connected to +5V through switch)
const int PB1_PIN = 2; // Push Button 1: Toggle Forward (Clockwise)
const int PB2_PIN = 3; // Push Button 2: Toggle Reverse (Counter-Clockwise)

// -------------------------------------------------------------
// Motor States (Toggle / Latch Mode)
// -------------------------------------------------------------
enum MotorMode {
  MODE_STOP = 0,
  MODE_FORWARD = 1,
  MODE_REVERSE = 2
};

MotorMode current_mode = MODE_STOP;

// -------------------------------------------------------------
// Stepping Sequence: 4-Phase Full-Step (2-Phase ON)
// -------------------------------------------------------------
const int STEP_COUNT_PER_REV = 2048; // 28BYJ-48 with 64:1 gear reduction
const int DEFAULT_DELAY_MS   = 3;    // Minimum ~2-3ms to prevent motor stalling
const unsigned long DEBOUNCE_MS = 30; // Debounce filter (ms)

const int step_sequence[4][4] = {
  {HIGH, LOW,  LOW,  HIGH}, // Step 0
  {HIGH, HIGH, LOW,  LOW }, // Step 1
  {LOW,  HIGH, HIGH, LOW }, // Step 2
  {LOW,  LOW,  HIGH, HIGH}  // Step 3
};

// Global step index tracking for smooth stepping
int current_step = 0;

// Debounce & State tracking
int pb1_debounced = LOW;
int pb2_debounced = LOW;
int pb1_last_raw  = LOW;
int pb2_last_raw  = LOW;

unsigned long pb1_last_change = 0;
unsigned long pb2_last_change = 0;
unsigned long last_diagnostic_time = 0;

// Function prototypes
void apply_step(int step_index);
void stop_motor();
void step_forward();
void step_reverse();
void rotate_clockwise_f(int steps, int step_delay_ms);
void rotate_clockwise_r(int steps, int step_delay_ms);

void setup() {
  // Initialize Serial Monitor
  Serial.begin(9600);
  delay(100);

  Serial.println("\n========================================================");
  Serial.println("  STEPPER MOTOR CONTROLLER: TOGGLE / LATCH MODE");
  Serial.println("========================================================");
  Serial.println("Operation Guide:");
  Serial.println("  - Press PB1 (D2): Start Continuous FORWARD (Press again to STOP)");
  Serial.println("  - Press PB2 (D3): Start Continuous REVERSE (Press again to STOP)");
  Serial.println("========================================================\n");

  // Configure stepper driver control pins as OUTPUT
  for (int i = 0; i < 4; i++) {
    pinMode(pins[i], OUTPUT);
  }

  // Configure Push Buttons as standard INPUT (Pull-Down resistors)
  pinMode(PB1_PIN, INPUT);
  pinMode(PB2_PIN, INPUT);

  // Read initial states
  pb1_debounced = digitalRead(PB1_PIN);
  pb2_debounced = digitalRead(PB2_PIN);
  pb1_last_raw  = pb1_debounced;
  pb2_last_raw  = pb2_debounced;

  // Ensure coils are de-energized initially
  stop_motor();
}

void loop() {
  int pb1_raw = digitalRead(PB1_PIN);
  int pb2_raw = digitalRead(PB2_PIN);
  unsigned long current_time = millis();

  // -----------------------------------------------------------
  // 1. Debounce & Click Detection for PB1 (Forward Toggle)
  // -----------------------------------------------------------
  if (pb1_raw != pb1_last_raw) {
    pb1_last_change = current_time;
    pb1_last_raw = pb1_raw;
  }
  if ((current_time - pb1_last_change) > DEBOUNCE_MS) {
    if (pb1_raw != pb1_debounced) {
      pb1_debounced = pb1_raw;
      // Rising edge: Button just got pressed down
      if (pb1_debounced == HIGH) {
        if (current_mode == MODE_FORWARD) {
          current_mode = MODE_STOP;
          Serial.println("[TOGGLE] PB1 Pressed -> Motor STOPPED");
        } else {
          current_mode = MODE_FORWARD;
          Serial.println("[TOGGLE] PB1 Pressed -> Locked FORWARD (CW)");
        }
      }
    }
  }

  // -----------------------------------------------------------
  // 2. Debounce & Click Detection for PB2 (Reverse Toggle)
  // -----------------------------------------------------------
  if (pb2_raw != pb2_last_raw) {
    pb2_last_change = current_time;
    pb2_last_raw = pb2_raw;
  }
  if ((current_time - pb2_last_change) > DEBOUNCE_MS) {
    if (pb2_raw != pb2_debounced) {
      pb2_debounced = pb2_raw;
      // Rising edge: Button just got pressed down
      if (pb2_debounced == HIGH) {
        if (current_mode == MODE_REVERSE) {
          current_mode = MODE_STOP;
          Serial.println("[TOGGLE] PB2 Pressed -> Motor STOPPED");
        } else {
          current_mode = MODE_REVERSE;
          Serial.println("[TOGGLE] PB2 Pressed -> Locked REVERSE (CCW)");
        }
      }
    }
  }

  // -----------------------------------------------------------
  // 3. Periodic Heartbeat Diagnostics (every 2 seconds)
  // -----------------------------------------------------------
  if (current_time - last_diagnostic_time >= 2000) {
    last_diagnostic_time = current_time;
    Serial.print("[STATUS] Motor Mode: ");
    if (current_mode == MODE_FORWARD) Serial.print("RUNNING FORWARD (CW)");
    else if (current_mode == MODE_REVERSE) Serial.print("RUNNING REVERSE (CCW)");
    else Serial.print("STOPPED");
    Serial.print(" | D2(PB1): ");
    Serial.print(pb1_debounced == HIGH ? "HIGH" : "LOW");
    Serial.print(" | D3(PB2): ");
    Serial.println(pb2_debounced == HIGH ? "HIGH" : "LOW");
  }

  // -----------------------------------------------------------
  // 4. Continuous Motor Execution based on Locked Mode
  // -----------------------------------------------------------
  if (current_mode == MODE_FORWARD) {
    step_forward();
    delay(DEFAULT_DELAY_MS);
  } 
  else if (current_mode == MODE_REVERSE) {
    step_reverse();
    delay(DEFAULT_DELAY_MS);
  } 
  else {
    // Mode is STOP: Cut coil power to prevent heating
    stop_motor();
  }
}

// -------------------------------------------------------------
// Single step forward (Clockwise)
// -------------------------------------------------------------
void step_forward() {
  current_step = (current_step + 1) % 4;
  apply_step(current_step);
}

// -------------------------------------------------------------
// Single step reverse (Counter-Clockwise)
// -------------------------------------------------------------
void step_reverse() {
  current_step = (current_step - 1 + 4) % 4;
  apply_step(current_step);
}

// -------------------------------------------------------------
// Helper: apply a specific phase configuration to the 4 pins
// -------------------------------------------------------------
void apply_step(int step_index) {
  for (int pin = 0; pin < 4; pin++) {
    digitalWrite(pins[pin], step_sequence[step_index][pin]);
  }
}

// -------------------------------------------------------------
// Stop motor: Sets all pins LOW.
// De-energizes all electromagnet coils, cutting holding current
// and preventing motor overheating when stationary.
// -------------------------------------------------------------
void stop_motor() {
  for (int i = 0; i < 4; i++) {
    digitalWrite(pins[i], LOW);
  }
}

// -------------------------------------------------------------
// Multi-step Blocked Rotation: Clockwise (Forward)
// -------------------------------------------------------------
void rotate_clockwise_f(int steps, int step_delay_ms) {
  for (int i = 0; i < steps; i++) {
    step_forward();
    delay(step_delay_ms);
  }
}

// -------------------------------------------------------------
// Multi-step Blocked Rotation: Counter-Clockwise (Reverse)
// -------------------------------------------------------------
void rotate_clockwise_r(int steps, int step_delay_ms) {
  for (int i = 0; i < steps; i++) {
    step_reverse();
    delay(step_delay_ms);
  }
}
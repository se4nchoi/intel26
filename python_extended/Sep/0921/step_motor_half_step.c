#include <Arduino.h>

// =============================================================
// [1-2 Phase (Half-Step) Stepper Motor Controller with Toggle]
// 1-2상 여자(Half-Step) 방식:
//   - 1상 여자와 2상 여자를 번갈아 가며 8단계로 제어
//   - 스텝 각도가 1/2로 줄어들어 회전이 극도로 부드럽고 진동이 최소화됨
//   - 28BYJ-48 모터 기준 1회전 = 약 4096 스텝 (8스텝 시퀀스 x 512)
// =============================================================

// -------------------------------------------------------------
// 1. Pin Configurations
// -------------------------------------------------------------
// Stepper Driver Control Pins (ULN2003 IN1 ~ IN4)
const int pins[4] = {8, 9, 10, 11};

// Push Button Pins (Breadboard with 10k Pull-Down resistors)
//   - Unpressed (Idle) : LOW  (0V)
//   - Pressed          : HIGH (5V)
const int PB1_PIN = 2; // PB1: Toggle Forward (Clockwise)
const int PB2_PIN = 3; // PB2: Toggle Reverse (Counter-Clockwise)

// -------------------------------------------------------------
// 2. Stepping Sequence: 1-2 Phase Half-Step (8단계 시퀀스)
// -------------------------------------------------------------
const int STEP_COUNT_PER_REV = 4096; // Half-step doubles resolution: 4096 steps/rev
const int DEFAULT_DELAY_MS   = 2;    // Half-step moves smaller angles, 1~3ms works great!
const unsigned long DEBOUNCE_MS = 30; // Button debounce filter (ms)

// 8단계 1-2상 여자 테이블 (1상과 2상 교대)
const int step_sequence[8][4] = {
  {HIGH, LOW,  LOW,  LOW }, // Step 0 (Phase A)
  {HIGH, HIGH, LOW,  LOW }, // Step 1 (Phase A + B)
  {LOW,  HIGH, LOW,  LOW }, // Step 2 (Phase B)
  {LOW,  HIGH, HIGH, LOW }, // Step 3 (Phase B + C)
  {LOW,  LOW,  HIGH, LOW }, // Step 4 (Phase C)
  {LOW,  LOW,  HIGH, HIGH}, // Step 5 (Phase C + D)
  {LOW,  LOW,  LOW,  HIGH}, // Step 6 (Phase D)
  {HIGH, LOW,  LOW,  HIGH}  // Step 7 (Phase D + A)
};

// -------------------------------------------------------------
// 3. State Management & Variables
// -------------------------------------------------------------
enum MotorMode {
  MODE_STOP = 0,
  MODE_FORWARD = 1,
  MODE_REVERSE = 2
};

MotorMode current_mode = MODE_STOP;
int current_step = 0; // Current step index in sequence (0 ~ 7)

// Button debouncing variables
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

// -------------------------------------------------------------
// 4. Setup Routine
// -------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  delay(100);

  Serial.println("\n========================================================");
  Serial.println("  1-2 PHASE (HALF-STEP / 하프스텝) STEPPER CONTROLLER");
  Serial.println("========================================================");
  Serial.println("Key Features:");
  Serial.println("  - Mode: 1-2 Phase Excitation (8 Steps per cycle)");
  Serial.println("  - Resolution: 4096 Steps / Revolution (2x Precision)");
  Serial.println("  - Motion: Ultra-Smooth, Low Vibration & Whisper Quiet");
  Serial.println("  - Controls: PB1 (Toggle Forward) / PB2 (Toggle Reverse)");
  Serial.println("========================================================\n");

  // Configure driver pins as OUTPUT
  for (int i = 0; i < 4; i++) {
    pinMode(pins[i], OUTPUT);
  }

  // Configure button pins as standard INPUT (Pull-Down circuit)
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

// -------------------------------------------------------------
// 5. Main Loop
// -------------------------------------------------------------
void loop() {
  int pb1_raw = digitalRead(PB1_PIN);
  int pb2_raw = digitalRead(PB2_PIN);
  unsigned long current_time = millis();

  // -----------------------------------------------------------
  // PB1 Toggle Detection (Forward)
  // -----------------------------------------------------------
  if (pb1_raw != pb1_last_raw) {
    pb1_last_change = current_time;
    pb1_last_raw = pb1_raw;
  }
  if ((current_time - pb1_last_change) > DEBOUNCE_MS) {
    if (pb1_raw != pb1_debounced) {
      pb1_debounced = pb1_raw;
      if (pb1_debounced == HIGH) { // Button clicked
        if (current_mode == MODE_FORWARD) {
          current_mode = MODE_STOP;
          Serial.println("[TOGGLE] PB1 Pressed -> Motor STOPPED");
        } else {
          current_mode = MODE_FORWARD;
          Serial.println("[TOGGLE] PB1 Pressed -> Half-Step FORWARD (CW) Locked");
        }
      }
    }
  }

  // -----------------------------------------------------------
  // PB2 Toggle Detection (Reverse)
  // -----------------------------------------------------------
  if (pb2_raw != pb2_last_raw) {
    pb2_last_change = current_time;
    pb2_last_raw = pb2_raw;
  }
  if ((current_time - pb2_last_change) > DEBOUNCE_MS) {
    if (pb2_raw != pb2_debounced) {
      pb2_debounced = pb2_raw;
      if (pb2_debounced == HIGH) { // Button clicked
        if (current_mode == MODE_REVERSE) {
          current_mode = MODE_STOP;
          Serial.println("[TOGGLE] PB2 Pressed -> Motor STOPPED");
        } else {
          current_mode = MODE_REVERSE;
          Serial.println("[TOGGLE] PB2 Pressed -> Half-Step REVERSE (CCW) Locked");
        }
      }
    }
  }

  // -----------------------------------------------------------
  // Periodic Diagnostics Output (every 2 seconds)
  // -----------------------------------------------------------
  if (current_time - last_diagnostic_time >= 2000) {
    last_diagnostic_time = current_time;
    Serial.print("[STATUS] Mode: ");
    if (current_mode == MODE_FORWARD) Serial.print("RUNNING FORWARD (CW)");
    else if (current_mode == MODE_REVERSE) Serial.print("RUNNING REVERSE (CCW)");
    else Serial.print("STOPPED");
    Serial.print(" | Step (0~7): ");
    Serial.print(current_step);
    Serial.print(" | D2(PB1): ");
    Serial.print(pb1_debounced == HIGH ? "HIGH" : "LOW");
    Serial.print(" | D3(PB2): ");
    Serial.println(pb2_debounced == HIGH ? "HIGH" : "LOW");
  }

  // -----------------------------------------------------------
  // Half-Step Motor Execution
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
    stop_motor(); // De-energize coils when stopped to save power
  }
}

// -------------------------------------------------------------
// 6. Motor Control Functions
// -------------------------------------------------------------

// Single half-step forward (Clockwise: 0 -> 1 -> ... -> 7 -> 0)
void step_forward() {
  current_step = (current_step + 1) % 8;
  apply_step(current_step);
}

// Single half-step reverse (Counter-Clockwise: 7 -> 6 -> ... -> 0 -> 7)
void step_reverse() {
  current_step = (current_step - 1 + 8) % 8;
  apply_step(current_step);
}

// Apply phase excitation matrix to output pins
void apply_step(int step_index) {
  for (int pin = 0; pin < 4; pin++) {
    digitalWrite(pins[pin], step_sequence[step_index][pin]);
  }
}

// Cut power to all coils
void stop_motor() {
  for (int i = 0; i < 4; i++) {
    digitalWrite(pins[i], LOW);
  }
}

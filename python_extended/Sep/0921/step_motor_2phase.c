#include <Arduino.h>

// =============================================================
// [2-Phase (Full-Step) Stepper Motor Controller with Toggle]
// 2상 여자(2-Phase Excitation) 방식:
//   - 항상 2개의 코일(상)이 동시에 여자(ON)되는 4단계 시퀀스
//   - 토크(회전력/지탱력)가 가장 강력한 풀스텝 제어
//   - 28BYJ-48 모터 기준 1회전 = 약 2048 스텝 (4스텝 시퀀스 x 512)
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
// 2. Stepping Sequence: 2-Phase Full-Step (4단계 2상 여자 테이블)
// -------------------------------------------------------------
const int STEP_COUNT_PER_REV = 2048; // 28BYJ-48 with 64:1 reduction
const int DEFAULT_DELAY_MS   = 3;    // Safe delay for 2-phase full-step
const unsigned long DEBOUNCE_MS = 30; // Button debounce filter (ms)

// 4단계 2상 여자 시퀀스 (동시에 2개 코일 ON)
const int step_sequence[4][4] = {
  {HIGH, HIGH, LOW,  LOW }, // Step 0 (Phase A, B)
  {LOW,  HIGH, HIGH, LOW }, // Step 1 (Phase B, C)
  {LOW,  LOW,  HIGH, HIGH}, // Step 2 (Phase C, D)
  {HIGH, LOW,  LOW,  HIGH}  // Step 3 (Phase D, A)
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
int current_step = 0; // Current step index in sequence (0 ~ 3)

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
  Serial.println("  2-PHASE (2상 여자 / 풀스텝) STEPPER CONTROLLER");
  Serial.println("========================================================");
  Serial.println("Key Features:");
  Serial.println("  - Mode: 2-Phase Excitation (2 Coils ON simultaneously)");
  Serial.println("  - Resolution: 2048 Steps / Revolution");
  Serial.println("  - Characteristics: Maximum Holding Torque & Strong Power");
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
          Serial.println("[TOGGLE] PB1 Pressed -> 2-Phase FORWARD (CW) Locked");
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
          Serial.println("[TOGGLE] PB2 Pressed -> 2-Phase REVERSE (CCW) Locked");
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
    if (current_mode == MODE_FORWARD) Serial.print("2-PHASE FORWARD (CW)");
    else if (current_mode == MODE_REVERSE) Serial.print("2-PHASE REVERSE (CCW)");
    else Serial.print("STOPPED");
    Serial.print(" | Step (0~3): ");
    Serial.print(current_step);
    Serial.print(" | D2(PB1): ");
    Serial.print(pb1_debounced == HIGH ? "HIGH" : "LOW");
    Serial.print(" | D3(PB2): ");
    Serial.println(pb2_debounced == HIGH ? "HIGH" : "LOW");
  }

  // -----------------------------------------------------------
  // 2-Phase Motor Step Execution
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

// Single 2-phase step forward (Clockwise: 0 -> 1 -> 2 -> 3 -> 0)
void step_forward() {
  current_step = (current_step + 1) % 4;
  apply_step(current_step);
}

// Single 2-phase step reverse (Counter-Clockwise: 3 -> 2 -> 1 -> 0 -> 3)
void step_reverse() {
  current_step = (current_step - 1 + 4) % 4;
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

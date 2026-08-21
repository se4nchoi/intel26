#include "GateMotor.h"
#include <Servo.h>

namespace GateMotor {

const int SERVO_PIN = 5;

const int CLOSED_ANGLE = 0;
const int OPEN_ANGLE = 90;

// Initial command + three retries.
const unsigned long RETRY_INTERVAL_MS = 500;
const int TOTAL_COMMAND_ATTEMPTS = 4;

Servo gateServo;

// These represent the commanded target.
// There is no physical position feedback yet.
bool gateIsOpen = false;
bool targetIsOpen = false;

bool commandSequenceActive = false;

int commandAttempts = 0;
unsigned long lastCommandMs = 0;

void writeTargetAngle() {
  if (targetIsOpen) {
    gateServo.write(OPEN_ANGLE);
  } else {
    gateServo.write(CLOSED_ANGLE);
  }
}

void startCommandSequence() {
  // Send the first command immediately.
  writeTargetAngle();

  commandAttempts = 1;
  lastCommandMs = millis();
  commandSequenceActive = true;
}

void begin() {
  gateServo.attach(SERVO_PIN);

  targetIsOpen = false;
  gateIsOpen = false;

  gateServo.write(CLOSED_ANGLE);

  delay(500);
}

void update() {
  if (!commandSequenceActive) {
    return;
  }

  unsigned long nowMs = millis();

  if (nowMs - lastCommandMs < RETRY_INTERVAL_MS) {
    return;
  }

  if (commandAttempts >= TOTAL_COMMAND_ATTEMPTS) {
    commandSequenceActive = false;

    Serial.println(
        "MOTOR: command sequence finished "
        "(position unverified)"
    );

    return;
  }

  writeTargetAngle();

  commandAttempts++;
  lastCommandMs = nowMs;

  Serial.print("MOTOR: command retry ");
  Serial.print(commandAttempts - 1);
  Serial.print("/");

  Serial.println(TOTAL_COMMAND_ATTEMPTS - 1);
}

void open() {
  // Avoid restarting an already active open request.
  if (targetIsOpen) {
    return;
  }

  targetIsOpen = true;
  gateIsOpen = true;

  Serial.println("MOTOR: gate opening");

  startCommandSequence();
}

void close() {
  // Avoid restarting an already active close request.
  if (!targetIsOpen) {
    return;
  }

  targetIsOpen = false;
  gateIsOpen = false;

  Serial.println("MOTOR: gate closing");

  startCommandSequence();
}

bool isOpen() {
  return gateIsOpen;
}

}
#include "Beeper.h"

namespace Beeper {

const int BEEPER_PIN = 6;

const unsigned long BEEP_ON_MS = 75;
const unsigned long BEEP_OFF_MS = 75;

enum class Pattern {
  IDLE,
  SINGLE_ON,
  DOUBLE_FIRST_ON,
  DOUBLE_PAUSE,
  DOUBLE_SECOND_ON
};

Pattern currentPattern = Pattern::IDLE;
unsigned long patternStartMs = 0;

void turnOn() {
  digitalWrite(BEEPER_PIN, HIGH);
}

void turnOff() {
  digitalWrite(BEEPER_PIN, LOW);
}

void begin() {
  pinMode(BEEPER_PIN, OUTPUT);
  turnOff();
}

void beepOnce() {
  turnOn();

  currentPattern = Pattern::SINGLE_ON;
  patternStartMs = millis();
}

void beepTwice() {
  turnOn();

  currentPattern = Pattern::DOUBLE_FIRST_ON;
  patternStartMs = millis();
}

void update() {
  unsigned long nowMs = millis();
  unsigned long elapsedMs = nowMs - patternStartMs;

  switch (currentPattern) {
    case Pattern::IDLE:
      break;

    case Pattern::SINGLE_ON:
      if (elapsedMs >= BEEP_ON_MS) {
        turnOff();
        currentPattern = Pattern::IDLE;
      }
      break;

    case Pattern::DOUBLE_FIRST_ON:
      if (elapsedMs >= BEEP_ON_MS) {
        turnOff();

        currentPattern = Pattern::DOUBLE_PAUSE;
        patternStartMs = nowMs;
      }
      break;

    case Pattern::DOUBLE_PAUSE:
      if (elapsedMs >= BEEP_OFF_MS) {
        turnOn();

        currentPattern = Pattern::DOUBLE_SECOND_ON;
        patternStartMs = nowMs;
      }
      break;

    case Pattern::DOUBLE_SECOND_ON:
      if (elapsedMs >= BEEP_ON_MS) {
        turnOff();
        currentPattern = Pattern::IDLE;
      }
      break;
  }
}

}
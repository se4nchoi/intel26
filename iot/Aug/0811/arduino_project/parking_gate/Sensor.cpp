#include "Sensor.h"

namespace Sensor {

// HC-SR04 pins
const int TRIG_PIN = 2;
const int ECHO_PIN = 3;

// Distance classification boundaries
const float MIN_DISTANCE_CM = 2.0;
const float DETECTION_LIMIT_CM = 150.0;
const float OUTSIDE_LIMIT_CM = 170.0;
const float MAX_DISTANCE_CM = 400.0;

// Confirmation times
const unsigned long PRESENCE_CONFIRM_MS = 1000;
const unsigned long NO_ECHO_GRACE_MS = 250;
const unsigned long CLEAR_CONFIRM_MS = 1000;

// Accumulated timing evidence
unsigned long accumulatedPresenceMs = 0;
unsigned long accumulatedClearMs = 0;

unsigned long previousUpdateMs = 0;
unsigned long noEchoStartMs = 0;

Reading previousReading = Reading::INVALID;

// Confirmed conditions
bool presentConfirmed = false;
bool areaClearConfirmed = false;

// One-loop events
bool justConfirmed = false;
bool justCleared = false;

void begin() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);
  delay(100);

  previousUpdateMs = millis();
}

unsigned long readEchoMicroseconds() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  return pulseIn(ECHO_PIN, HIGH, 30000UL);
}

float readDistanceCm() {
  unsigned long echoDurationUs =
      readEchoMicroseconds();

  if (echoDurationUs == 0) {
    return -1.0;
  }

  return echoDurationUs / 58.0;
}

Reading classifyDistance(float distanceCm) {
  if (distanceCm == -1.0) {
    return Reading::NO_ECHO;
  }

  if (distanceCm < MIN_DISTANCE_CM ||
      distanceCm > MAX_DISTANCE_CM) {
    return Reading::INVALID;
  }

  if (distanceCm <= DETECTION_LIMIT_CM) {
    return Reading::IN_ZONE;
  }

  if (distanceCm < OUTSIDE_LIMIT_CM) {
    return Reading::BORDERLINE;
  }

  return Reading::OUTSIDE_ZONE;
}

const char* readingName(Reading reading) {
  switch (reading) {
    case Reading::IN_ZONE:
      return "IN_ZONE";

    case Reading::BORDERLINE:
      return "BORDERLINE";

    case Reading::OUTSIDE_ZONE:
      return "OUTSIDE_ZONE";

    case Reading::NO_ECHO:
      return "NO_ECHO";

    case Reading::INVALID:
      return "INVALID";
  }

  return "ERROR";
}

void update() {
  unsigned long nowMs = millis();

  float distanceCm = readDistanceCm();
  Reading reading = classifyDistance(distanceCm);

  unsigned long elapsedMs =
      nowMs - previousUpdateMs;

  // Reset one-loop event flags.
  justConfirmed = false;
  justCleared = false;

  // Accumulate presence only between two valid
  // consecutive IN_ZONE readings.
  if (previousReading == Reading::IN_ZONE &&
      reading == Reading::IN_ZONE) {
    accumulatedPresenceMs += elapsedMs;
  }

  // OUTSIDE_ZONE and NO_ECHO are currently treated
  // as evidence that the detection area may be clear.
  bool previousWasClearEvidence =
      previousReading == Reading::OUTSIDE_ZONE ||
      previousReading == Reading::NO_ECHO;

  bool currentIsClearEvidence =
      reading == Reading::OUTSIDE_ZONE ||
      reading == Reading::NO_ECHO;

  if (previousWasClearEvidence &&
      currentIsClearEvidence) {
    accumulatedClearMs += elapsedMs;
  }

  if (reading == Reading::IN_ZONE) {
    // A detected object cancels accumulated
    // clearance evidence.
    accumulatedClearMs = 0;
    areaClearConfirmed = false;

    noEchoStartMs = 0;

    if (!presentConfirmed &&
        accumulatedPresenceMs >= PRESENCE_CONFIRM_MS) {
      presentConfirmed = true;
      justConfirmed = true;
    }
  }

  else if (reading == Reading::NO_ECHO) {
    if (previousReading != Reading::NO_ECHO) {
      noEchoStartMs = nowMs;
    }

    unsigned long noEchoDurationMs =
        nowMs - noEchoStartMs;

    // Preserve presence through a brief missing Echo.
    // Sustained NO_ECHO eventually removes presence.
    if (noEchoDurationMs > NO_ECHO_GRACE_MS) {
      accumulatedPresenceMs = 0;
      presentConfirmed = false;
    }

    if (!areaClearConfirmed &&
        accumulatedClearMs >= CLEAR_CONFIRM_MS) {
      presentConfirmed = false;
      areaClearConfirmed = true;
      justCleared = true;
    }
  }

  else if (reading == Reading::OUTSIDE_ZONE) {
    accumulatedPresenceMs = 0;
    noEchoStartMs = 0;

    // Preserve CAR_PRESENT until clearance has
    // remained continuous for the confirmation time.
    if (!areaClearConfirmed &&
        accumulatedClearMs >= CLEAR_CONFIRM_MS) {
      presentConfirmed = false;
      areaClearConfirmed = true;
      justCleared = true;
    }
  }

  else if (reading == Reading::BORDERLINE) {
    // Pause both decisions.
    // Do not add time or discard confirmed conditions.
  }

  else {
    // INVALID cannot prove presence or clearance.
    accumulatedPresenceMs = 0;
    accumulatedClearMs = 0;
    noEchoStartMs = 0;
  }

  Serial.print("distance_cm=");

  if (reading == Reading::NO_ECHO) {
    Serial.print("NO_ECHO");
  } else {
    Serial.print(distanceCm, 1);
  }

  Serial.print("  reading=");
  Serial.print(readingName(reading));

  Serial.print("  presence_ms=");
  Serial.print(accumulatedPresenceMs);

  Serial.print("  clear_ms=");
  Serial.print(accumulatedClearMs);

  Serial.print("  condition=");

  if (presentConfirmed) {
    Serial.println("CAR_PRESENT");
  } else if (areaClearConfirmed) {
    Serial.println("AREA_CLEAR");
  } else {
    Serial.println("UNCONFIRMED");
  }

  previousReading = reading;
  previousUpdateMs = nowMs;

  delay(1000);
}

bool carPresentConfirmed() {
  return presentConfirmed;
}

bool carJustConfirmed() {
  return justConfirmed;
}

bool areaClear() {
  return areaClearConfirmed;
}

bool areaJustCleared() {
  return justCleared;
}

}
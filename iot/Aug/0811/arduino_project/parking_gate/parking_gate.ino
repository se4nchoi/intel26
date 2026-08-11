#include "Sensor.h"
#include "GateMotor.h"
#include "Beeper.h"

const unsigned long CLOSE_LEAD_TIME_MS = 1500;

bool closePending = false;
unsigned long closePendingStartMs = 0;

void setup() {
  Serial.begin(9600);

  // Ensure the beeper begins in its OFF state.
  Beeper::begin();

  Sensor::begin();
  GateMotor::begin();

  Serial.println("Parking gate system started");
}

void loop() {
  Sensor::update();
  Beeper::update();
  GateMotor::update();

  if (Sensor::carJustConfirmed()) {
    // A newly confirmed car cancels any pending closure.
    if (closePending) {
      closePending = false;

      Serial.println(
          "ACTION: pending close cancelled"
      );
    }

    Serial.println("ACTION: car confirmed");

    Beeper::beepOnce();
    GateMotor::open();
  }

  if (Sensor::areaJustCleared()) {
    // Only schedule a close if the gate was commanded open.
    if (GateMotor::isOpen()) {
      closePending = true;
      closePendingStartMs = millis();

      Serial.println(
          "ACTION: area clear; close pending"
      );
    }
  }

  if (closePending) {
    // Sensor::areaClear() becomes false as soon as
    // a new IN_ZONE reading appears.
    if (!Sensor::areaClear()) {
      closePending = false;

      Serial.println(
          "ACTION: pending close cancelled "
          "by new detection"
      );
    }

    else if (
        millis() - closePendingStartMs >=
        CLOSE_LEAD_TIME_MS
    ) {
      closePending = false;

      Serial.println(
          "ACTION: close lead time completed"
      );

      Beeper::beepTwice();
      GateMotor::close();
    }
  }
}
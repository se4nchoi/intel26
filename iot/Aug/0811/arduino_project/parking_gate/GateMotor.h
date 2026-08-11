#ifndef GATE_MOTOR_H
#define GATE_MOTOR_H

#include <Arduino.h>

namespace GateMotor {

void begin();
void update();

void open();
void close();

// This reports the commanded target, not measured position.
bool isOpen();

}

#endif
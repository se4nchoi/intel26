#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>

namespace Sensor {

enum class Reading {
  IN_ZONE,
  BORDERLINE,
  OUTSIDE_ZONE,
  NO_ECHO,
  INVALID
};

void begin();

unsigned long readEchoMicroseconds();
float readDistanceCm();

Reading classifyDistance(float distanceCm);
const char* readingName(Reading reading);

void update();

bool carPresentConfirmed();
bool carJustConfirmed();

bool areaClear();
bool areaJustCleared();

}

#endif
#ifndef BEEPER_H
#define BEEPER_H

#include <Arduino.h>

namespace Beeper {

void begin();
void update();

void beepOnce();
void beepTwice();

}

#endif
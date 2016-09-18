#ifndef RSM_EEPROM_H
#define RSM_EEPROM_H

#include "Arduino.h"

byte read_id();
float read_ramp_time();
float read_min_period();
void write_id(byte id);
void write_ramp_time(float ramp_time);
void write_min_period(float min_period);

#endif

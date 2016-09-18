#ifndef DDG_EEPROM_H
#define DDG_EEPROM_H

#include "Arduino.h"

byte read_id();
float read_min();
float read_max();
int read_offset();
long read_delay();

void write_id(byte id);
void write_min(float min);
void write_max(float max);
void write_offset(int offset);
void write_delay(long delay);

#endif

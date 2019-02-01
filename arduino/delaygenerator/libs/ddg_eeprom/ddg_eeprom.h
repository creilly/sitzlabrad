#ifndef DDG_EEPROM_H
#define DDG_EEPROM_H

#include "Arduino.h"

const byte addresses = 200;

byte read_id();
float read_min();
float read_max();
long read_offset();
long read_delay();

void write_id(byte id);
void write_min(float min);
void write_max(float max);
void write_offset(long offset);
void write_delay(long delay);

byte initialize_delay();
void initialize_ring_buffer(long delay);
long _debug_delay_buffer(byte address);
byte _debug_status_buffer(byte address);
byte _debug_status_add();
long _debug_status_offset();
void _debug_sequence(long length);

#endif


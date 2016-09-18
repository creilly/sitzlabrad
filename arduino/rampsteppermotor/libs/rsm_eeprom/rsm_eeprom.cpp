#include "Arduino.h" // for typedefs (byte, etc)
#include "rsm_eeprom.h"
#include "sitz_eeprom.h"

const byte id_add = 0;
const byte ramp_time_add = 1;
const byte min_period_add = 5;

byte read_id() {  
  byte width = sizeof(byte);
  byte byte_array[width];
  eeprom_read(id_add,byte_array,width);
  return *(byte*)byte_array;
}
float read_ramp_time() {
  byte width = sizeof(float);
  byte byte_array[width];
  eeprom_read(ramp_time_add,byte_array,width);
  return *(float*)byte_array;
}
float read_min_period() {
  byte width = sizeof(float);
  byte byte_array[width];
  eeprom_read(min_period_add,byte_array,width);
  return *(float*)byte_array;
}
void write_id(byte id) {
  eeprom_write(id_add,(byte*)&id,sizeof(byte));
}
void write_ramp_time(float ramp_time) {
  eeprom_write(ramp_time_add,(byte*)&ramp_time,sizeof(float));
}
void write_min_period(float min_period) {
  eeprom_write(min_period_add,(byte*)&min_period,sizeof(float));
}


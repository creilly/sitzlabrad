#include "ddg_eeprom.h"
#include "sitz_eeprom.h"
#include "Arduino.h"

const byte id_add = 0;
const byte min_add = 1;
const byte max_add = 5;
const byte offset_add = 9;
const byte delay_add = 13;

byte read_id() {  
  byte width = sizeof(byte);
  byte byte_array[width];
  eeprom_read(id_add,byte_array,width);
  return *(byte*)byte_array;
}
float read_min() {
  byte width = sizeof(float);
  byte byte_array[width];
  eeprom_read(min_add,byte_array,width);
  return *(float*)byte_array;
}
float read_max() {
  byte width = sizeof(float);
  byte byte_array[width];
  eeprom_read(max_add,byte_array,width);
  return *(float*)byte_array;
}
int read_offset() {
  byte width = sizeof(int);
  byte byte_array[width];
  eeprom_read(offset_add,byte_array,width);
  return *(int*)byte_array;
}
long read_delay() {
  byte width = sizeof(long);
  byte byte_array[width];
  eeprom_read(delay_add,byte_array,width);
  return *(long*)byte_array;
}
void write_id(byte id) {
  eeprom_write(id_add,(byte*)&id,sizeof(byte));
}
void write_min(float min) {
  eeprom_write(min_add,(byte*)&min,sizeof(float));
}
void write_max(float max) {
  eeprom_write(max_add,(byte*)&max,sizeof(float));
}
void write_offset(int offset) {
  eeprom_write(offset_add,(byte*)&offset,sizeof(int));
}
void write_delay(long delay) {
  eeprom_write(delay_add,(byte*)&delay,sizeof(long));
}

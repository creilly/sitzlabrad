#include "Arduino.h" // for typedefs (byte, etc)
#include "ssm_eeprom.h"
#include "sitz_eeprom.h"

const byte id_add = 0;

byte read_id() {  
  byte width = sizeof(byte);
  byte byte_array[width];
  eeprom_read(id_add,byte_array,width);
  return *(byte*)byte_array;
}
void write_id(byte id) {
  eeprom_write(id_add,(byte*)&id,sizeof(byte));
}

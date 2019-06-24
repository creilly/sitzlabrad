#include "Arduino.h" // arduino typedefs (byte, etc.)
#include "sitz_eeprom.h"
#include "EEPROM.h"

void eeprom_read(long address, byte byte_array[], byte data_size) {
  int i;
  for (i = 0; i < data_size; i++) {
    byte_array[i] = EEPROM.read(address+i);
  }
}
void eeprom_write(long address, byte byte_array[], byte data_size){
  int i;
  for (i = 0; i < data_size; i++) {
    EEPROM.write(address + i, byte_array[i]);
  }
}

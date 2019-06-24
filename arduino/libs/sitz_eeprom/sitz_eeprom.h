#ifndef SITZ_EEPROM_H
#define SITZ_EEPROM_H

#include "Arduino.h"

void eeprom_read(long address, byte byte_array[], byte data_size);
void eeprom_write(long address, byte byte_array[], byte data_size);

#endif 

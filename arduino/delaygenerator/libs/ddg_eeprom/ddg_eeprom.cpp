/* 

 ddg eeprom library
 ------------------
 ------------------

 intro
 -----

 since we frequently write delays, we run into the 100k write
 lifetime of the eeprom. to extend the lifetime by a factor N (= 200 for us),
 we cycle through the addresses used to store the current delay, 
 so no one address is subjected to too much wear and tear. the set 
 of addresses used to store the current delay we'll term the "delay 
 buffer".

 another ring buffer (we'll term the "status buffer") stores the 
 address of the current delay. the number of addresses in the status 
 buffer is one greater than the number of addresses in the delay buffer.

 primary initialization ( initialize_ring_buffer() ):
 --------------------------------------------------------------

 before first use, the status buffer is initialized to:

 address: | 0 | 1 | ... | N-1 | N |
 value:   | 0 | 1 | ... | N-1 | 0 |

 where N is the number of addresses in the delay buffer. the initial delay 
 is then written to address 0 of the delay buffer. this initialization 
 need only to be performed once.

 secondary initiailization ( initialize_delay() ):
 -------------------------------------------------

 on every power up and immediately after primary initialization, 
 the status buffer address containing the current delay (we'll 
 term the "active address") is determined by finding the address 
 whose contents equals the contents of the successive address. 
 after primary initialization, for instance, this will be address N, 
 which points to address 0 in the delay buffer. it is important to 
 keep in mind that the active address resides in the status buffer, 
 not the delay buffer.

 writing delays ( write_delay() ):
 ---------------------------------
 
 a new delay is written to the delay buffer address following the one 
 pointed to by the active address. the status buffer following the active 
 address then becomes the active address, and now points to the newly 
 written delay.

 reading delays ( read_delay() ):
 --------------------------------
 
 calling read_delay() returns the contents of the delay buffer address 
 pointed to by the active address. remember to perform secondary 
 initialization before calling read or write commands.

 references
 ----------

 this general technique is known as "wear leveling". our specific 
 solution is a modified version of the one described in:

 AVR101: High Endurance EEPROM Storage
 http://ww1.microchip.com/downloads/en/AppNotes/doc2526.pdf

*/

#include "ddg_eeprom.h"
#include "sitz_eeprom.h"
#include "Arduino.h"

const byte id_add = 0;
const byte min_add = 1;
const byte max_add = 5;
const byte offset_add = 9;
const byte delay_add = 13; // delay buffer starts here
const byte delay_width = sizeof(long);
const long status_offset = delay_add+addresses*delay_width; // status buffer starts here

// holds active address.
// before first read or write,
// initialize this variable by calling initialize_delay().
byte status_add;

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
long read_offset() {
  byte width = sizeof(long);
  byte byte_array[width];
  eeprom_read(offset_add,byte_array,width);
  return *(long*)byte_array;
}
byte _read_status() {
  byte width = sizeof(byte);
  byte byte_array[width];    
  eeprom_read(status_offset+long(status_add)*width,byte_array,width);
  return *(byte*)byte_array;
}
long read_delay() {  
  byte width = sizeof(long);
  byte byte_array[width];
  eeprom_read(delay_add+long(width)*_read_status(),byte_array,width);  
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
void write_offset(long offset) {
  eeprom_write(offset_add,(byte*)&offset,sizeof(long));
}
void write_delay(long delay) {
  byte delay_width = sizeof(long);
  byte status_width = sizeof(byte);
  byte prev_delay_add = _read_status();
  byte new_delay_add = (prev_delay_add + 1)%addresses;
  status_add = (status_add + 1)%(addresses+1);
  eeprom_write(delay_add+long(new_delay_add)*delay_width,(byte*)&delay,sizeof(long));
  eeprom_write(status_offset+long(status_add)*status_width,(byte*)&new_delay_add,sizeof(byte));
}

byte initialize_delay() {
  byte success = false;
  status_add = addresses;
  byte previous_add = _read_status();
  for (byte add = 0; add < addresses+1; add++) {
    status_add = add;
    byte current_add = _read_status();
    if (current_add == previous_add) {
      success = true;
      break;
    }
    previous_add = current_add;
  }  
  if (status_add == 0) {
    status_add = addresses;
  }
  else {
    status_add--;
  }  
  return success;
}

void initialize_ring_buffer(long delay) {
  byte status_width = sizeof(byte);
  byte delay_width = sizeof(long);
  for (byte add = 0; add <= addresses+1; add++) {
    byte status = add%addresses;
    eeprom_write(status_offset+add,(byte*)&status,status_width);
  }
  eeprom_write(delay_add,(byte*)&delay,delay_width);
}

// debugging functions

// returns contents of specified delay buffer address
long _debug_delay_buffer(byte address) {
  byte width = sizeof(long);
  byte byte_array[width];
  eeprom_read(delay_add+long(width)*address,byte_array,width);
  return *(long*)byte_array;
}

// returns contents of specified status buffer address
byte _debug_status_buffer(byte address) {
  byte width = sizeof(byte);
  byte byte_array[width];
  eeprom_read(status_offset+long(width)*address,byte_array,width);
  return *(byte*)byte_array;
}

// returns value of active address
byte _debug_status_add() {
  return status_add;
}

// writes a sequence of delays ( 0, 1, 2, ..., length-1 )
void _debug_sequence(long length) {
  for (int delay = 0; delay < length; delay++) {
    write_delay(delay);
  }
}



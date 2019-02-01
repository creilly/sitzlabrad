#include "EEPROM.h"
#include "ddg_eeprom.h"

const char init_command = 'i';
const char status_command = 's';
const char delay_command = 'd';
const char init_status_add_command = 'z';
const char status_add_command = 'a';
const char read_command = 'r';
const char write_command = 'w';
const char sequence_command = 'q';
const char print_status_buffer_command = 'p';
const char print_delay_buffer_command = 't';

const char term_char = '\n';

const char col_width = 10;

String success_code = "success!";
String failure_code = "failure!";

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(-1);
}

void loop() {
  Serial.println("(i): [i]nitialize ring buffer");
  Serial.println("(s): read [s]tatus address");
  Serial.println("(d): read [d]elay address");
  Serial.println("(z): initiali[z]e delay");
  Serial.println("(a): read status [a]ddress variable");
  Serial.println("(r): [r]ead delay");
  Serial.println("(w): [w]rite delay");
  Serial.println("(q): write se[q]uence of delays");
  Serial.println("(p): [p]rint status buffer");
  Serial.println("(t): prin[t] delay buffer");
  char command = Serial.readStringUntil(term_char).charAt(0);
  switch (command) {
  case (init_command): {
    Serial.println("enter initial delay (in ns)");
    long delay = Serial.readStringUntil(term_char).toInt();
    initialize_ring_buffer(delay);
    break;
  }
  case (status_command): {
    char prompt[256];
    sprintf(prompt,"enter status buffer address (0-%d)",addresses);
    Serial.println(prompt);
    byte address = Serial.readStringUntil(term_char).toInt()%(addresses+1);
    Serial.println(_debug_status_buffer(address));
    break;
  }
  case (delay_command): {
    char prompt[256];
    sprintf(prompt,"enter delay buffer address (0-%d)",addresses-1);
    Serial.println(prompt);
    byte address = Serial.readStringUntil(term_char).toInt()%addresses;
    Serial.println(_debug_delay_buffer(address));
    break;
  }
  case (init_status_add_command): {
    initialize_delay();
    break;
  }
  case (status_add_command): {
    Serial.println(_debug_status_add());
    break;
  }
  case (read_command): {
    Serial.println(read_delay());
    break;
  }
  case (write_command): {
    Serial.println("enter delay (in ns)");
    long delay = Serial.readStringUntil(term_char).toInt();
    write_delay(delay);
    break;
  }
  case (sequence_command): {
    Serial.println("enter length of sequence");
    long length = Serial.readStringUntil(term_char).toInt();
    _debug_sequence(length);
    break;
  }
  case (print_status_buffer_command): {
    byte address = 0;
    while (true) {
      byte start_address = address;
      byte values[col_width];
      for (int col = 0; col < col_width; col++) {
	values[col] = _debug_status_buffer(address);
	address++;
	if (address>addresses) {
	  break;
	}
      }
      byte end_address = address-1;
      char row[6*col_width+10];
      byte marker = 0;
      marker += sprintf(row+marker,"%3d-%-3d: |",start_address,end_address);
      for (int col = 0; col < address-start_address; col++) {
	marker += sprintf(row+marker," %3d |",values[col]);
      }
      Serial.println(row);
      if (address>addresses) {
	break;
      }
    }
    break;
  }
  case (print_delay_buffer_command): {
    byte address = 0;
    while (true) {
      byte start_address = address;
      long values[col_width];
      for (int col = 0; col < col_width; col++) {
	values[col] = _debug_delay_buffer(address);
	address++;
	if (address==addresses) {
	  break;
	}
      }
      byte end_address = address-1;
      char row[12*col_width+10];
      byte marker = 0;
      marker += sprintf(row+marker,"%3d-%-3d: |",start_address,end_address);
      for (int col = 0; col < address-start_address; col++) {
	marker += sprintf(row+marker," %9ld |",values[col]);
      }
      Serial.println(row);
      if (address==addresses) {
	break;
      }
    }
    break;
  }
  default:
    Serial.println(failure_code);
    return;
  }
  Serial.println(success_code);
}

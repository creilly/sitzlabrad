#include "EEPROM.h"
#include "ddg_eeprom.h"

const char read_command = 'r';
const char write_command = 'w';
const char initialize_command = 'i';
const char id_command = 'i';
const char min_command = '-';
const char max_command = '+';
const char offset_command = 'o';
const char delay_command = 'd';
const char term_char = '\n';

String success_code = "success!";
String failure_code = "failure!";
String init_failure_code = "failed to initialize ring buffer";

byte init_success;
  
void setup() {
  init_success = initialize_delay();
  Serial.begin(115200);
  Serial.setTimeout(-1);
}
char get_io_mode(){
  Serial.println("(r): read eeprom");
  Serial.println("(w): write eeprom");
  Serial.println("(i): initialize ring buffers");
  return Serial.readStringUntil(term_char).charAt(0);
}
char get_param(){
  Serial.println("(i): device id");
  Serial.println("(-): min voltage");
  Serial.println("(+): max voltage");
  Serial.println("(o): offset");
  Serial.println("(d): delay");
  return Serial.readStringUntil(term_char).charAt(0);
}
void loop() {
  char io = get_io_mode();
  if (!init_success) {
    Serial.println(init_failure_code);
    return;
  }
  switch (io) {
  case (read_command): {
    switch (get_param()) {
        
    case (id_command):
      Serial.println(read_id());
      break;
          
    case (min_command):
      Serial.println(read_min());
      break;
          
    case (max_command):
      Serial.println(read_max());
      break;
          
    case (offset_command):
      Serial.println(read_offset());
      break;

    case (delay_command):
      Serial.println(read_delay());
      break;
          
    default:
      Serial.println(failure_code);
      return;
          
      break;
    }
    break;
  }
  case (write_command): {
    char param = get_param();
    Serial.println("enter value");
    String response = Serial.readStringUntil(term_char);
    switch (param) {
        
    case (id_command):
      write_id((byte)response.toInt());
      break;
        
    case (min_command):
      write_min(response.toFloat());
      break;

    case (max_command):
      write_max(response.toFloat());
      break;

    case (offset_command):
      write_offset(response.toInt());
      break;

    case (delay_command):
      write_delay(response.toInt()); // toInt actually returns a long
      break;
	  
    default:
      Serial.println(failure_code);
      return;
    }
    break;
  }
  case (initialize_command): {
    Serial.println("are you sure? y/[n]:");
    char confirmation = Serial.readStringUntil(term_char).charAt(0);
    if (confirmation == 'y' || confirmation == 'Y') {
      Serial.println("enter initial delay (in ns)");
      long delay = Serial.readStringUntil(term_char).toInt();
      initialize_ring_buffer(delay);
      init_success = initialize_delay();
    }
    else {
      Serial.println("initialization canceled");
    }
  }
    break;

  default:
    Serial.println(failure_code);
    return;
  }
  Serial.println(success_code);
}

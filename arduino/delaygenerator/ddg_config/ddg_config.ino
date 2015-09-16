#include "EEPROM.h"
#include "ddg_eeprom.h"

const char read_command = 'r';
const char write_command = 'w';
const char id_command = 'i';
const char min_command = '-';
const char max_command = '+';
const char offset_command = 'o';
const char delay_command = 'd';
const char term_char = '\n';

String success_code = "success!";
String failure_code = "failure!";
  
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(-1);
}
char get_io_mode(){
  Serial.println("(r): read eeprom");
  Serial.println("(w): write eeprom");
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
  char param = get_param();
  switch (io) {
    case (read_command): {
      switch (param) {
        
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
      	  write_offset((int)response.toInt());
          break;

        case (delay_command):
      	  write_delay(response.toInt()); // toInt actually returns a long
          break;
          
        default: {
          Serial.println(failure_code);
          return;
          
        }
        break;
      }
      break;
    }
    default:
      Serial.println(failure_code);
      return;
  }
  Serial.println(success_code);
}

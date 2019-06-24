#include <EEPROM.h> // hack: a dep. of rsm_eeprom but we must include here as well
#include "ssm_eeprom.h" // accesses rsm configuration params

const char read_command = 'r';
const char write_command = 'w';
const char id_command = 'i';
const char term_char = '\n';

String success_code = "success!";
String failure_code = "failure!";

void setup() {
  Serial.setTimeout(-1); // wait forever
  Serial.begin(115200);
}
char get_io_mode(){
  Serial.println("(r): read eeprom");
  Serial.println("(w): write eeprom");
  return Serial.readStringUntil(term_char).charAt(0);
}
char get_param(){
  Serial.println("(i): device id");
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

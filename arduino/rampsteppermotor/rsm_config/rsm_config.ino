#include <EEPROM.h> // hack: a dep. of rsm_eeprom but we must include here as well
#include "rsm_eeprom.h" // accesses rsm configuration params

const char read_command = 'r';
const char write_command = 'w';
const char id_command = 'i';
const char ramp_time_command = 'r';
const char min_period_command = 'p';
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
  Serial.println("(r): ramp time");
  Serial.println("(p): minimum period");
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
          
        case (ramp_time_command):
          Serial.println(read_ramp_time());
          break;
          
        case (min_period_command):
          Serial.println(read_min_period(),6);
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
        
        case (ramp_time_command):
          write_ramp_time(response.toFloat());
          break;

        case (min_period_command):
          write_min_period(response.toFloat());
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

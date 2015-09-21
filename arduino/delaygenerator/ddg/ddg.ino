#include <EEPROM.h> // hack: a dep. of ddg_eeprom but we must include here as well
#include "ddg_eeprom.h" // accesses ddg configuration params
// pins
const byte serial_pin = 2; // feeds data to shift registers
const byte clock_pin = 3; // triggers register shifts
const byte clear_pin = 4; // clears registers (necessary?)
const byte counter_reset_pin = 5; // disables counters during writes
const byte trig_slope_pin = 6; // configures trigger slope

// delay encoding
const byte clock_period = 100; // in ns
const byte counter_bits = 20; // coarse delays from offset to offset + clock_period * 2^counter_bits
const byte dac_bits = 8; // sub-clock cycle resolution of clock_period / 2^dac_bits
const byte total_bits = counter_bits+dac_bits;
const float max_dac_voltage = 5.0; // dac chip produces fractions of this voltage

// commands
const char get_command = 'r'; // if command begins with this char, return current delay
const char set_command = 'w'; // command is followed by desired delay
const char id_command = 'i'; // returns device id
const char term_char = '\n'; // commands are terminated with term_char

// response
const char handshake_response = 'h'; // indicate readiness
const char success_response = 's'; // command successful
const char command_failure_response = 'c'; // invalid command
const char send_delay_response = 'd'; // send desired delay
const char range_failure_response = 'r'; // desired delay invalid

// parameters
byte device_id; // unique ddg identifier
int offset; // minimum achievable delay
float min_voltage, max_voltage; // config parameters for sub cycle delays
long current_delay; // delay currently programmed

void init_pins() {
  pinMode(clock_pin,OUTPUT);
  pinMode(serial_pin,OUTPUT);
  pinMode(clear_pin,OUTPUT);
  pinMode(counter_reset_pin,OUTPUT);
  pinMode(trig_slope_pin,OUTPUT);

  digitalWrite(counter_reset_pin,HIGH);
  digitalWrite(trig_slope_pin,LOW);		
  digitalWrite(clock_pin,LOW);
  digitalWrite(clear_pin,LOW);
  delay(10);
  digitalWrite(clear_pin,HIGH);
}

void init_params() {
  device_id = read_id();
  min_voltage = read_min();
  max_voltage = read_max();
  offset = read_offset();
  current_delay = read_delay();
}

void setup() {
  init_pins();
  init_params();
  set_delay(current_delay);
  Serial.setTimeout(-1); // wait forever
  Serial.begin(115200);
  Serial.println(handshake_response);
}

void loop() {
  Serial.println(handle_command(Serial.readStringUntil(term_char).charAt(0)));
}

char handle_command(char command) {
  switch (command) {
  case id_command:
    Serial.println(device_id);
    return success_response;
  case get_command:
    Serial.println(current_delay);
    return success_response;
  case set_command:
    Serial.println(send_delay_response);
    return set_delay(Serial.readStringUntil(term_char).toInt());
  default:
    return command_failure_response;
  }
}

// method to convert a time in ns to the binary values for counters & call dac08 method and then write to registers
byte set_delay(unsigned long delay) {

  if ((delay <= 0) || (delay >= clock_period*pow(2,20))) {
    return range_failure_response;
  }

  if (delay < offset) { 
    delay = 0;
  }
  else {
    delay = delay - offset;
  }

  unsigned long cycles = delay/long(clock_period);      
  int bits[total_bits]; // store the bits to be written in an int array

  // read cycles into binary array
  for (int k=counter_bits-1; k>-1; k--) {
    bits[k] = (cycles >> k) & 1;
  }
   
  int remainder = delay % clock_period;
  int dac_value = get_dac_value(remainder);

  // read dac_value to binary array
  for (int k=dac_bits-1; k>-1; k--) {
    bits[total_bits-1-k] = (dac_value >> k) & 1;
  }  

  shift(bits, total_bits);
  current_delay = delay + offset; // add back on offset
  write_delay(current_delay);
  return success_response;
}

// writes the delay to the registers
void shift(int *bits, int length) {  
  int time = 10; // time between digital line changes (in us)
  
  digitalWrite(counter_reset_pin,LOW); // disable counters during write

  // load the registers
  for (int i = length-1; i >= 0; i--) {
    if (bits[i] > 0) {
      digitalWrite(serial_pin, HIGH);
    } 
    else {
      digitalWrite(serial_pin, LOW);
    }
    delayMicroseconds(time);
    digitalWrite(clock_pin, HIGH);
    delayMicroseconds(time);
    digitalWrite(clock_pin, LOW);
    delayMicroseconds(time);
  }
  digitalWrite(counter_reset_pin,HIGH); // reenable the counters
}

int get_dac_value(float duration) {
  float clock_period_fraction = duration/float(clock_period);
  float dac_voltage = min_voltage + clock_period_fraction * ( max_voltage - min_voltage );
  float dac_voltage_fraction = dac_voltage / max_dac_voltage;
  int binary_fraction = dac_voltage_fraction * pow(2,dac_bits);
  return binary_fraction;
}

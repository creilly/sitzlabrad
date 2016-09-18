#include <EEPROM.h> // hack: a dep. of rsm_eeprom but we must include here as well
#include "rsm_eeprom.h" // accesses rsm configuration params

// pins
const byte step_pin = 2; // step output to stepper motor driver
const byte stop_pin = 3; // interrupt pin to stop pulse generation. must be pin 2 or 3

// stepper motor parameters to be read from eeprom
byte device_id;
float ramp_time, min_period;
long ramp_steps, initial_period;

// commands
const char id_command = 'i';
const char generate_steps_command = 'g';

// responses
const char generate_steps_ack = 'g';
const char invalid_command_response = 'x';

// return codes
const char completed_code = 'c';
const char stopped_code = 's';
const char invalid_steps_code = 'i';

// handshaking
const char handshake_response = 'H'; // indicate readiness (ddg uses 'h')

const char term_char = '\n'; // commands are terminated with term_char

volatile bool stop_requested = false;

void init_pins() {
  device_id = read_id();
  
  ramp_time = read_ramp_time();
  min_period = read_min_period();
  
  ramp_steps = long(1./2.*ramp_time/min_period);
  initial_period = long(sqrt(2.*ramp_time*min_period)*1E6);
  
  pinMode(step_pin,OUTPUT);
  digitalWrite(step_pin,LOW);
  
  pinMode(stop_pin,INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(stop_pin), on_stop, RISING);
}

void on_stop() {
  stop_requested = true;
}

void setup() {
  init_pins();
  Serial.setTimeout(-1); // wait forever
  Serial.begin(115200);
  Serial.println(handshake_response);
}

void loop() {
  Serial.println(handle_command(Serial.readStringUntil(term_char)[0]));
  // Serial.println(generate_steps(Serial.readStringUntil(term_char).toInt()));
}

String handle_command(char command) {
  String response;
  switch (command) {
  case id_command:
    {
      response = String(device_id);
    }
    break;
  case generate_steps_command:
    { 
      Serial.println(generate_steps_ack);
      long steps_requested;
      steps_requested = Serial.readStringUntil(term_char).toInt();
      long steps_generated;
      long hack;
      char return_code = generate_steps(steps_requested,steps_generated,hack);
      response = String(return_code);
      response.concat(" ");
      response.concat(steps_generated);
      response.concat(" ");
      response.concat(hack);  
    }
    break;
  default:
    {
      response = String(invalid_command_response);
    }
  }
  return response;
}

char generate_steps(long total_steps, long& steps_generated, long& hack) {
  if (total_steps == 0) {
    return invalid_steps_code;
  }
  stop_requested = false;
  long step_period = initial_period;
  long steps = 0;
  long dummy_step_period = 1000;
  long dummy_remainder = 500;
  long dummy_accel_step = 20000;
  long accel_step = 0;
  long accel_steps;
  long remainder = 0;
  long decel_remainder = 0;
  if (ramp_steps < total_steps/2) {
    accel_steps = ramp_steps;
  }
  else {
    accel_steps = total_steps/2;
  }
  long a = 0;
  long b = 0;
  while (steps<accel_steps) {
    if (stop_requested) {
      break;
    }
    generate_step(step_period);
    steps++;
    accel_step++;
    a = 2 * step_period + remainder;
    b = 4 * steps + 1;
    step_period = step_period - a/b;
    remainder = a%b;
  }
  while (total_steps-steps > ramp_steps) {
    if (stop_requested) {
      break;
    }
    generate_step(step_period);
    a = 2 * dummy_step_period + dummy_remainder;
    b = 4 * dummy_accel_step - 1;
    dummy_step_period = dummy_step_period + a/b;
    dummy_remainder = a%b;
    steps++;
    dummy_accel_step--;
  }
  while (accel_step) {
    if (stop_requested) {
      true;
    }
    generate_step(step_period);
    a = 2 * step_period + remainder;
    b = 4 * accel_step - 1;
    step_period = step_period + a/b;
    remainder = a%b;
    steps++;
    accel_step--;
  }
  steps_generated = steps;
  hack = dummy_remainder;
  if (stop_requested) {
    return stopped_code;
  }
  else {
    return completed_code;
  }
}

void generate_step(long step_period) {
  long delay_time = step_period/2;
  if (delay_time > 16E3) {
    delay_time /= 1E3;
    digitalWrite(step_pin,HIGH);
    delay(delay_time);
    digitalWrite(step_pin,LOW);
    delay(delay_time);
  }
  else {
    digitalWrite(step_pin,HIGH);
    delayMicroseconds(delay_time);
    digitalWrite(step_pin,LOW);
    delayMicroseconds(delay_time);
  }
}

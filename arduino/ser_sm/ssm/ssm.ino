#include <EEPROM.h> // hack: a dep. of rsm_eeprom but we must include here as well
#include "ssm_eeprom.h" // accesses rsm configuration params

// stepper motor parameters to be read from eeprom
const byte step_pin = 8;
const byte dir_pin = 9;
byte device_id;

// handshaking
const char handshake_response = 'r'; // indicate readiness (ddg uses 'h', rsm uses 'H')

const char term_char = '\n'; // commands are terminated with term_char

const char GENERATE_PULSES = 's';
const char SET_DIRECTION = 'd';
const char GET_PULSES = 'g';
const char STOP = 'p';
const char FINISHED = 'f';
const char ID = 'i';

const char INVALID_COMMAND_RESPONSE = 'i';
const char SUCCESS_RESPONSE = 's';
const char DEVICE_BUSY_RESPONSE = 'b';
const char DEVICE_STOPPED_RESPONSE = 'p';

char command;
unsigned long data;

unsigned long pulses;
unsigned long pulses_requested;
const unsigned long pulse_threshold = 1001;
unsigned long time_start;
const unsigned long time_interval = 200; // microseconds

bool generating_pulses;
bool awaiting_ack;
bool blocking;
bool phase;
bool dir;

String message;

void setup() {
  device_id = read_id();
  generating_pulses = false;
  awaiting_ack = false;
  
  pinMode(step_pin, OUTPUT);
  digitalWrite(step_pin, LOW);
  
  pinMode(dir_pin, OUTPUT);

  Serial.setTimeout(-1); // wait forever
  Serial.begin(115200);
  Serial.println(handshake_response);  
}

void loop() {
  if (generating_pulses) {
    handle_pulse_generation();
  }
  handle_clients();  
}


void handle_stop() {
  end_pulse_generation();
}

void end_pulse_generation() {
  if (blocking) {
    Serial.println(pulses);
  }
  else {
    awaiting_ack = true;
  }
  generating_pulses = false;
}

void toggle() {
  phase = !phase;
  digitalWrite(step_pin,phase);
  time_start = micros();
}
void handle_pulse_generation() {
  if (micros() - time_start > time_interval) {
    toggle();
    if (phase==HIGH) {
      pulses++;
    }
    else if (pulses==pulses_requested) {
      end_pulse_generation();
    }
  }
}
byte parse_command(char &command,unsigned long &data) {
  command = message.charAt(0);
  if (
    command==GENERATE_PULSES
    ||
    command==GET_PULSES
    ||
    command==SET_DIRECTION
    ||
    command==STOP
    ||
    command==FINISHED
    ||
    command==ID
  ) {
      if (
        command==GENERATE_PULSES
        ||
        command==SET_DIRECTION
      ) {
        char s[255]; 
        message.substring(2).toCharArray(s,255);
        char* t;
        data = strtoul(s,&t,10);
        if (s==t){
          return false;
        }
      }
      return true;
  }
  else {
    return false;
  }
}
void handle_clients() {
  if (Serial.available()) {
    message = Serial.readStringUntil(term_char);
    if (parse_command(command,data)) {
      switch (command) {
      case GENERATE_PULSES:
      	if (generating_pulses || awaiting_ack) {
      	  Serial.println(DEVICE_BUSY_RESPONSE);
      	}
      	else {
      	  pulses = 0;
      	  pulses_requested = data;
      	  phase = LOW;
      	  time_start = micros();
      	  generating_pulses = true;
      	  blocking = pulses_requested < pulse_threshold;
          if (!blocking) {
            Serial.println(-1);
          }
      	}
      	break;
      case GET_PULSES:
      	Serial.println(pulses);
      	break;
      case SET_DIRECTION:
      	if (generating_pulses) {
      	  Serial.println(DEVICE_BUSY_RESPONSE);
      	}
      	else {
      	  digitalWrite(dir_pin,!data); // may want to untoggle the not
      	  Serial.println(SUCCESS_RESPONSE);
      	}
      	break;
      case STOP:
      	if (generating_pulses) {
      	  Serial.println(SUCCESS_RESPONSE);
      	  handle_stop();
      	}
      	else {
      	  Serial.println(DEVICE_STOPPED_RESPONSE);
      	}
      	break;
      case FINISHED:
      	if (awaiting_ack) {
      	  awaiting_ack = false;	  
      	  Serial.println(pulses);
      	}
      	else {
      	  Serial.println(-1);
      	}
        break;
      case ID:
        Serial.println(device_id);
        Serial.println(SUCCESS_RESPONSE);
        break;
      }
    }
    else {
      Serial.println(INVALID_COMMAND_RESPONSE);
    }
  }
}

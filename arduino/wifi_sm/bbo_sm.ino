#include <ESP8266WiFi.h>

const byte max_clients = 255;
const char* ssid = "robin";
const char* password = "scatter12";

const byte step_pin = 0;
const byte dir_pin = 4; // bbo dir is gpio1, kdp dir we're trying gpio4

byte clients_connected;
byte client_index;
byte scratch_index;

const char GENERATE_PULSES = 's';
const char SET_DIRECTION = 'd';
const char GET_PULSES = 'g';
const char STOP = 'p';

const char INVALID_COMMAND_RESPONSE = 'i';
const char SUCCESS_RESPONSE = 's';
const char DEVICE_BUSY_RESPONSE = 'b';
const char DEVICE_STOPPED_RESPONSE = 'p';

char command;
unsigned long data;

WiFiClient set_client;
WiFiClient current_client;
WiFiClient clients[max_clients];

WiFiServer server(80);

unsigned long pulses;
unsigned long pulses_requested;
unsigned long time_start;
const unsigned long time_interval = 2000; // microseconds

bool generating_pulses;
bool phase;
bool dir;

String message;

void setup() {
  generating_pulses = false;
  clients_connected = 0;
  
  pinMode(step_pin, OUTPUT);
  digitalWrite(step_pin, LOW);
  
  pinMode(dir_pin, OUTPUT);
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1);
  }
  server.begin();
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
  set_client.println(pulses);
  set_client.flush();
  set_client.stop();
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
void remove_client(byte client_index) {
  for (scratch_index=client_index+1;scratch_index<clients_connected;scratch_index++) {
    clients[scratch_index-1]=clients[scratch_index];
  }
  clients_connected--;
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
  client_index = 0;
  while (client_index < clients_connected) {
    current_client = clients[client_index];
    if (current_client.available()) {
      message = current_client.readStringUntil('\n');
      if (parse_command(command,data)) {
        client_index++;
        switch (command) {
          case GENERATE_PULSES:
            if (generating_pulses) {
              current_client.println(DEVICE_BUSY_RESPONSE);
              current_client.stop();
            }
            else {
              pulses = 0;
              pulses_requested = data;
              set_client = current_client;
              phase = LOW;
              time_start = micros();
              generating_pulses = true;
            }
            break;
          case GET_PULSES:
            current_client.println(pulses);
            current_client.stop();
            break;
          case SET_DIRECTION:
            if (generating_pulses) {
              current_client.println(DEVICE_BUSY_RESPONSE);
            }
            else {
              digitalWrite(dir_pin,data);
              current_client.println(SUCCESS_RESPONSE);
            }
            current_client.stop();
            break;
          case STOP:
            if (generating_pulses) {
              handle_stop();
              current_client.println(SUCCESS_RESPONSE);
            }
            else {
              current_client.println(DEVICE_STOPPED_RESPONSE);
            }
        }
      }
      else {
        current_client.println(INVALID_COMMAND_RESPONSE);
        current_client.stop();
      }
      remove_client(client_index);
    }
    else {
      if (current_client.connected()) {
        client_index++;
      }
      else {
        remove_client(client_index);
      }
    }
  }
  if (clients_connected<max_clients) {
    current_client = server.available();
    if (current_client) {
      clients[clients_connected]=current_client;
      clients_connected++;
    }
  }
}


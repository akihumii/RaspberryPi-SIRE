#include "wiringpi-serial.h"

#include "easylogging++.h"

WiringPiSerial::WiringPiSerial(const char *device, int baud_rate){
  serial_device_ = device;
  baud_rate_ = baud_rate;
}

WiringPiSerial::~WiringPiSerial(){
  serialClose(serial_file_descriptor_);
}

int WiringPiSerial::Init(){
  if ((serial_file_descriptor_ = serialOpen(serial_device_, baud_rate_)) < 0){
    LOG(ERROR) << ", \"event\":\"wiringpi-serial.Init\", \"errnum\":1, \"msg\":\"Unable to open serial device\"";
    throw std::string("Unable to open serial device");
    return -1;
  }

  // if (wiringPiSetup () == -1){
  //   std::cerr « "Unable to start wiringPi\n";
  //   return -2;
  // }
  LOG(INFO) << ", \"event\":\"wiringpi-serial.Init\", \"errnum\":0, \"msg\":\"Serial initialized!\"";
  FlushStream();
  setBitMode();
  return 0;
}

int WiringPiSerial::SafeRead(const void *buf, size_t count){
  int bytes_read;
  while(count){
    bytes_read = read(serial_file_descriptor_, (uint8_t*)buf, count);
    if(bytes_read <= 0){
      LOG(ERROR) << ", \"event\":\"wiringpi-serial.SafeRead\", \"errnum\":1, \"msg\":\"No data on the serial port!\"";
      return -1;
    }
    count -= bytes_read;
    buf = (uint8_t*)buf + bytes_read;
  }
  return 0;
}

int WiringPiSerial::SafeWrite(const void *buf, size_t count){
  int bytes_written;
  while(count){
    bytes_written = write(serial_file_descriptor_, (uint8_t*)buf, count);
    if(bytes_written <= 0){
      LOG(ERROR) << ", \"event\":\"wiringpi-serial.SafeWrite\", \"errnum\":1, \"msg\":\"Cannot write to the serial port!\"";
      return -1;
    }
    count -= bytes_written;
    buf = (uint8_t*)buf + bytes_written;
  }
  return 0;
}

int WiringPiSerial::SimpleRead(uint8_t *buf, size_t count){
  return read(serial_file_descriptor_, buf, count);
}

int WiringPiSerial::SimpleWrite(uint8_t *buf, size_t count){
  return write(serial_file_descriptor_, buf, count);
}

int WiringPiSerial::FlushStream(){
  serialFlush(serial_file_descriptor_);
  return 0;
}

void WiringPiSerial::setBitMode(){
  tcgetattr(serial_file_descriptor_, &options);
  options.c_cflag &= ~CSIZE;
//  if(bitLength == 5){
//    options.c_cflag |= CS5;
//    LOG(INFO) << ", \"event\":\"Set Bit Length:\", \"errnum\":0, \"msg\":\"5 Bit Mode set!\"";
//  }
//  if(bitLength == 8){
    options.c_cflag |= CS8;
//    LOG(INFO) << ", \"event\":\"Set Bit Length:\", \"errnum\":0, \"msg\":\"8 Bit Mode set!\"";
//  }
  options.c_cflag |= PARENB;
  options.c_cflag &= ~PARODD;
  options.c_cflag &= ~CSTOPB;
  tcsetattr(serial_file_descriptor_, TCSANOW, &options);
}

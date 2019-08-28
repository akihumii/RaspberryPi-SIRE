#ifndef WIRINGPI_SERIAL_H
#define WIRINGPI_SERIAL_H

#include <iostream>
#include <unistd.h>
#include <termios.h>

// #include <wiringPi.h>
#include <wiringSerial.h>

class WiringPiSerial{
  public:
    WiringPiSerial(const char *device, int baud_rate);
    ~WiringPiSerial();
    int Init();

    int SafeRead(const void *buf, size_t count);
    int SafeWrite(const void *buf, size_t count);
    
    // Functions to read/write directly to the serial port
    // Returns the number of bytes actually read/written
    // Can not reliably read multiple bytes so only recommending using single bytes
    int SimpleRead(uint8_t *buf, size_t count);
    int SimpleWrite(uint8_t *buf, size_t count);
    void setBitMode();
    int FlushStream();
  private:
    int serial_file_descriptor_;
    const char *serial_device_;
    int baud_rate_;
    struct termios options;
    unsigned char byte = 0;
};

#endif

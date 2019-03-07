#ifndef PARALLEL_GPIO_H
#define PARALLEL_GPIO_H

#include <iostream>
#include <unistd.h>
#include <termios.h>

#include <wiringPi.h>

#define DATA_RDY 	0
#define CTS 		2
#define RESET		3
#define BIT7		29
#define BIT6		28
#define BIT5		27
#define BIT4		26
#define BIT3		6
#define BIT2		5
#define BIT1		4
#define BIT0		1
#define BITCTRL		7	// HIGH for 8 Bit Mode, LOW for 5 Bit Mode
#define CLK_TUNE	12
#define SYS_TUNE	13

typedef enum BITMODE{
	BITMODE_8,
	BITMODE_5
} BITMODE;

class ParallelGPIO{
	public:
		ParallelGPIO();
		~ParallelGPIO();
		int Init();
		int SafeRead(const void *buf, size_t count);
		unsigned char* getBuffer();
		int getBytesAvailable();
		unsigned char readByte(void);
		void setBitMode(BITMODE value);
		BITMODE getBitMode();
		void resetFPGA();
		void setClockTuneMode(bool flag);
		void setSystemTuneMode(bool flag);
	private:
		BITMODE mode = BITMODE_5;
		FILE *fp;
};

#endif

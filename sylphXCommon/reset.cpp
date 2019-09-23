#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <wiringPi.h>
#include "easylogging++.h"
#include "parallel-gpio.h"
INITIALIZE_EASYLOGGINGPP

ParallelGPIO *data_stream;

int main(int argc, char *argv[]){
	if(wiringPiSetup() == -1){
		LOG(ERROR) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Error!\"";
		return -1;
	}
	LOG(INFO) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Successful!\"";
	data_stream = new ParallelGPIO();
	data_stream->Init();
	data_stream->resetFPGA();
	LOG(INFO) << ", \"event\":\"Reset FPGA\", \"errnum\":0, \"msg\":\"Reset FPGA Successful!!\"";
	return 0;
}
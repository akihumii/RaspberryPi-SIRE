#include "parallel-gpio.h"
#include "easylogging++.h"

ParallelGPIO::ParallelGPIO(){

}

ParallelGPIO::~ParallelGPIO(){
//	fclose(fp);
}

int ParallelGPIO::Init(){
	pinMode(CTS, OUTPUT);
	pinMode(RESET, OUTPUT);
	pinMode(BITCTRL, OUTPUT);
	digitalWrite(RESET, LOW);			// Reset FPGA Module
	digitalWrite(CTS, HIGH);
	digitalWrite(BITCTRL, HIGH);		// Default HIGH (8 Bit Mode)
	pinMode(BIT7, INPUT);
	pinMode(BIT6, INPUT);
	pinMode(BIT5, INPUT);
	pinMode(BIT4, INPUT);
	pinMode(BIT3, INPUT);
	pinMode(BIT2, INPUT);
	pinMode(BIT1, INPUT);
	pinMode(BIT0, INPUT);
	digitalWrite(RESET, HIGH);			// Release Reset for FPGA Module
//	fp = new FILE();
//	if(NULL == (fp = fopen("data.txt", "w"))){
//		printf("Could not open data.txt\n");
//	}
	return 0;
}

unsigned char ParallelGPIO::readByte(void){
	while(!digitalRead(DATA_RDY)){};
	unsigned char byte = (unsigned char) digitalRead(BIT7) << 7 | 
	(unsigned char) digitalRead(BIT6) << 6 | 
	(unsigned char) digitalRead(BIT5) << 5 | 
	(unsigned char) digitalRead(BIT4) << 4 | 
	(unsigned char) digitalRead(BIT3) << 3 | 
	(unsigned char) digitalRead(BIT2) << 2 | 
	(unsigned char) digitalRead(BIT1) << 1 | 
	(unsigned char) digitalRead(BIT0);
	if(mode == BITMODE_5){
		byte &= 0B00011111;
	}
//	usleep(1);
	digitalWrite(CTS, LOW);
//	usleep(1);
	while(digitalRead(DATA_RDY)){};
//	usleep(1);
	digitalWrite(CTS, HIGH);
//	fprintf(fp, "%d\n", byte);
	return byte;
}

int ParallelGPIO::SafeRead(const void *buf, size_t count){
	unsigned char *temp = (unsigned char*) buf;
	for(size_t i = 0; i < count; i++){
		temp[i] = readByte();
	}
	buf = (unsigned char*)buf + count;
	return 0;
}

void ParallelGPIO::setBitMode(BITMODE value){
	mode = value;
	(value == BITMODE_8)? digitalWrite(BITCTRL, HIGH) : digitalWrite(BITCTRL, LOW);
}

void ParallelGPIO::resetFPGA(){
	digitalWrite(RESET, LOW);			// Reset FPGA Module
	usleep(100000);
	digitalWrite(RESET, HIGH);			// Release Reset for FPGA Module
	// usleep(100000);
}

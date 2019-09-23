#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <termios.h>
#include <unistd.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include "fcntl.h"
#include <time.h>
#include <netinet/tcp.h>
#include <wiringPi.h>
#include "wiringpi-serial.h"
#include "easylogging++.h"
#include "ringbuffer.h"
#include "parallel-gpio.h"

#define BUFFER_SIZE 2048
#define SOCKET_SERVER_PORT 8888

INITIALIZE_EASYLOGGINGPP

int socket_desc, client_sock, c, read_size, flag = 1, count = 0, read_len, write_len, retx_count = 0;
struct sockaddr_in server, client;
unsigned char readbuffer[BUFFER_SIZE];
unsigned char writebuffer[BUFFER_SIZE];
unsigned char recvbuffer[32];
bool read_bool = 0;
// WiringPiSerial *fd;
ParallelGPIO *data_stream;
ringbuffer<uint8_t> *rb;
ringbuffer<uint8_t> *rb_parallel;
pthread_t tid[3];
pthread_mutex_t lock;

void *readParallel(void *arg){
	data_stream = new ParallelGPIO();
	data_stream->Init();
	while(1){
		data_stream->readByte();
	}
}

void *readPacket(void *arg){
	while(1){
		// pthread_mutex_lock(&lock);
		if(rb->getFree() > 2048){
			// fd->SafeRead(readbuffer, BUFFER_SIZE);
			rb_parallel->read(readbuffer, BUFFER_SIZE);
			rb->write(readbuffer, BUFFER_SIZE);
			memset(readbuffer, '\0', BUFFER_SIZE);
		}
		else{
			LOG(INFO) << ", \"event\":\"Ring Buffer: \", \"errnum\":0, \"msg\":\"Ring buffer full!\"";
		}
	}
}

void *sendWiFi(void *arg){
	while(1){
		// pthread_mutex_lock(&lock);
		if(rb->getOccupied() > 0){
			rb->read(writebuffer, BUFFER_SIZE);
			if(write(client_sock, writebuffer, BUFFER_SIZE) < 0){
				retx_count++;
				LOG(INFO) << ", \"event\":\"Retransmission: \", \"errnum\":0, \"msg\":\"Occurence: "<< retx_count << "\"";
			}
			memset(writebuffer, '\0', BUFFER_SIZE);
		}
		// memset(writebuffer, '\0', BUFFER_SIZE);
		// pthread_mutex_unlock(&lock);
	}
}

int main(int argc, char *argv[]){

	if(wiringPiSetup() == -1){
		LOG(ERROR) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Error!\"";
		return -1;
	}
	LOG(INFO) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Successful!\"";

	// rb = new ringbuffer<uint8_t>(409600);
	// if(rb->getFree() < 0){
	// 	LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
	// }
	// LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

	rb_parallel = new ringbuffer<uint8_t>(409600);
	if(rb_parallel->getFree() < 0){
		LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
	}
	LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

    if (pthread_mutex_init(&lock, NULL) != 0)
    {
        LOG(ERROR) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initialisation Failed!\"";
        return -1;
    }
    LOG(INFO) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initiation Successful!\"";

	// if(pthread_create(&(tid[0]), NULL, &readPacket, NULL) < 0){
	// 	LOG(ERROR) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread could not be created!\"";
	// }
	// LOG(INFO) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread created!\"";

	if(pthread_create(&(tid[2]), NULL, &readParallel, NULL) < 0){
		LOG(ERROR) << ", \"event\":\"Creating Parallel Thread:\", \"errnum\":0, \"msg\":\"Parallel Thread could not be created!\"";
	}
	LOG(INFO) << ", \"event\":\"Creating Parallel Thread:\", \"errnum\":0, \"msg\":\"Parallel Thread created!\"";


	pthread_join(tid[2], NULL);

	return 0;
}

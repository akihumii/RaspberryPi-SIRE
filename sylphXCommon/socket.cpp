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

#define BUFFER_SIZE 25
#define SOCKET_SERVER_PORT 8888

INITIALIZE_EASYLOGGINGPP
static void acceptConnection();

int socket_desc, client_sock, c, sync_len = 0, syncIndex = 0, flag = 1, count = 0, read_len, write_len, retx_count = 0, odin_socket;
struct sockaddr_in server, client, odin_addr;
// unsigned char parallelbuffer[BUFFER_SIZE];
unsigned char recvbuffer[16];
bool read_bool = 0;
WiringPiSerial *fd;
// ParallelGPIO *data_stream;
ringbuffer<uint8_t> *rb;
// ringbuffer<uint8_t> *rb_parallel;
pthread_t tid[4];
pthread_mutex_t lock1, lock2;

static int findSyncPulse(unsigned char* buf, int len){
	int i;
	for(i = 0; i < len; i++){
		if((uint8_t) buf[i] == 0 && (uint8_t) buf[i+3] == 90 
				&& (uint8_t) buf[i+25] == 0 && (uint8_t) buf[i+25+3]){
			return i;
		}
	}
	return -1;
}

bool disconnectSignalReceived(){
	return (recv(client_sock, &recvbuffer, 16, MSG_DONTWAIT) > 0);
}

void *readPacket(void *arg){
	fd = new WiringPiSerial("/dev/serial0", 500000);
	fd->Init();
	unsigned char readbuffer[BUFFER_SIZE*20];
	unsigned char sync_buf[2];
	while(1){
		if(rb->getFree() > BUFFER_SIZE*20+1){
			fd->SafeRead(readbuffer, BUFFER_SIZE*20);
			if(sync_len <= 0){
				sync_len = recv(odin_socket, &sync_buf, 2, MSG_DONTWAIT);
				if(sync_len > 0){
					goto slotSyncPulse;
				}
			}
			else{
				slotSyncPulse:
				syncIndex = findSyncPulse(readbuffer, BUFFER_SIZE*20);
				if(syncIndex != -1){
					readbuffer[syncIndex] = 255;
					sync_len = 0;
					syncIndex = -1;
					memset(sync_buf, '\0', 2);
				}
			}
			rb->write(readbuffer, BUFFER_SIZE*20);
			memset(readbuffer, '\0', BUFFER_SIZE*20);
		}
		if(disconnectSignalReceived()){
			LOG(INFO) << ", \"event\":\"Disconnect: \", \" msg \" : 0, Disconnect Signal Received! \"";
//			break;
			acceptConnection();
		}
	}
}

void *sendWiFi(void *arg){
	unsigned char writebuffer[BUFFER_SIZE*20];
	while(1){
		if(rb->getOccupied() > BUFFER_SIZE*20+1){
			rb->read(writebuffer, BUFFER_SIZE*20);
			if(write(client_sock, writebuffer, BUFFER_SIZE*20) < 0){
				retx_count++;
				LOG(INFO) << ", \"event\":\"Retransmission: \", \"errnum\":0, \"msg\":\"Occurence: "<< retx_count << "\"";
			}
			memset(writebuffer, '\0', BUFFER_SIZE*20);
		}
		if(disconnectSignalReceived()){
			LOG(INFO) << ", \"event\":\"Disconnect: \", \" msg \" : 0, Disconnect Signal Received! \"";
//			break;
			acceptConnection();
		}
	}
}

static void connectOdin(void){
	odin_socket = socket(AF_INET , SOCK_STREAM , 0);
	if(odin_socket < 0){
		LOG(INFO) << ", \"event\":\"Odin socket creation:\", \"errnum\":0, \"msg\":\"Failed to create Odin socket!\"";
	}
	else{
		LOG(INFO) << ", \"event\":\"Odin socket creation:\", \"errnum\":0, \"msg\":\"Odin socket created!\"";
	}

	int temp, flag = 1;
	do{
		usleep(500000);
		LOG(INFO) << ", \"event\":\"Connecting Odin:\", \"errnum\":0, \"msg\":\"Trying to connect to Odin!\"";
		odin_addr.sin_family = AF_INET;
		odin_addr.sin_port = htons(45454);
		odin_addr.sin_addr.s_addr = inet_addr("192.168.4.1");
		temp = connect(odin_socket, (struct sockaddr *)&odin_addr, sizeof(struct sockaddr_in));
	}while(temp < 0);
	LOG(INFO) << ", \"event\":\"Connecting Odin:\", \"errnum\":0, \"msg\":\"Odin connected!\"";

	fcntl(odin_socket, F_SETFL, O_NONBLOCK);
	setsockopt(odin_socket, IPPROTO_TCP, TCP_NODELAY, (void *)&flag, sizeof(flag));
}

static void acceptConnection(){
	client_sock = accept(socket_desc, (struct sockaddr *)&client, (socklen_t *)&c);
	fcntl(client_sock, F_SETFL, O_NONBLOCK);
	setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, (void *)&flag, sizeof(flag));

	if(client_sock<0){
		LOG(ERROR) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket Connection Error!\"";
		// return -1;
	}
	LOG(INFO) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket connected!\"";
}

static void waitForSylph(){
	socket_desc = socket(AF_INET, SOCK_STREAM, 0);

	if(socket_desc == -1){
		LOG(ERROR) << ", \"event\":\"Socket creation\", \"errnum\":0, \"msg\":\"Socket Creation Error!\"";
		// return -1;
	}
	LOG(INFO) << ", \"event\":\"Socket creation\", \"errnum\":0, \"msg\":\"Socket Creation Successful!\"";

	server.sin_family = AF_INET;
	server.sin_addr.s_addr = INADDR_ANY;
	server.sin_port = htons(SOCKET_SERVER_PORT);

binding:
	if(!bind(socket_desc, (struct sockaddr *)&server, sizeof(server))){
		LOG(ERROR) << ", \"event\":\"Socket Binding\", \"errnum\":0, \"msg\":\"Socket Binding Error!\"";
		goto binding;
	}

	LOG(INFO) << ", \"event\":\"Socket Binding\", \"errnum\":0, \"msg\":\"Socket Binding Successful!\"";

	listen(socket_desc, 1);

	LOG(INFO) << ", \"event\":\"Listening:\", \"errnum\":0, \"msg\":\"Waiting for connections...\"";

	c = sizeof(struct sockaddr_in);

	acceptConnection();
}

int main(int argc, char *argv[]){
	if(wiringPiSetup() == -1){
		LOG(ERROR) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Error!\"";
		return -1;
	}
	LOG(INFO) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Successful!\"";

	rb = new ringbuffer<uint8_t>(BUFFER_SIZE*2000);
	if(rb->getFree() < 0){
		LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
	}
	LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

	connectOdin();
	waitForSylph();

	// rb_parallel = new ringbuffer<uint8_t>(BUFFER_SIZE*20);
	// if(rb_parallel->getFree() < 0){
	// 	LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
	// }
	// LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

	// if (pthread_mutex_init(&lock1, NULL) != 0)
	// {
	// 	LOG(ERROR) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initialisation Failed!\"";
	// 	return -1;
	// }
	// LOG(INFO) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initiation Successful!\"";

	// if (pthread_mutex_init(&lock2, NULL) != 0)
	// {
	// 	LOG(ERROR) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initialisation Failed!\"";
	// 	return -1;
	// }
	// LOG(INFO) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initiation Successful!\"";

	if(pthread_create(&(tid[0]), NULL, &readPacket, NULL) < 0){
		LOG(ERROR) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread could not be created!\"";
	}
	LOG(INFO) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread created!\"";

	if(pthread_create(&(tid[1]), NULL, &sendWiFi, NULL) < 0){
		LOG(ERROR) << ", \"event\":\"Creating WiFi Thread:\", \"errnum\":0, \"msg\":\"WiFi Thread could not be created!\"";
	}
	LOG(INFO) << ", \"event\":\"Creating WiFi Thread:\", \"errnum\":0, \"msg\":\"WiFi Thread created!\"";

	for(int i = 0; i < 2; i++){
		pthread_join(tid[i], NULL);
	}

	return 0;
}

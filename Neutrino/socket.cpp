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
#include "../common/wiringpi-serial.h"
#include "../common/easylogging++.h"
#include "../common/ringbuffer.h"
#include "../common/parallel-gpio.h"

#define BUFFER_SIZE 160
#define BUFFER_SIZE_2 3200
#define SOCKET_SERVER_PORT 8888
#define FPGA_CLOCK_SPEED 19200

INITIALIZE_EASYLOGGINGPP

int socket_desc, client_sock, c, read_size, flag = 1, count = 0, read_len, write_len, retx_count = 0, odin_socket;
int sync_len = 0, syncIndex = 0;

struct sockaddr_in server, client, odin_addr;

unsigned char buf_in[BUFFER_SIZE];
unsigned char buf_out[BUFFER_SIZE_2];
unsigned char buf_cmd[32];
unsigned char buf_sync[BUFFER_SIZE];
unsigned char buf_sync_cmd[32];

bool read_bool = 0;
int recv_count = 0;

bool isFrDetected = false;
uint8_t counter = 0;
int counterIndex = 0;

WiringPiSerial *fd;
ParallelGPIO *data_stream;

ringbuffer<uint8_t> *rb_wifi;
ringbuffer<uint8_t> *rb_sync;

pthread_t tid[4];
pthread_mutex_t lock_rb_wifi, lock_data;

BITMODE selectedMode = BITMODE_8;

static int findSyncPulse(unsigned char* buf, int len){
    int i = 0;
    if(data_stream->getBitMode() == BITMODE_8){
        for(i = 0; i < len-4; i++){
            if((uint8_t) buf[i] == 0xF0 && (uint8_t) buf[i+4] == 0){
                return i+4;
            }
        }
    }
    else{
        for(i = 0; i < len-9; i++){
            if((uint8_t) buf[i] == 0x10 && (uint8_t) buf[i+1] == 0x1F && (uint8_t) buf[i+9] == 0){
                return i+9;
            }
        }
    }
    return -1;
}

void slotSyncPulse(){
    syncIndex = findSyncPulse(buf_sync, BUFFER_SIZE);
    if(syncIndex != -1){
        buf_sync[syncIndex] = 255;
        sync_len = 0;
        syncIndex = -1;
        memset(buf_sync_cmd, '\0', 32);
    }
}

static void acceptConnection(void){
    client_sock = accept(socket_desc, (struct sockaddr *)&client, (socklen_t *)&c);
    // fcntl(client_sock, F_SETFL, O_NONBLOCK);
    setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, (void *)&flag, sizeof(flag));

    if(client_sock<0){
        LOG(ERROR) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket Connection Error!\"";
        close(socket_desc);
    }
    LOG(INFO) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket connected!\"";
}

static void connectOdin(void){
    odin_socket = socket(AF_INET , SOCK_STREAM , 0);
    if(odin_socket < 0){
        fprintf(stdout, "Failed to create Odin socket\n");
    }
    else{
        fprintf(stdout, "Odin socket created\n");
    }

    int temp, flag = 1;
    do{
        usleep(500000);
        fprintf(stdout, "Trying to connect to Odin\n");
        odin_addr.sin_family = AF_INET;
        odin_addr.sin_port = htons(45454);
        odin_addr.sin_addr.s_addr = inet_addr("192.168.4.1");
        temp = connect(odin_socket, (struct sockaddr *)&odin_addr, sizeof(struct sockaddr_in));
    }while(temp < 0);
    fprintf(stdout, "Connected to Odin\n");

    // fcntl(odin_socket, F_SETFL, O_NONBLOCK);
    setsockopt(odin_socket, IPPROTO_TCP, TCP_NODELAY, (void *)&flag, sizeof(flag));
}

static void waitForSylph(void){
    socket_desc = socket(AF_INET, SOCK_STREAM, 0);

    if(socket_desc == -1){
        LOG(ERROR) << ", \"event\":\"Socket creation\", \"errnum\":0, \"msg\":\"Socket Creation Error!\"";
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

    listen(socket_desc, 99);

    LOG(INFO) << ", \"event\":\"Listening:\", \"errnum\":0, \"msg\":\"Waiting for connections...\"";

    c = sizeof(struct sockaddr_in);

    acceptConnection();
}

void initRecvDataParam(){
    data_stream = new ParallelGPIO();
    data_stream->Init();
    data_stream->resetFPGA();
    fd = new WiringPiSerial("/dev/serial0", FPGA_CLOCK_SPEED);
    fd->Init();
    recv_count = 0;
}

void setupCmdSettings(){
    switch(buf_cmd[6]){
        case 180:
        case 181:
        case 229:
            data_stream->resetFPGA();
            rb_wifi->resetBuffer();
            rb_sync->resetBuffer();
            read_bool = true;
            data_stream->setBitMode(BITMODE_5);
            break;
        case 36:
            data_stream->setClockTuneMode(true);
        case 52:
        case 53:
        case 101:
        case 21:
            data_stream->resetFPGA();
            rb_wifi->resetBuffer();
            rb_sync->resetBuffer();
            read_bool = true;
            data_stream->setBitMode(BITMODE_8);
            break;
        default:
            read_bool = false;
            data_stream->setBitMode(BITMODE_8);
            LOG(INFO) << ", \"event\":\"Stop Reading:\", \"errnum\":0, \"msg\":\"Stop Reading!\"";
    }
}

void sendCmd(){
    if(buf_cmd[0] == 50){
        fprintf(stdout, "Disconnect signal received!\n");
        close(client_sock);
        client_sock = -1;
        acceptConnection();
    }
    else{
        if(fd->SimpleWrite(buf_cmd, recv_count) < 0){
            LOG(ERROR) << ", \"event\":\"Sending Command:\", \"errnum\":0, \"msg\":\"Command cannot be sent!" << "\"";
        }
        else{
            LOG(INFO) << ", \"event\":\"Sending Command:\", \"errnum\":0, \"msg\":\"Command Sent!\"";
        }
        memset(buf_cmd, '\0', recv_count);
    }
}

bool verifyCounter(){
    if (isFrDetected == false){
        // findSyncPulse returns sync pulse index, so can calculate counter index based on that
        if (data_stream->getBitMode() == BITMODE_8){
            counterIndex = findSyncPulse(buf_in, BUFFER_SIZE) - 3;
        }
        else{
            counterIndex = findSyncPulse(buf_in, BUFFER_SIZE) - 7;
        }

        if (counterIndex != -1){
            counter = buf_in[counterIndex];
            isFrDetected = true;
        }
        else {
            return;
        }
    }

    while(counterIndex < BUFFER_SIZE){
        if (counter != buf_in[counterIndex]){
            printf("err counter index read: %d %d\n", counter, buf_in[counterIndex]);
            isFrDetected = false;
            break;
        }

        if (data_stream->getBitMode() == BITMODE_8){
            counter = (counter + 2) % 256;
            counterIndex += 16;
        }
        else{
            counter = (counter + 2) % 32;
            counterIndex += 32;
        }
    }
    counterIndex = counterIndex % BUFFER_SIZE;

    if (!isFrDetected){
        for (int i = 0; i < BUFFER_SIZE; i ++){
            printf("%d ", buf_in[i]);
        }
        printf("\n ");
    }

    return isFrDetected;

}

void storeData(){
    pthread_mutex_lock(&lock_data);
    data_stream->SafeRead(buf_in, BUFFER_SIZE);
    pthread_mutex_unlock(&lock_data);
    
    // for debugging, use the following cond instead
    // if ((verifyCounter()) && (rb_wifi->getFree() > BUFFER_SIZE+1)){
    if (rb_wifi->getFree() > BUFFER_SIZE+1){
        pthread_mutex_lock(&lock_rb_wifi);
        rb_wifi->write(buf_in, BUFFER_SIZE);
        pthread_mutex_unlock(&lock_rb_wifi);
    }
}

// FPGA -> internal buffer
void *recvData(void *arg){
    initRecvDataParam();
    while(1){
        if(read_bool){
        storeData();
        }
    }
}

// find sync pulse from internal buffer
void *readPacket(void *arg){
    // minimal changes from original, logic-wise it wont work
    // TODO: remove rb-wifi dependant, modify recv() usage for tcp-blocking
    while(1){
        if(rb_wifi->getFree() > BUFFER_SIZE+1 && rb_sync->getOccupied() > BUFFER_SIZE+1){
            rb_sync->read(buf_sync, BUFFER_SIZE);

            if(sync_len <= 0){
                sync_len = recv(odin_socket, &buf_sync_cmd, 32, MSG_DONTWAIT);
            }
            if(sync_len > 0){
                slotSyncPulse();
            }
            // rb_wifi->write(buf_sync, BUFFER_SIZE);
            memset(buf_sync, '\0', BUFFER_SIZE);
        }
    }
}

// internal buffer -> wifi out
void *sendWiFi(void *arg){
    while(1){
        if(rb_wifi->getOccupied() > BUFFER_SIZE_2+1){
            pthread_mutex_lock(&lock_rb_wifi);
            rb_wifi->read(buf_out, BUFFER_SIZE_2);
            pthread_mutex_unlock(&lock_rb_wifi);

            if(client_sock > 0){
                if(write(client_sock, buf_out, BUFFER_SIZE_2) < 0){
                    printf("wifi packet dropped.\n");
                }
            }
        }
    }
}

// wifi in -> FPGA
void *recvWiFi(void *arg){
    while(1){
        recv_count = recv(client_sock, &buf_cmd, 32, 0);
        if(recv_count > 0){
            pthread_mutex_lock(&lock_data);
            data_stream->setClockTuneMode(false);
            setupCmdSettings();
            sendCmd();
            pthread_mutex_unlock(&lock_data);
        }
    }
}

int main(int argc, char *argv[]){
    // commented out useless logging for readablility, all of them should be running fine
    // if there is any error, the program should terminate, cron log can be used to store that error
    // wiringPiSetup() no longer returns anything valuable, see http://wiringpi.com/reference/setup/

    wiringPiSetup();
    rb_wifi = new ringbuffer<uint8_t>(BUFFER_SIZE_2 * 1000);    // ~3.2MB, overkill imo
    rb_sync = new ringbuffer<uint8_t>(BUFFER_SIZE * 10);        // ~1.6KB, unused rn
    pthread_mutex_init(&lock_rb_wifi, NULL);
    pthread_mutex_init(&lock_data, NULL);
    // connectOdin();
    waitForSylph();

    pthread_create(&(tid[1]), NULL, &sendWiFi, NULL);
    pthread_create(&(tid[1]), NULL, &recvWiFi, NULL);
    pthread_create(&(tid[2]), NULL, &recvData, NULL);
    
    for(int i = 0; i < 3; i++){
        pthread_join(tid[i], NULL);
    }

    return 0;
}

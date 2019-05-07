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

INITIALIZE_EASYLOGGINGPP

int socket_desc, client_sock, c, read_size, flag = 1, count = 0, read_len, write_len, retx_count = 0, odin_socket;
int sync_len = 0, syncIndex = 0;

struct sockaddr_in server, client, odin_addr;

unsigned char parallelbuffer[BUFFER_SIZE];
unsigned char readbuffer[BUFFER_SIZE];
unsigned char writebuffer[BUFFER_SIZE_2];
unsigned char recvbuffer[32];
unsigned char sync_buf[32];

bool read_bool = 0;

int recv_count = 0;

bool isFrDetected = false;
uint8_t counter = 0;
int counterIndex = 0;

bool isFrDetected2 = false;
uint8_t counter2 = 0;
int counterIndex2 = 0;


WiringPiSerial *fd;
ParallelGPIO *data_stream;

ringbuffer<uint8_t> *rb;
ringbuffer<uint8_t> *rb_parallel;

pthread_t tid[4];
pthread_mutex_t lock1, lock2;

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

void initParallelTask(){
    data_stream = new ParallelGPIO();
    data_stream->Init();
    data_stream->resetFPGA();
    fd = new WiringPiSerial("/dev/serial0", 19200);
    fd->Init();
    recv_count = 0;
}

void verifyCounter(){
    if (isFrDetected == false){
        if (data_stream->getBitMode() == BITMODE_8){
            counterIndex = findSyncPulse(parallelbuffer, BUFFER_SIZE) - 3;
        }
        else{
            counterIndex = findSyncPulse(parallelbuffer, BUFFER_SIZE) - 7;
        }

        if (counterIndex != -1){
            counter = parallelbuffer[counterIndex];
            isFrDetected = true;
        }
    }

    while(counterIndex < BUFFER_SIZE){
        if (counter != parallelbuffer[counterIndex]){
            printf("err counter index read: %d %d\n", counter, parallelbuffer[counterIndex]);
            isFrDetected = false;
            // break;
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
            printf("%d ", parallelbuffer[i]);
        }
        printf("\n ");
    }

}

void verifyCounter2(){
    counterIndex2 = findSyncPulse(writebuffer, BUFFER_SIZE_2) - 3;

    if (!isFrDetected2 && counterIndex2 != -1){
        counter2 = writebuffer[counterIndex2];
        isFrDetected2 = true;
    }

    while(counterIndex2 < BUFFER_SIZE_2 && isFrDetected2 == true){
        if (counter2 != writebuffer[counterIndex2]){
            printf("err count index wifi: %d %d\n", counter2, writebuffer[counterIndex2]);
            isFrDetected2 = false;
            break;
        }
        counter2 = (counter2 + 2) % 256;
        counterIndex2 += 16;
    }
    counterIndex2 -= BUFFER_SIZE_2;

    if (!isFrDetected2){
        for (int i = 0; i < BUFFER_SIZE_2; i ++){
            printf("%d ", writebuffer[i]);
        }
        printf("\n ");
    }

}


void setupCmdSettings(){
    switch(recvbuffer[6]){
        case 180:
        case 181:
        case 229:
            data_stream->resetFPGA();
            rb->resetBuffer();
            rb_parallel->resetBuffer();
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
            rb->resetBuffer();
            rb_parallel->resetBuffer();
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
    if(recvbuffer[0] == 50){
        fprintf(stdout, "Disconnect signal received!\n");
        close(client_sock);
        client_sock = -1;
        acceptConnection();
    }
    else{
        if(fd->SimpleWrite(recvbuffer, recv_count) < 0){
            LOG(ERROR) << ", \"event\":\"Sending Command:\", \"errnum\":0, \"msg\":\"Command cannot be sent!" << "\"";
        }
        else{
            LOG(INFO) << ", \"event\":\"Sending Command:\", \"errnum\":0, \"msg\":\"Command Sent!\"";
        }
        memset(recvbuffer, '\0', recv_count);
    }
}

void resolveCmd(){
    recv_count = recv(client_sock, &recvbuffer, 32, 0);
    if(recv_count > 0){
        data_stream->setClockTuneMode(false);
        setupCmdSettings();
        sendCmd();
    }
    else{
        //TODO: err read cmd
    }
}

void storeData(){
    data_stream->SafeRead(parallelbuffer, BUFFER_SIZE);

    // if (data_stream->getBitMode() == BITMODE_5){
    //     return;
    // }

    // verifyCounter();

    pthread_mutex_lock(&lock1);
    rb->write(parallelbuffer, BUFFER_SIZE);
    // rb_parallel->write(parallelbuffer, BUFFER_SIZE);
    pthread_mutex_unlock(&lock1);
    memset(parallelbuffer, '\0', BUFFER_SIZE);
}

void slotSyncPulse(){
    syncIndex = findSyncPulse(readbuffer, BUFFER_SIZE);
    if(syncIndex != -1){
        readbuffer[syncIndex] = 255;
        sync_len = 0;
        syncIndex = -1;
        memset(sync_buf, '\0', 32);
    }
}

void *readParallel(void *arg){
    initParallelTask();
    while(1){
        if(rb->getFree() < BUFFER_SIZE+1){
            printf("buffer overflow, write\n");
            while (rb->getFree() < BUFFER_SIZE+1){}
        }
        if(read_bool){
        pthread_mutex_lock(&lock2);
        storeData();
        pthread_mutex_unlock(&lock2);
        }

    }
}

void *readPacket(void *arg){
    while(1){
        if(rb->getFree() > BUFFER_SIZE+1 && rb_parallel->getOccupied() > BUFFER_SIZE+1){
            rb_parallel->read(readbuffer, BUFFER_SIZE);

            if(sync_len <= 0){
                sync_len = recv(odin_socket, &sync_buf, 32, MSG_DONTWAIT);
            }
            if(sync_len > 0){
                slotSyncPulse();
            }

            // rb->write(readbuffer, BUFFER_SIZE);
            memset(readbuffer, '\0', BUFFER_SIZE);
        }
    }
}

void *sendWiFi(void *arg){
    while(1){
        if(rb->getOccupied() > BUFFER_SIZE_2+1){
            pthread_mutex_lock(&lock1);
            int len = rb->read(writebuffer, BUFFER_SIZE_2);
            if (len != BUFFER_SIZE_2){
                printf("buffer overflow, read\n");
            }
            pthread_mutex_unlock(&lock1);

            // verifyCounter2();

            if(client_sock > 0){
                if(write(client_sock, writebuffer, BUFFER_SIZE_2) < 0){
                    printf("wifi packet dropped.\n");
                }
            }
            memset(writebuffer, '\0', BUFFER_SIZE_2);
        }
    }
}

void *recvWiFi(void *arg){
    while(1){
        if(client_sock > 0){
            pthread_mutex_lock(&lock2);
            resolveCmd();
            pthread_mutex_unlock(&lock2);
        }
    }
}

int main(int argc, char *argv[]){
    if(wiringPiSetup() == -1){
        LOG(ERROR) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Error!\"";
        return -1;
    }
    LOG(INFO) << ", \"event\":\"wiringpi-Setup\", \"errnum\":0, \"msg\":\"Wiring Pi Setup Successful!\"";

    rb = new ringbuffer<uint8_t>(BUFFER_SIZE_2 * 1000);
    rb_parallel = new ringbuffer<uint8_t>(BUFFER_SIZE * 10);

    // if(rb->getFree() < 0){
    //     LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
    // }
    // LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

    // if(rb_parallel->getFree() < 0){
    //     LOG(ERROR) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer could not be created!\"";
    // }
    // LOG(INFO) << ", \"event\":\"Ring buffer initialisation\", \"errnum\":0, \"msg\":\"Ring buffer created!\"";

    // if (pthread_mutex_init(&lock1, NULL) != 0)
    // {
    //     LOG(ERROR) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initialisation Failed!\"";
    //     return -1;
    // }
    // LOG(INFO) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initiation Successful!\"";

    // if (pthread_mutex_init(&lock2, NULL) != 0)
    // {
    //     LOG(ERROR) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initialisation Failed!\"";
    //     return -1;
    // }
    // LOG(INFO) << ", \"event\":\"Mutex Initialisation\", \"errnum\":0, \"msg\":\"Mutex Initiation Successful!\"";

    pthread_mutex_init(&lock1, NULL);
    pthread_mutex_init(&lock2, NULL);

    // connectOdin();
    waitForSylph();

    // if(pthread_create(&(tid[0]), NULL, &readPacket, NULL) < 0){
    //     LOG(ERROR) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread could not be created!\"";
    // }
    // LOG(INFO) << ", \"event\":\"Creating readPacket Thread:\", \"errnum\":0, \"msg\":\"Packet Thread created!\"";

    if(pthread_create(&(tid[2]), NULL, &sendWiFi, NULL) < 0){
        LOG(ERROR) << ", \"event\":\"Creating WiFi Thread:\", \"errnum\":0, \"msg\":\"WiFi Thread could not be created!\"";
    }
    LOG(INFO) << ", \"event\":\"Creating WiFi Thread:\", \"errnum\":0, \"msg\":\"WiFi Thread created!\"";
    
    pthread_create(&(tid[2]), NULL, &recvWiFi, NULL);

    if(pthread_create(&(tid[1]), NULL, &readParallel, NULL) < 0){
        LOG(ERROR) << ", \"event\":\"Creating Parallel Thread:\", \"errnum\":0, \"msg\":\"Parallel Thread could not be created!\"";
    }
    LOG(INFO) << ", \"event\":\"Creating Parallel Thread:\", \"errnum\":0, \"msg\":\"Parallel Thread created!\"";

    for(int i = 0; i < 3; i++){
        pthread_join(tid[i], NULL);
    }

    return 0;
}

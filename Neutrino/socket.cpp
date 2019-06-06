#include <sys/socket.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <time.h>

#include <wiringPi.h>
#include <pthread.h>
#include <termios.h>
#include <unistd.h>

#include <arpa/inet.h>
#include <netinet/tcp.h>

#include "../common/wiringpi-serial.h"
#include "../common/easylogging++.h"
#include "../common/ringbuffer.h"
#include "../common/parallel-gpio.h"

#define BUFFER_SIZE 160
#define BUFFER_SIZE_2 3200
#define SOCKET_SERVER_PORT 8888

#define CLK_PIN 21      // physical pin 29
#define CMD_GATE_PIN 23 // physical pin 33

INITIALIZE_EASYLOGGINGPP

struct sockaddr_in server, client, odin_addr;

unsigned char buf_in[BUFFER_SIZE];
unsigned char buf_out[BUFFER_SIZE_2];
unsigned char buf_cmd[32];
unsigned char buf_sync[BUFFER_SIZE];
unsigned char buf_sync_cmd[32];

WiringPiSerial *fd;
ParallelGPIO *data_stream;
BITMODE bitmode = BITMODE_8;

ringbuffer<uint8_t> *rb_wifi;
ringbuffer<uint8_t> *rb_sync;

pthread_t thread[3];
pthread_mutex_t lock_rb_wifi, lock_data;

int socket_desc, client_sock, c, read_size, flag = 1, count = 0, read_len, write_len, retx_count = 0, odin_socket;
int sync_len = 0, syncIndex = 0;

int recv_count = 0;
bool is_read_data = 0;

bool is_fr_detected = false;
uint8_t counter = 0;
int counter_index = 0;

static int find_sync_pulse(unsigned char* buf, int len){
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

static void accept_connection(void){
    client_sock = accept(socket_desc, (struct sockaddr *)&client, (socklen_t *)&c);
    // fcntl(client_sock, F_SETFL, O_NONBLOCK);
    setsockopt(client_sock, IPPROTO_TCP, TCP_NODELAY, (void *)&flag, sizeof(flag));

    if(client_sock<0){
        LOG(ERROR) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket Connection Error!\"";
        close(socket_desc);
    }
    LOG(INFO) << ", \"event\":\"Accepting:\", \"errnum\":0, \"msg\":\"Socket connected!\"";
}

static void connect_odin(void){
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

static void wait_for_sylph(void){
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

    accept_connection();
}

int stick_thread_to_core(pthread_t* thread, int core_id) {
    int num_cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (core_id < 0 || core_id >= num_cores){
        return EINVAL;
    }
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    return pthread_setaffinity_np(*thread, sizeof(cpu_set_t), &cpuset);
}

void init_recv_data_task(){
    data_stream = new ParallelGPIO();
    data_stream->Init();
    data_stream->resetFPGA();

    int clk_speed = 0;
    if(digitalRead(CLK_PIN)){
        clk_speed =19200;
        fprintf(stdout, "clk speed: 19200\n");
    }
    else{
        clk_speed = 38400;
        fprintf(stdout, "clk speed: 38400\n");
    }

    fd = new WiringPiSerial("/dev/serial0", clk_speed);
    fd->Init();
    recv_count = 0;
}

void setup_cmd_settings(){
    switch(buf_cmd[6]){
        case 180:
        case 181:
        case 229:
            data_stream->resetFPGA();
            rb_wifi->resetBuffer();
            rb_sync->resetBuffer();
            is_read_data = true;
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
            is_read_data = true;
            data_stream->setBitMode(BITMODE_8);
            break;
        default:
            is_read_data = false;
            data_stream->setBitMode(BITMODE_8);
            LOG(INFO) << ", \"event\":\"Stop Reading:\", \"errnum\":0, \"msg\":\"Stop Reading!\"";
    }
}

void write_cmd(){
    if(buf_cmd[0] == 50){
        fprintf(stdout, "Disconnect signal received!\n");
        close(client_sock);
        client_sock = -1;
        accept_connection();
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

bool verify_counter(){
    if (is_fr_detected == false){
        // find_sync_pulse returns sync pulse index, so can calculate counter index based on that
        if (data_stream->getBitMode() == BITMODE_8){
            counter_index = find_sync_pulse(buf_in, BUFFER_SIZE) - 3;
        }
        else{
            counter_index = find_sync_pulse(buf_in, BUFFER_SIZE) - 7;
        }

        if (counter_index != -1){
            counter = buf_in[counter_index];
            is_fr_detected = true;
        }
        else {
            return is_fr_detected;
        }
    }

    while(counter_index < BUFFER_SIZE){
        if (counter != buf_in[counter_index]){
            printf("err counter index read: %d %d\n", counter, buf_in[counter_index]);
            is_fr_detected = false;
            break;
        }

        if (data_stream->getBitMode() == BITMODE_8){
            counter = (counter + 2) % 256;
            counter_index += 16;
        }
        else{
            counter = (counter + 2) % 32;
            counter_index += 32;
        }
    }
    counter_index = counter_index % BUFFER_SIZE;

    if (!is_fr_detected){
        for (int i = 0; i < BUFFER_SIZE; i ++){
            printf("%d ", buf_in[i]);
        }
        printf("\n ");
    }

    return is_fr_detected;

}

void store_data(){
    pthread_mutex_lock(&lock_data);
    data_stream->SafeRead(buf_in, BUFFER_SIZE);
    pthread_mutex_unlock(&lock_data);

    // for debugging, use the following if condition instead
    // if ((verify_counter()) && (rb_wifi->getFree() > BUFFER_SIZE+1)){
    if (rb_wifi->getFree() > BUFFER_SIZE+1){
        pthread_mutex_lock(&lock_rb_wifi);
        rb_wifi->write(buf_in, BUFFER_SIZE);
        pthread_mutex_unlock(&lock_rb_wifi);
    }
}

void init_gpio_pin(){
    wiringPiSetup();
    pinMode (CMD_GATE_PIN, OUTPUT) ;
    // pinMode (CTS_PIN, OUTPUT) ;
    digitalWrite(CMD_GATE_PIN,LOW);
    delay(100);
    digitalWrite(CMD_GATE_PIN,LOW);
}

// FPGA -> internal buffer
void *recv_data(void *arg){
    init_recv_data_task();

    while(1){
        if(is_read_data){
            store_data();
        }
    }
}

// internal buffer -> wifi out
void *send_wifi(void *arg){
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
void *recv_wifi(void *arg){
    while(1){
        recv_count = recv(client_sock, &buf_cmd, 32, 0);
        if(recv_count > 0){
            is_read_data = false;
            digitalWrite(CMD_GATE_PIN,HIGH);
            usleep(100000);
            pthread_mutex_lock(&lock_data);
            data_stream->setClockTuneMode(false);
            setup_cmd_settings();
            write_cmd();
            pthread_mutex_unlock(&lock_data);
            usleep(100000);
            digitalWrite(CMD_GATE_PIN,LOW);
        }
    }
}

void init_main(){
    init_gpio_pin();
    rb_wifi = new ringbuffer<uint8_t>(BUFFER_SIZE_2 * 1000);    // ~3.2MB, overkill imo
    rb_sync = new ringbuffer<uint8_t>(BUFFER_SIZE * 10);        // ~1.6KB, unused rn
    pthread_mutex_init(&lock_rb_wifi, NULL);
    pthread_mutex_init(&lock_data, NULL);
}

void init_all_threads(){
    pthread_create(&(thread[0]), NULL, &recv_data, NULL);
    pthread_create(&(thread[1]), NULL, &recv_wifi, NULL);
    pthread_create(&(thread[2]), NULL, &send_wifi, NULL);

    stick_thread_to_core(&(thread[0]),1);
    stick_thread_to_core(&(thread[1]),2);
    stick_thread_to_core(&(thread[2]),3);

    for(int i = 0; i < 3; i++){
        pthread_join(thread[i], NULL);
    }
}

int main(int argc, char *argv[]){
    init_main();
    wait_for_sylph();
    init_all_threads();

    return 0;
}

CC=g++
RM= rm -rf
CFLAGS= -c -Wall
LDFLAGS= -lpthread -lwiringPi
SOURCES=../common/wiringpi-serial.cpp ../common/easylogging++.cpp ../common/parallel-gpio.cpp socket.cpp
OBJECTS=$(SOURCES:.cpp=.o)
EXECUTABLE=neutrino

all: $(SOURCES) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

.cpp.o:
	$(CC) $(CFLAGS) $(LDFLAGS) $< -o $@

clean:
	$(RM) $(OBJECTS) $(EXECUTABLE)

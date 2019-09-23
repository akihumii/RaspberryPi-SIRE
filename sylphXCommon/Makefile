CC=g++
RM= rm -rf
CFLAGS= -c -Wall
LDFLAGS= -lpthread -lwiringPi
SOURCES=wiringpi-serial.cpp easylogging++.cpp parallel-gpio.cpp socket.cpp
OBJECTS=$(SOURCES:.cpp=.o)
EXECUTABLE=sylphx

all: $(SOURCES) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

.cpp.o:
	$(CC) $(CFLAGS) $(LDFLAGS) $< -o $@

clean:
	$(RM) $(OBJECTS) $(EXECUTABLE)

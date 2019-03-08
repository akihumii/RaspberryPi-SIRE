# RaspberryPi-SIRE

This repository comprises of C++ and Python code for Raspberry Pi 3B+ that is used for Neutrino and SylphX.

Data Acquisition and Transmission portion is written in C++, and Classification portion is written in Python.

OS used for the development of Raspberry Pi 3B+ is Raspbian Stretch Lite, which can be downloaded at:
```

https://downloads.raspberrypi.org/raspbian_lite_latest
```

For first setup, please refer to this link:
```
https://github.com/shih91at/RaspberryPi-SIRE/blob/master/Infomation/FirstSetup.txt

```

Important setup steps are listed below:

1) Connecting to WiFi:
```
	wpa_passphrase "Odin AP" "password" >> /etc/wpa_supplicant/wpa_supplicant.conf
```

2) Remove autologin:
```
	sudo ln -fs /etc/systemd/system/autologin@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
```

3) Install programs:
```
	sudo apt-get install wiringpi
	sudo apt-get install vim
	sudo apt-get install git
	sudo apt-get install bc
```

4) Enable SSH:
```
	sudo raspi-config
```

5) Configure UART:
```
	https://raspberrypi.stackexchange.com/questions/45570/how-do-i-make-serial-work-on-the-raspberry-pi3/45571#45571
	To enable it you need to change enable_uart=1 in /boot/config.txt.
```

6) Disable BlueTooth:

https://scribles.net/disabling-bluetooth-on-raspberry-pi/

The steps below shows how to disable on-board Bluetooth and related services. Those steps also disable loading the related kernel modules such as bluetooth, hci_uart, btbcm, etc at boot.

6a. Open /boot/config.txt file.
```
	sudo nano /boot/config.txt
```
6b. Add below, save and close the file.
```
	# Disable Bluetooth
	dtoverlay=pi3-disable-bt
```

6c. Disable related services.
```
	sudo systemctl disable hciuart.service
	sudo systemctl disable bluealsa.service
	sudo systemctl disable bluetooth.service
```
6d. Reboot to apply the changes
```
	sudo reboot
```
Even after disabling on-board Bluetooth and related services, Bluetooth will be available when a Bluetooth adapter is plugged in.


7) Automatic launch program:
Create a file in /lib/systemd/system/[program-name].service
```
	[Unit]
	Description=[program-name] startup
	After=multi-user.target
	
	[Service]
	ExecStart=/home/pi/[program-destination]
	
	[Install]
	WantedBy=multi-user.target
```

Type the following command to activate the service
```
	sudo systemctl daemon-reload
	sudo systemctl enable [program-name].service
	sudo systemctl start [program-name].service
	sudo reboot
```

For pinout, please refer to this:
![](https://user-images.githubusercontent.com/19749458/53934296-491b8080-40dd-11e9-8190-aee72b1c48c3.png)
![](https://user-images.githubusercontent.com/19749458/54015754-a259e180-41bb-11e9-8cb3-67e74a2ea640.png)

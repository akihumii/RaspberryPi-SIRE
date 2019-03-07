%% configureRpi

board = targetHardware('Raspberry Pi');

board.DeviceAddress = '192.168.137.75';
board.Username = 'pi';
board.Password = 'raspberry';

board

 deploy(board,'onlineClassificationRPi')

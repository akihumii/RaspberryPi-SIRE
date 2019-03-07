function onlineClassificationRPi() %#codegen
% Create a Raspberry Pi object

classInfo = classOnlineClassification(); % Initiatialize the object

setTcpip(classInfo,'127.0.0.1',8888,'NetworkRole','client','Timeout',1)

tcpip(classInfo); % create tcpip object

openPort(classInfo); % open channel port
disp('Successfully open port...')

disp('Failed open port...')

end
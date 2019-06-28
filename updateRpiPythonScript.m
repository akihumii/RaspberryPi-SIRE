function [] = updateRpiPythonScript()
%UPDATERPIPYTHONSCRIPT Delete the outdated python scripts in Rpi and
%transfer the updated ones into Rpi.
%   Detailed explanation goes here
directory = fullfile('C:','Users','lsitsai','Documents','GitHub','RaspberryPi-SIRE','pythonClassification');
systemCmd = sprintf('pscp -pw raspberry -scp %s%s*.py pi@192.168.4.3:~/Python/', directory, filesep);
status = system(systemCmd);
if ~status
    popMsg('finished...');
else
    popMsg('Failed transferring...');
end
end


import multiprocessing


class OdinCommandHandler(multiprocessing.Process):
    def __init__(self, odin_obj, change_parameter_event, odin_command_queue):
        multiprocessing.Process.__init__(self)
        self.odin_obj = odin_obj
        self.change_parameter_event = change_parameter_event
        self.odin_command_queue = odin_command_queue

    def run(self):
        while True:
            if self.change_parameter_event.is_set():
                while not self.odin_command_queue.empty():
                    command = self.odin_command_queue.get()
                    self.odin_obj.sock.send(self.odin_obj.convert_to_char(command))
                    print('sent command to Odin...')
                    print(command)

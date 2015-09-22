import numpy as np
import zmq
from multiprocessing import Process, Queue
from world import mapping, vehicles
from engine.server.server import ThreadedUDPServer, UDP_Interrupt
from engine.server.server_conf import settings
from engine.server.message_passing.zmq.zmq_workers import ZMQ_Worker_Sub
from world.mapping import map
from utils import logging_thread
from utils.utils import Interrupt
from engine.server.web_services.web_update import web_post

KILL_COMMAND = 'DEATH'

HOST = 'localhost'
PORT = 2002

class WorkflowManager(object):

    def __init__(self):
        #self.logger = logging.getLogger('py_map_server')
        self.processes = {}
        self.threads = {}
        self.context = zmq.Context()
        self.zmq_result = Queue()
        self.commands = Queue()
        self.logger = Queue()

    def start_engine(self):
        self.start_logging()
        self.start_server_process()
        #self.start_zmq_processes()
        self.start_map_process()
        #self.start_web_services()

    def init_model(self):
        pass

    def start_logging(self):
        logger = logging_thread.LogThread(self.logger)
        logger.daemon = True
        self.threads['logging_thread'] = logger
        logger.start()


    def start_web_services(self):
        rt = Interrupt(5, web_post, url=None, data=None, headers=None)  # it auto-starts, no need of rt.start()

    def start_server_process(self):
        """
        Starts a threaded UDP server for taking API calls. This was mainly impleneted as a communication layer between
        Matlab and Python. Because it is cumbersome, other options are being pursued, including higher level socket
        APIs like LCM and ZMQ.

        Note that the server process will instantiate it's own map interface. When all of it's functionality has been
        duplicated by other means, this module will be deprecated,
        """
        map_server = ThreadedUDPServer((HOST, PORT), UDP_Interrupt)
        server_process = Process(name='server_process', target=map_server.serve_forever)
        self.processes['server_process'] = server_process
        self.logger.put("Threaded server loop running in process:'{}'".format(server_process.name))
        print("UDP server running in process: '{}'".format(server_process.name))
        server_process.daemon = True
        server_process.start()


    def start_matlab_process(self):
        """
        :return:
        """

    def start_map_process(self):
        """
        Instantiates a Map object and makes it's services available in a process. This process listens for requests
        as a ZMQ subscriber.

        @todo: This ought to be something other than a subscriber?

        """
        map_process = map.MapProcess(settings['FILE_CONFIG']['filename'])
        self.processes['map_process'] = map_process
        self.logger.put("{} beginning..".format(map_process.name))
        map_process.start()
        self.logger.put("{} running in: {}".format(map_process.name, map_process.pid))

    def start_zmq_processes(self):
        """
        Initialize ZMQ communication links in a process, interface to QGIS
        :return:
        """
        zmq_worker_qgis = ZMQ_Worker_Sub(qin=self.commands, qout=self.zmq_result)
        zmq_worker_qgis.start()
        self.threads['qgis_worker'] = zmq_worker_qgis
        #self.logger.info("Threaded ZMQ loop running in: {}".format(zmq_worker_qgis.name))
        self.logger.put("Threaded ZMQ loop running in: {}".format(zmq_worker_qgis.name))
        print("ZMQ processes running in: '{}'".format(zmq_worker_qgis.name))




#  @todo: remove executable from server file into a workflow_manager file
if __name__ == "__main__":
    try:
        subscriptions = []
        manager = WorkflowManager()
        manager.start_engine()
        command = raw_input('Server Command:')
        if command == 'shutdown':
            print "Giving the kill command"
            manager.commands.put(KILL_COMMAND)
            for process in manager.processes.values():
                print process
                process.terminate()
            for thread in manager.threads.values():
                print thread
                #thread.kill()
    except KeyboardInterrupt:
        pass


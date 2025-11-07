import multiprocessing
import sys
import threading
import time
from PyQt5.QtWidgets import QApplication
from gui.app.main_window import InterfaceWindow
from maspy import *
import re
from maspy.logger import QueueListener
from gui.assets.theme.styler import load_stylesheet

class InterfaceProcess:
    def __init__(self):
        self.command_queue = multiprocessing.Queue()
        self.new_queue = multiprocessing.Queue()

    def _dispatch_log_records(self, listener):
        try:
            while True:
                log_list = listener.get_records()
                if log_list:
                    self.new_queue.put(log_list)
                
                time.sleep(5)
                
        except Exception as e:
            print(f"ERRO NO DISPATCHER DE LOGS: {e}", file=sys.__stderr__)

    def start(self):
        listener = QueueListener()
        aux = str(Admin()._num_agent)
        valores = re.findall(r':\s*(\d+)', aux)
        num_agents = sum(int(valor) for valor in valores)

        log_dispatcher_thread = threading.Thread(
            target=self._dispatch_log_records, 
            args=(listener,), 
            daemon=True
        )
        log_dispatcher_thread.start()

        self.process = multiprocessing.Process(
            target=self._run, 
            args=(self.command_queue, num_agents, self.new_queue)
        )
        self.process.start()

    def _run(self, command_queue, num_agents, new_queue):
        app = QApplication(sys.argv)

        stylesheet = load_stylesheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)

        window = InterfaceWindow(command_queue, num_agents, new_queue)
        window.show()
        sys.exit(app.exec_())
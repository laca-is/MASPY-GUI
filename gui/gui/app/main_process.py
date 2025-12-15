import multiprocessing
import sys
import threading
import time
import re
from queue import Empty 
from PyQt5.QtWidgets import QApplication
from gui.app.main_window import InterfaceWindow
from maspy import Admin
from maspy.logger import QueueListener
from gui.assets.theme.styler import load_stylesheet

class InterfaceProcess:
    def __init__(self):
        self.command_queue = multiprocessing.Queue()
        self.new_queue = multiprocessing.Queue()

    def _dispatch_log_records(self, listener):
        buffer = []
        last_flush = time.time()
        BATCH_SIZE = 500
        FLUSH_INTERVAL = 0.05
        
        try:
            while True:
                
                records = listener.get_records() 
                
                if records:
                    buffer.extend(records)
                else:
                    time.sleep(1)

                current_time = time.time()
                
                if buffer and (len(buffer) >= BATCH_SIZE or (current_time - last_flush) >= FLUSH_INTERVAL):
                    self.new_queue.put(buffer)
                    buffer = []
                    last_flush = current_time
                
        except Exception as e:
            print(f"ERRO CRÍTICO NO DISPATCHER DE LOGS: {e}", file=sys.__stderr__)

    def start(self):
        listener = QueueListener()
        try:
            aux = str(Admin()._num_agent)
            valores = re.findall(r':\s*(\d+)', aux)
            num_agents = sum(int(valor) for valor in valores)
        except:
            num_agents = 0

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
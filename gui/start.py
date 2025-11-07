import threading
import time
from queue import Empty

from maspy import Admin
from gui.app.main_process import InterfaceProcess

def run_mas_simulation():
    #Admin().slow_cycle_by(cycle_delay) 
    
    Admin().start_system()

def start_interface():
    interface_process = InterfaceProcess()
    interface_process.start()
    
    simulation_thread = threading.Thread(target=run_mas_simulation, daemon=True)

    simulation_thread.start()

    while interface_process.process.is_alive():
        try:
            command_data = interface_process.command_queue.get(timeout=0.5)

            command = None
            if isinstance(command_data, tuple):
                command = command_data[0]
            else:
                command = command_data

            #if command == 'START_SIMULATION':
                #simulation_thread = threading.Thread(target=run_mas_simulation, args=(delay_s,), daemon=True)
                #simulation_thread.start()
                
            delay_s = float(command_data[1])
                
            
            if command == 'TOGGLE_PAUSE':
                Admin().pause_system()  # com defeito

        except Empty:
            continue
        except (KeyboardInterrupt, SystemExit):
            print("[Script Principal] Interrupção recebida. Encerrando...")
            break
            
    print("[Script Principal] A janela da GUI foi fechada.")
    interface_process.process.join()
    print("[Script Principal] Processo da GUI finalizado. Encerrando o programa.")


if __name__ == '__main__':
    start_interface()
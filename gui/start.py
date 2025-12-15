import threading
import sys
import time
from queue import Empty
import multiprocessing

try:
    from maspy import Admin
except ImportError:
    print("[Start] AVISO: Biblioteca 'maspy' não encontrada. O backend não funcionará.")
    Admin = None

from gui.app.main_process import InterfaceProcess

def run_mas_simulation():
    if Admin:
        print("[Simulação] Iniciando sistema MASPY...")
        time.sleep(1)
        Admin().start_system()
    else:
        print("[Simulação] Modo Mock: MASPY não está presente.")
        while True:
            time.sleep(1)

def start_interface():
    interface_process = InterfaceProcess()
    interface_process.start()

    simulation_thread = threading.Thread(target=run_mas_simulation, daemon=True)
    simulation_thread.start()

    print("[Main] Interface e Simulação iniciadas. Aguardando comandos...")

    while interface_process.process.is_alive():
        try:
            command_data = interface_process.command_queue.get(timeout=0.1)

            command = command_data[0] if isinstance(command_data, tuple) else command_data

            if command == 'TOGGLE_PAUSE':
                print("[Main] Comando recebido: PAUSAR/RETOMAR SIMULAÇÃO")
                
                if Admin:
                    try:
                        Admin().pause_system()
                        print("[Main] Admin().pause_system() chamado com sucesso.")
                        
                    except Exception as e:
                        print(f"[Main] Erro ao tentar pausar o MASPY: {e}")

            elif command == 'START_SIMULATION':
                delay = command_data[1] if isinstance(command_data, tuple) else 0
                print(f"[Main] Comando START recebido. Delay: {delay}")
            
        except Empty:
            continue
            
        except (KeyboardInterrupt, SystemExit):
            print("[Main] Interrupção recebida. Encerrando...")
            break
        except Exception as e:
            print(f"[Main] Erro inesperado no loop principal: {e}")

    interface_process.process.join()

if __name__ == '__main__':
    multiprocessing.freeze_support() 
    start_interface()
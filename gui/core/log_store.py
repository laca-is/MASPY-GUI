import json
import queue
import re
import ast
import bisect
from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot

class LogStore(QObject):
    store_updated = pyqtSignal()
    environment_state_updated = pyqtSignal(dict)
    agent_list_updated = pyqtSignal(list)
    environment_history_updated = pyqtSignal(str, dict) 

    def __init__(self, new_queue):
        super().__init__()
        self.new_queue = new_queue

        self.all_logs_timeline = []
        self.logs_by_agent = defaultdict(list)
        self.logs_by_class = defaultdict(list)
        self.message_logs = []
        
        self.agent_log_indices = defaultdict(list)
        
        self.environment_state_snapshots = {} 
        self.environment_states_history = []  
        self.environment_change_history = defaultdict(list) 

        self.known_agents = set()
        self.total_message_count = 0
        self.emitted_agent_list = False 

        self.is_live = True
        self.current_timeline_index = 0
        
        self.timeline_ms_map = [] 
        self.total_duration_ms = 0 
        
        self.all_intentions_history = []
        self.agent_last_intention_tracker = {}

        self.processing_timer = QTimer(self)
        self.processing_timer.setInterval(50) 
        self.processing_timer.timeout.connect(self._read_and_process_queue)
        
        self.ui_notify_timer = QTimer(self)
        self.ui_notify_timer.setInterval(1000) 
        self.ui_notify_timer.timeout.connect(self._notify_ui)
        
        self.has_new_data = False
        #print("[LogStore V4] Iniciado (com Time Travel).") 

    def start_polling(self):
        self.processing_timer.start()
        self.ui_notify_timer.start()
        #print("[LogStore V4] Polling iniciado.") 

    @pyqtSlot(int)
    def set_current_timeline_index(self, index):
        self.current_timeline_index = index
        max_index = len(self.all_logs_timeline) - 1
        if max_index < 0: max_index = 0
        
        self.is_live = (index >= max_index)
        
        current_states = self.get_environment_states_at_index(index)
        self.environment_state_updated.emit(current_states)

    @pyqtSlot()
    def toggle_live_mode(self):
        self.is_live = not self.is_live
        #print(f"[LogStore] Modo Live alterado para: {self.is_live}")
        
        if self.is_live:
            max_index = len(self.all_logs_timeline) - 1
            if max_index < 0: max_index = 0
            self.current_timeline_index = max_index
            self.store_updated.emit()

    def _notify_ui(self):
        if self.has_new_data and self.is_live:
            self.has_new_data = False
            self.store_updated.emit()
            
            if not self.emitted_agent_list and self.known_agents:
                 self._emit_agent_list()
    
    def _time_to_ms(self, time_str):
        if not isinstance(time_str, str):
            return 0
        try:
            h, m, s_ms = time_str.split(':')
            if '.' not in s_ms:
                s_ms = f"{s_ms}.000"
                
            s, ms = s_ms.split('.')
            ms = ms.ljust(3, '0')[:3] 
            
            total_ms = int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
            return total_ms
        except (ValueError, TypeError, AttributeError, Exception) as e:
            #print(f"Erro ao converter system_time '{time_str}': {e}")
            return self.total_duration_ms 
    
    def _read_and_process_queue(self):
        try:
            while True:
                log_bundle = self.new_queue.get_nowait()
                for json_string in log_bundle:
                    try:
                        log_data = json.loads(json_string)
                        self._index_log(log_data)
                        self.has_new_data = True
                    except json.JSONDecodeError:
                        print(f"Erro ao decodificar JSON: {json_string}")
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Erro fatal em _read_and_process_queue: {e}") 

    def _index_log(self, log_data):
        log_index = len(self.all_logs_timeline)
        log_data['log_index'] = log_index
        
        self.all_logs_timeline.append(log_data)
        
        class_name = log_data.get("class_name")
        if not class_name:
            return
            
        self.logs_by_class[class_name].append(log_data)

        if class_name == "Agent":
            agent_name = log_data.get("my_name")
            if agent_name:
                self.logs_by_agent[agent_name].append(log_data)
                self.agent_log_indices[agent_name].append(log_index)
                
                if agent_name not in self.known_agents:
                    self.known_agents.add(agent_name)
                    self.emitted_agent_list = False 
                
                current_last_intention = log_data.get('last_intention')
                previous_last_intention = self.agent_last_intention_tracker.get(agent_name)

                if (current_last_intention and 
                    current_last_intention != 'null' and 
                    current_last_intention != previous_last_intention):
                    
                    entry = {
                        "system_time": log_data.get("system_time"),
                        "log_index": log_index,
                        "agent_name": agent_name,
                        "last_event": log_data.get('last_event', 'Gatilho desconhecido'),
                        "intention_str": current_last_intention
                    }
                    self.all_intentions_history.append(entry)
                    self.agent_last_intention_tracker[agent_name] = current_last_intention
        
        elif class_name == "Channel":
            self._parse_channel_log(log_data)
            
        elif class_name == "Environment":
            self._parse_environment_log(log_data) 
        
        system_time = log_data.get("system_time")
        current_ms = self._time_to_ms(system_time)
        self.timeline_ms_map.append(current_ms)
        self.total_duration_ms = current_ms 

    def _emit_agent_list(self):
        if not self.known_agents:
            return
        
        filtered_agents = []
        for agent_name in self.known_agents:
            if f"{agent_name}_1" in self.known_agents:
                continue
            filtered_agents.append(agent_name)
            
        sorted_agents = sorted(list(filtered_agents))
        self.agent_list_updated.emit(sorted_agents)
        self.emitted_agent_list = True 

    def _parse_channel_log(self, log_data):
        desc = log_data.get("desc", "")
        if not isinstance(desc, str):
            return 
            
        if desc.startswith("connected_agents:"):
            try:
                agents_list_str = desc.split(":", 1)[1].strip()
                agents_list = ast.literal_eval(agents_list_str)
                if isinstance(agents_list, list):
                    new_agents_set = set(agents_list)
                    if new_agents_set != self.known_agents:
                        #print(f"[LogStore] Corrigindo lista de agentes. Fonte: {new_agents_set}")
                        self.known_agents = new_agents_set
                        self.emitted_agent_list = False 
                        self._emit_agent_list() 
            except Exception as e:
                print(f"[LogStore V4] ERRO ao parsear connected_agents: {e} | DADO: {desc}")
                
        match = re.search(r"(\w+)\s+sending\s+([^:]+):\s*(.*)\s+to\s+([\w\s,\[\]']+)", desc)
        if match:
            sender, performative, content, receiver_raw = match.groups()
            receiver = receiver_raw.strip()
            
            parsed_msg = {
                "system_time": log_data.get("system_time"),
                "log_index": log_data['log_index'], 
                "sender": sender,
                "receiver": receiver,
                "performative": performative.strip(),
                "content": {"raw": content.strip()} 
            }
            self.message_logs.append(parsed_msg)
            self.total_message_count += 1
            
    def _parse_percept_string(self, percept_str):
        if not isinstance(percept_str, str):
            return str(percept_str) 
        match = re.search(r"Percept\('([^']+)',\s*\((.*?)\),\s*'([^']+)'\)", percept_str)
        if match:
            name = match.group(1)
            args = match.group(2).replace("'", "").split(',') 
            source = match.group(3)
            clean_args = [arg.strip() for arg in args if arg.strip()]
            if len(clean_args) == 1:
                return f"{name}({clean_args[0]}) [Fonte: {source}]"
            elif len(clean_args) > 1:
                return f"{name}{tuple(clean_args)} [Fonte: {source}]"
            else:
                return f"{name}() [Fonte: {source}]"
        return percept_str 

    def _parse_environment_log(self, log_data):
        env_name = log_data.get("my_name")
        if not env_name:
            return
            
        desc = log_data.get("desc", "")
        system_time = log_data.get("system_time", "00:00:00")
        log_index = log_data['log_index']
        agent_action = log_data.get("action", "N/A")
        
        history_entry = None

        if desc == "Creating Percept":
            history_entry = {
                "time": system_time,
                "log_index": log_index,
                "type": "create",
                "content": self._parse_percept_string(log_data.get("percept(s)")),
                "agent_action": f"{agent_action} ({log_data.get('agent')})"
            }
        elif desc == "Changing Percept":
             history_entry = {
                "time": system_time,
                "log_index": log_index,
                "type": "change",
                "content": f"{self._parse_percept_string(log_data.get('old_percept'))} → {self._parse_percept_string(log_data.get('new_percept'))}",
                "agent_action": f"{agent_action} ({log_data.get('agent')})"
            }
        elif desc == "Deleting Percept":
            history_entry = {
                "time": system_time,
                "log_index": log_index,
                "type": "delete",
                "content": self._parse_percept_string(log_data.get("percept(s)")),
                "agent_action": f"{agent_action} ({log_data.get('agent')})"
            }

        if history_entry:
            self.environment_change_history[env_name].append(history_entry)
            if self.is_live:
                self.environment_history_updated.emit(env_name, history_entry)

        percepts_list = log_data.get("percepts")
        if not isinstance(percepts_list, (list, dict)):
             return

        if isinstance(percepts_list, list) and len(percepts_list) > 0:
            current_state_dict = percepts_list[0]
        elif isinstance(percepts_list, dict):
             current_state_dict = percepts_list
        else:
            current_state_dict = {}

        aggregate_state = {
            'percepts': {},
            'connected_agents': log_data.get('connected_agents', [])
        }
        
        try:
            for key, value_str in current_state_dict.items():
                aggregate_state['percepts'][key] = self._parse_percept_string(value_str)

            if aggregate_state['percepts']:
                self.environment_states_history.append(
                    (env_name, log_data['log_index'], aggregate_state)
                )
                
                if (self.is_live and 
                    self.environment_state_snapshots.get(env_name) != aggregate_state):
                    
                    self.environment_state_snapshots[env_name] = aggregate_state
                    self.environment_state_updated.emit(self.environment_state_snapshots)
                
        except Exception as e:
            print(f"Erro ao processar item de percepts {env_name}: {e} | DADO: {percepts_list}")

    def get_full_timeline(self):
        return self.all_logs_timeline
        
    def get_logs_for_agent(self, agent_name):
        all_logs = self.logs_by_agent.get(agent_name, [])
        if self.is_live:
            return all_logs
            
        return [log for log in all_logs if log['log_index'] <= self.current_timeline_index]
        
    def get_all_messages(self):
        if self.is_live:
            return self.message_logs
            
        return [msg for msg in self.message_logs if msg['log_index'] <= self.current_timeline_index]
    
    def get_all_intentions_history(self):
        if self.is_live:
            return self.all_intentions_history
            
        return [i for i in self.all_intentions_history if i['log_index'] <= self.current_timeline_index]
    
    def get_environment_change_history(self, env_name):
        all_history = self.environment_change_history.get(env_name, [])
        if self.is_live:
            return all_history
        
        return [log for log in all_history if log['log_index'] <= self.current_timeline_index]
        
    def get_environment_states_at_index(self, index):
        latest_states = {}
        for (env_name, log_index, state) in self.environment_states_history:
            if log_index <= index:
                latest_states[env_name] = state
        return latest_states

    def get_latest_agent_state_before_index(self, agent_name, log_index):
        agent_logs = self.logs_by_agent.get(agent_name, [])
        indices = self.agent_log_indices.get(agent_name, [])
        
        if not agent_logs or not indices:
            return {}

        insertion_point = bisect.bisect_right(indices, log_index)
        
        if insertion_point == 0:
            return {}
        
        return agent_logs[insertion_point - 1]

    def get_total_duration_ms(self):
        return self.total_duration_ms

    def get_index_from_ms(self, ms_value):
        if not self.timeline_ms_map:
            return 0
        
        if ms_value >= self.total_duration_ms:
            return len(self.timeline_ms_map) - 1

        index = bisect.bisect_left(self.timeline_ms_map, ms_value)
        return index

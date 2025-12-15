import json
import queue
import re
import bisect
from collections import defaultdict
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot

class BaseLog:
    __slots__ = ('log_index', 'system_time', 'time_ms', 'class_name')
    def __init__(self, index, time_str, ms, cls_name):
        self.log_index = index
        self.system_time = time_str
        self.time_ms = ms
        self.class_name = cls_name
    def get(self, key, default=None): return getattr(self, key, default)
    def __getitem__(self, key): return getattr(self, key)

class MessageLog(BaseLog):
    __slots__ = ('sender', 'receiver', 'performative', 'content', 'sender_action')
    def __init__(self, index, time_str, ms, sender, receiver, perf, content, action):
        super().__init__(index, time_str, ms, "Channel")
        self.sender = sender
        self.receiver = receiver
        self.performative = perf
        self.content = content
        self.sender_action = action

class AgentLog(BaseLog):
    __slots__ = ('agent_name', 'cycle', 'action', 'beliefs', 'goals', 
                 'running_intentions', 'last_event', 'last_intention', 'desc',
                 'perceptions', 'envs', 'chs', 'events')
    def __init__(self, index, time_str, ms, name, data):
        super().__init__(index, time_str, ms, "Agent")
        self.agent_name = name
        self.cycle = data.get('cycle', 0)
        self.desc = data.get('desc', '')
        self.beliefs = data.get('beliefs') or []
        self.goals = data.get('goals') or []
        self.running_intentions = data.get('running_intentions') or []
        self.last_event = data.get('last_event', '')
        self.last_intention = data.get('last_intention', '')
        self.perceptions = data.get('perceptions') or {}
        self.envs = data.get('envs') or []
        self.chs = data.get('chs') or []
        self.events = data.get('events') or []
        self.action = self._extract_action(self.desc, self.running_intentions)

    def _extract_action(self, desc, intentions):
        if not desc: return "Ocioso"
        if "doing action" in desc or "action:" in desc:
            match = re.search(r"(?:doing action|action:)\s*\*?(\w+)", desc)
            if match: return f"Running: {match.group(1)}"
        if intentions:
            first = intentions[0]
            if "->" in first or "]" in first:
                try:
                    match = re.search(r"(?:->|\]\s*,)\s*([\w\d_]+)\(", first)
                    if match: return f"Plan: {match.group(1)}"
                except: pass
        return "Processando"

class IntentionLog(BaseLog):
    __slots__ = ('agent_name', 'intention', 'trigger', 'cycle')
    def __init__(self, index, time_str, ms, agent, intention, trigger, cycle):
        super().__init__(index, time_str, ms, "Intention")
        self.agent_name = agent
        self.intention = intention
        self.trigger = trigger
        self.cycle = cycle

class EnvironmentLog(BaseLog):
    __slots__ = ('env_name', 'type', 'content', 'agent_action')
    def __init__(self, index, time_str, ms, env, log_type, content, action):
        super().__init__(index, time_str, ms, "Environment")
        self.env_name = env
        self.type = log_type
        self.content = content
        self.agent_action = action

class LogStore(QObject):
    store_updated = pyqtSignal()
    environment_state_updated = pyqtSignal(dict)
    agent_list_updated = pyqtSignal(list)
    environment_history_updated = pyqtSignal(str, object)
    participants_updated = pyqtSignal(list)

    def __init__(self, new_queue):
        super().__init__()
        self.new_queue = new_queue

        self.all_logs_timeline = []     
        self.timeline_ms_map = []       
        
        self.message_logs = []
        self.msg_timestamps = []        
        
        self.intention_logs = []
        self.int_timestamps = []        
        
        self.logs_by_agent = defaultdict(list)
        
        self.environment_states = {}
        self.environment_history = defaultdict(list)
        self.env_history_timestamps = defaultdict(list)
        
        self.environment_states_history = defaultdict(list)
        self.env_states_timestamps = defaultdict(list)
        
        self.known_agents = set()
        self.agent_last_intention_tracker = {}
        
        self.total_duration_ms = 0 
        self.current_timeline_ms = 0
        
        self.current_timeline_index = 0
        
        self.is_live = True
        self.emitted_agent_list = False 

        self.processing_timer = QTimer(self)
        self.processing_timer.setInterval(16) 
        self.processing_timer.timeout.connect(self._read_and_process_queue)
        
        self.ui_notify_timer = QTimer(self)
        self.ui_notify_timer.setInterval(500) 
        self.ui_notify_timer.timeout.connect(self._notify_ui)
        
        self.has_new_data = False

    def start_polling(self):
        self.processing_timer.start()
        self.ui_notify_timer.start()
    
    def _read_and_process_queue(self):
        try:
            packets_limit = 5000 
            count = 0
            while count < packets_limit:
                try:
                    log_bundle = self.new_queue.get_nowait()
                    for json_string in log_bundle:
                        try:
                            data = json.loads(json_string)
                            self._process_log_entry(data)
                            self.has_new_data = True
                        except (json.JSONDecodeError, TypeError):
                            pass
                    count += 1
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Erro LogStore: {e}")

    def _time_to_ms(self, time_str):
        if not time_str: return 0
        try:
            h, m, s_full = time_str.split(':')
            s, ms = s_full.split('.')
            return (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)
        except:
            return self.total_duration_ms

    def _process_log_entry(self, data):
        log_index = len(self.all_logs_timeline)
        sys_time = data.get("system_time", "00:00:00.000")
        ms = self._time_to_ms(sys_time)
        class_name = data.get("class_name")
        
        if ms > self.total_duration_ms:
            self.total_duration_ms = ms
            if self.is_live:
                self.current_timeline_ms = ms
                self.current_timeline_index = len(self.timeline_ms_map) 
                
        self.timeline_ms_map.append(ms)
        log_obj = None

        if class_name == "Agent":
            name = data.get("my_name")
            log_obj = AgentLog(log_index, sys_time, ms, name, data)
            
            self.logs_by_agent[name].append(log_obj)
            
            if name not in self.known_agents:
                self.known_agents.add(name)
                self.emitted_agent_list = False
            
            curr = log_obj.last_intention
            if curr and curr != 'null':
                prev = self.agent_last_intention_tracker.get(name)
                if curr != prev:
                    trig = log_obj.last_event.replace('gain:', '').replace('lose:', '')
                    int_log = IntentionLog(log_index, sys_time, ms, name, curr, trig, log_obj.cycle)
                    
                    self.intention_logs.append(int_log)
                    self.int_timestamps.append(ms) 
                    
                    self.agent_last_intention_tracker[name] = curr

        elif class_name == "Channel":
            desc = data.get("desc", "")
            if "sending" in desc:
                match = re.search(r"(\w+)\s+sending\s+([^:]+):\s*(.*)\s+to\s+([\w\s,\[\]']+)", desc)
                if match:
                    s, p, c, r = match.groups()
                    s_logs = self.logs_by_agent.get(s)
                    act = s_logs[-1].action if s_logs else "Desconhecido"
                    
                    log_obj = MessageLog(log_index, sys_time, ms, s, r.strip(), p.strip(), c.strip(), act)
                    self.message_logs.append(log_obj)
                    self.msg_timestamps.append(ms)
            
            if not log_obj:
                log_obj = BaseLog(log_index, sys_time, ms, "Channel")

        elif class_name == "Environment":
            env_name = data.get("my_name")
            desc = data.get("desc", "")
            
            if desc.startswith(("Creating", "Deleting", "Changing")):
                action = f"{data.get('action')} ({data.get('agent')})"
                p_new = data.get('new_percept') or data.get('percept(s)')
                content = str(p_new)
                if "Changing" in desc:
                    content = f"{str(data.get('old_percept'))} -> {content}"

                first_word = desc.split()[0]
                if "Creating" in first_word:
                    l_type = "create"
                elif "Deleting" in first_word:
                    l_type = "delete"
                elif "Changing" in first_word:
                    l_type = "change"
                else:
                    l_type = first_word.lower()

                log_obj = EnvironmentLog(log_index, sys_time, ms, env_name, l_type, content, action)
                
                self.environment_history[env_name].append(log_obj)
                self.env_history_timestamps[env_name].append(ms)
                
                if self.is_live:
                    self.environment_history_updated.emit(env_name, log_obj)
            
            percepts = data.get("percepts")
            if percepts:
                clean = {k: str(v) for k, v in (percepts[0] if isinstance(percepts, list) else percepts).items()}
                state_snapshot = {
                    'percepts': clean,
                    'connected_agents': data.get('connected_agents', [])
                }
                self.environment_states[env_name] = state_snapshot
                
                self.environment_states_history[env_name].append(state_snapshot)
                self.env_states_timestamps[env_name].append(ms)
                
                if self.is_live:
                     self.environment_state_updated.emit(self.environment_states)

            if not log_obj:
                log_obj = BaseLog(log_index, sys_time, ms, "Environment")

        else:
            log_obj = BaseLog(log_index, sys_time, ms, class_name or "Unknown")

        self.all_logs_timeline.append(log_obj)
        
        if self.is_live:
            self.current_timeline_index = len(self.timeline_ms_map) - 1

    def _get_slice_index(self, timestamp_list, target_ms):
        if not timestamp_list: return 0
        return bisect.bisect_right(timestamp_list, target_ms)

    def get_messages_reference(self):
        return self.message_logs

    def get_message_count_limit(self):
        if self.is_live: return len(self.message_logs)
        return self._get_slice_index(self.msg_timestamps, self.current_timeline_ms)

    def get_all_messages(self):
        if self.is_live: return self.message_logs
        cut_idx = self._get_slice_index(self.msg_timestamps, self.current_timeline_ms)
        return self.message_logs[:cut_idx]

    def get_all_intentions_history(self):
        if self.is_live: return self.intention_logs
        cut_idx = self._get_slice_index(self.int_timestamps, self.current_timeline_ms)
        return self.intention_logs[:cut_idx]

    def get_logs_for_agent(self, agent_name):
        logs = self.logs_by_agent.get(agent_name, [])
        if not logs: return []
        if self.is_live: return logs
        
        lo, hi = 0, len(logs)
        target = self.current_timeline_ms
        while lo < hi:
            mid = (lo + hi) // 2
            if logs[mid].time_ms <= target:
                lo = mid + 1
            else:
                hi = mid
        return logs[:lo]
    
    def get_latest_agent_state_before_index(self, agent_name, log_index):
        logs = self.logs_by_agent.get(agent_name, [])
        if not logs: return {}
        return logs[-1] 

    def get_environment_states_at_index(self, index):
        if self.is_live or index >= len(self.all_logs_timeline) - 10:
            return self.environment_states

        result = {}
        target_ms = self.current_timeline_ms
        
        for env_name in self.environment_states_history.keys():
            timestamps = self.env_states_timestamps.get(env_name, [])
            states = self.environment_states_history.get(env_name, [])
            
            if not timestamps or not states:
                continue
            
            idx = bisect.bisect_right(timestamps, target_ms)
            if idx > 0:
                result[env_name] = states[idx - 1]
        
        return result
    
    def get_latest_environment_states(self):
        return self.environment_states

    def get_environment_change_history(self, env_name):
        hist = self.environment_history.get(env_name, [])
        if self.is_live: return hist
        
        ts_list = self.env_history_timestamps.get(env_name, [])
        cut_idx = self._get_slice_index(ts_list, self.current_timeline_ms)
        return hist[:cut_idx]

    def _notify_ui(self):
        if self.has_new_data and self.is_live:
            self.has_new_data = False
            self.store_updated.emit()
            if not self.emitted_agent_list and self.known_agents:
                self._emit_agent_list()

    def _emit_agent_list(self):
        if not self.known_agents:
            return
        
        filtered_agents = []
        for agent_name in self.known_agents:
            if f"{agent_name}_1" in self.known_agents:
                continue
            filtered_agents.append(agent_name)
            
        sorted_agents = sorted(filtered_agents)
        self.agent_list_updated.emit(sorted_agents)
        self.emitted_agent_list = True

    @pyqtSlot(int)
    def set_current_timeline_index(self, index):
        if 0 <= index < len(self.timeline_ms_map):
            self.current_timeline_ms = self.timeline_ms_map[index]
            self.current_timeline_index = index 
        else:
            self.current_timeline_ms = self.total_duration_ms
            self.current_timeline_index = len(self.timeline_ms_map) - 1 if self.timeline_ms_map else 0

        total = len(self.all_logs_timeline)
        self.is_live = (index >= total - 10)
        self.store_updated.emit()

    @pyqtSlot()
    def toggle_live_mode(self):
        self.is_live = not self.is_live
        if self.is_live:
            self.current_timeline_ms = self.total_duration_ms
            self.current_timeline_index = len(self.timeline_ms_map) - 1 if self.timeline_ms_map else 0
            self.store_updated.emit()

    def get_total_duration_ms(self):
        return self.total_duration_ms

    def get_index_from_ms(self, ms_value):
        if not self.timeline_ms_map: return 0
        idx = bisect.bisect_left(self.timeline_ms_map, ms_value)
        return min(idx, len(self.timeline_ms_map) - 1)
from PyQt5.QtCore import QObject, pyqtSignal

class AgentDataModel(QObject):
    agent_data_updated = pyqtSignal(str)

    def __init__(self, log_store, parent=None):
        super().__init__(parent)
        self.log_store = log_store
        
        self.log_store.store_updated.connect(self.on_store_updated)

        self.observed_agents = set()

    def on_store_updated(self):
        for agent_name in self.observed_agents:
            self.agent_data_updated.emit(agent_name)

    def get_agent_log_history(self, agent_name):
        if agent_name not in self.observed_agents:
            self.observed_agents.add(agent_name)
            
        return self.log_store.get_logs_for_agent(agent_name)

    def get_latest_agent_state(self, agent_name):
        logs = self.log_store.get_logs_for_agent(agent_name)
        if logs:
            return logs[-1]
        return {}

    def stop_observing_agent(self, agent_name):
        if agent_name in self.observed_agents:
            self.observed_agents.remove(agent_name)
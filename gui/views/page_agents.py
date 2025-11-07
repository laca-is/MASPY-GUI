import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QScrollArea, QLineEdit, QLabel, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from gui.widgets.agent_card import AgentCard 
from gui.widgets.agent_detail_window import AgentDetailWindow
from gui.assets.theme.theme_dark import theme_colors

class AgentesPage(QWidget):
    def __init__(self, log_store, data_model):
        super().__init__()
        self.setProperty("class", "page")
        self.data_model = data_model
        self.log_store = log_store
        self.agent_queue = []
        self.agent_cards = {}
        self.open_windows = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        search_and_status_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar agente por nome...")
        self.search_input.setFixedHeight(40)

        self.search_input.textChanged.connect(self.on_search_changed)
        search_and_status_layout.addWidget(self.search_input)

        self.status_label = QLabel("Carregando agentes...")
        self.status_label.hide()
        search_and_status_layout.addWidget(self.status_label)
        search_and_status_layout.addStretch()

        self.layout.addLayout(search_and_status_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.container_widget = QWidget()
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.container_widget.setLayout(self.grid_layout)
        self.grid_layout.setContentsMargins(0, 5, 0, 5) 
        
        self.scroll_area.setWidget(self.container_widget)
        self.layout.addWidget(self.scroll_area)

        
    def on_agent_list_updated(self, agents):
        self._clear_grid()
        self.agent_cards.clear()
        if not agents:
            self.status_label.setText("Aguardando agentes do sistema...")
            self.status_label.show()
            return
        self.agent_queue = sorted(agents)
        self.status_label.setText(f"Carregando {len(self.agent_queue)} agentes...")
        self.status_label.show()
        QTimer.singleShot(50, self.process_agent_batch)

    def process_agent_batch(self):
        batch_size = 20
        processed_count = 0
        while self.agent_queue and processed_count < batch_size:
            agent_name = self.agent_queue.pop(0)
            self._add_agent_card(agent_name)
            processed_count += 1
        if self.agent_queue:
            remaining = len(self.agent_queue)
            total = len(self.agent_cards) + remaining
            self.status_label.setText(f"Carregando... {total-remaining}/{total}")
            QTimer.singleShot(10, self.process_agent_batch)
        else:
            self.status_label.setText(f"{len(self.agent_cards)} agentes carregados.")
            QTimer.singleShot(3000, self.status_label.hide)
            self.on_search_changed()

    def _add_agent_card(self, agent_name):
        if agent_name in self.agent_cards:
            return
        agent_card = AgentCard(agent_name)
        agent_card.details_button.clicked.connect(
            lambda checked, name=agent_name: self.on_agent_clicked(name)
        )
        self.agent_cards[agent_name] = agent_card
        
        latest_state = self.data_model.get_latest_agent_state(agent_name)
        if latest_state:
            self._update_card_from_log(agent_card, latest_state)
            
        cols = 3
        total_items = len(self.agent_cards) - 1
        row = total_items // cols
        col = total_items % cols
        self.grid_layout.addWidget(agent_card, row, col)

    def on_search_changed(self):
        search_text = self.search_input.text().strip().lower()
        for name, card in self.agent_cards.items():
            card.setVisible(search_text in name.lower())

    def _clear_grid(self):
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def on_store_updated(self):
        search_text = self.search_input.text().strip().lower()
        
        for agent_name, card in self.agent_cards.items():
            is_visible = card.isVisible()
            matches_search = search_text and search_text in agent_name.lower()
            
            if is_visible or matches_search:
                latest_state = self.data_model.get_latest_agent_state(agent_name)
                if latest_state:
                    self._update_card_from_log(card, latest_state)

    def _update_card_from_log(self, card, log_data):
        num_beliefs = len(log_data.get('beliefs', []))
        num_goals = len(log_data.get('goals', []))
        card.beliefs_label.setText(f"Crenças: {num_beliefs}")
        card.goals_label.setText(f"Objetivos: {num_goals}")

        card.update_cycle(log_data.get('cycle', 0))

        action_str = self._extract_action_from_log(log_data)
        card.update_action(action_str)

    def _extract_action_from_log(self, log_data):
        desc = log_data.get("desc", "")

        if desc:
            match = re.search(r"doing action \*(\w+)", desc)
            if match:
                return f"Executando: {match.group(1)}"

            match = re.search(r"action:\s*\*(\w+)", desc)
            if match:
                return f"Executando: {match.group(1)}"
        
        running_intentions = log_data.get("running_intentions", [])
        if not running_intentions:
            return "Ocioso"
        try:
            main_intention_str = running_intentions[0]
            
            match = re.search(r"->\s*([\w\d_]+)\(.*\)\s*Context=", main_intention_str)
            if match: 
                return f"Plano: {match.group(1)}"
            
            match = re.search(r"\]\s*,\s*([\w\d_]+)\(.*\)", main_intention_str)
            if match: 
                return f"Plano: {match.group(1)}"
                
        except (IndexError, TypeError):
            pass
        
        return "Executando Intenção"

    def on_agent_clicked(self, agent_name):
        try:
            if agent_name in self.open_windows and self.open_windows[agent_name].isVisible():
                self.open_windows[agent_name].activateWindow()
                return
        except RuntimeError:
            pass
            
        detail_window = AgentDetailWindow(agent_name, self.data_model)
        
        detail_window.destroyed.connect(
            lambda: self.on_detail_window_closed(agent_name)
        )
        
        self.open_windows[agent_name] = detail_window
        detail_window.show()

    def on_detail_window_closed(self, agent_name):
        self.data_model.stop_observing_agent(agent_name)
        if agent_name in self.open_windows:
            del self.open_windows[agent_name]

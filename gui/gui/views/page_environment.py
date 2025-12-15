import copy
import re 
import ast 
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QScrollArea, QFrame, QTreeWidget, QTreeWidgetItem, 
                             QHeaderView, QTextEdit, QPushButton, QButtonGroup,
                             QListWidget, QListWidgetItem, QSizePolicy)
from PyQt5.QtCore import Qt
from gui.assets.theme.styler import current_theme

class AmbientePage(QWidget):
    def __init__(self, log_store):
        super().__init__()
        self.setProperty("class", "page")
        self.log_store = log_store
        
        self.known_environments = set()
        self.selected_environment = None
        self.env_button_group = QButtonGroup(self)
        self.env_button_group.setExclusive(True)

        self._setup_ui()

        self.log_store.environment_state_updated.connect(self.on_environment_state_updated)
        self.log_store.environment_history_updated.connect(self.on_environment_history_updated)
        self.log_store.store_updated.connect(self.check_timeline_update)

        self.on_environment_state_updated(self.log_store.get_environment_states_at_index(0))

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        left_column = QFrame()
        left_column.setFrameShape(QFrame.StyledPanel)
        left_column.setProperty("class", "card")
        left_column.setMaximumWidth(250)
        left_layout = QVBoxLayout(left_column)

        left_title = QLabel("Environments")
        left_title.setProperty("class", "h2")
        left_layout.addWidget(left_title)
        
        self.env_scroll_area = QScrollArea()
        self.env_scroll_area.setWidgetResizable(True)
        
        self.env_list_widget = QWidget()
        self.env_list_layout = QVBoxLayout(self.env_list_widget)
        self.env_list_layout.setAlignment(Qt.AlignTop)
        self.env_list_layout.setSpacing(4)
        self.env_scroll_area.setWidget(self.env_list_widget)
        
        left_layout.addWidget(self.env_scroll_area)
        main_layout.addWidget(left_column)

        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.details_container, stretch=1)

        self._show_placeholder()

    def update_theme(self):
        if self.selected_environment:
            self.rebuild_history_log()

    def _show_placeholder(self):
        self._clear_layout(self.details_layout)
        placeholder = QLabel("Select an environment to view details")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setProperty("class", "text-secondary")
        self.details_layout.addWidget(placeholder)

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def _build_details_ui(self, env_name):
        self._clear_layout(self.details_layout)
        
        title = QLabel(f"Monitoring: {env_name}")
        title.setProperty("class", "h1")
        self.details_layout.addWidget(title)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        agents_frame = QFrame()
        agents_frame.setProperty("class", "card")
        agents_layout = QVBoxLayout(agents_frame)
        agents_title = QLabel("Conected Agents")
        agents_title.setProperty("class", "h2")
        self.agents_list = QListWidget()
        agents_layout.addWidget(agents_title)
        agents_layout.addWidget(self.agents_list)
        top_layout.addWidget(agents_frame, stretch=1)

        state_frame = QFrame()
        state_frame.setProperty("class", "card")
        state_layout = QVBoxLayout(state_frame)
        state_title = QLabel("Percepts")
        state_title.setProperty("class", "h2")
        self.state_list = QListWidget()
        state_layout.addWidget(state_title)
        state_layout.addWidget(self.state_list)
        top_layout.addWidget(state_frame, stretch=2)

        self.details_layout.addLayout(top_layout)

        history_frame = QFrame()
        history_frame.setProperty("class", "card")
        history_layout = QVBoxLayout(history_frame)
        history_title = QLabel("Changes History")
        history_title.setProperty("class", "h2")
        
        self.history_log = QTextEdit()
        self.history_log.setReadOnly(True)
        self.history_log.setMinimumHeight(200)
        self.history_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        history_layout.addWidget(history_title)
        history_layout.addWidget(self.history_log)
        
        self.details_layout.addWidget(history_frame)
        self.details_layout.setStretchFactor(history_frame, 1)

    def _add_environment_button(self, env_name):
        button = QPushButton(env_name)
        button.setObjectName("FilterButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked, n=env_name: self.on_environment_selected(n))
        self.env_button_group.addButton(button)
        
        for i in range(self.env_list_layout.count()):
            widget = self.env_list_layout.itemAt(i).widget()
            if widget and widget.text() > env_name:
                self.env_list_layout.insertWidget(i, button)
                return
        self.env_list_layout.addWidget(button)

    def on_environment_selected(self, env_name):
        if self.selected_environment == env_name:
            return
            
        self.selected_environment = env_name
        self._build_details_ui(env_name)

        idx = self.log_store.current_timeline_index
        all_states = self.log_store.get_environment_states_at_index(idx)
        
        self.on_environment_state_updated(all_states)
        self.rebuild_history_log()

    def check_timeline_update(self):
        if self.isVisible() and self.selected_environment:
            self.on_timeline_state_changed(self.log_store.current_timeline_index)

    def on_environment_state_updated(self, all_envs_data):
        if not all_envs_data:
            return

        for env_name in all_envs_data.keys():
            if env_name not in self.known_environments:
                self.known_environments.add(env_name)
                self._add_environment_button(env_name)

        if self.selected_environment and self.selected_environment in all_envs_data:
            data = all_envs_data[self.selected_environment]

            self.agents_list.clear()
            agents = data.get('connected_agents', [])
            if not agents:
                self.agents_list.addItem(QListWidgetItem("No agents are connected."))
            else:
                self.agents_list.addItems(sorted(agents))

            self.state_list.clear()
            percepts = data.get('percepts', {})
            if not percepts:
                self.state_list.addItem(QListWidgetItem("No Percepts in the Environment"))
            else:
                for key, value in sorted(percepts.items()):
                    self.state_list.addItem(QListWidgetItem(f"{key}: {value}"))

    def on_environment_history_updated(self, env_name, history_entry):
        if env_name == self.selected_environment and self.log_store.is_live:
            self._format_and_add_history_entry(history_entry)
            sb = self.history_log.verticalScrollBar()
            sb.setValue(sb.maximum())

    def rebuild_history_log(self):
        if not self.selected_environment:
            return
            
        self.history_log.clear()
        history_list = self.log_store.get_environment_change_history(self.selected_environment)

        for entry in history_list:
            self._format_and_add_history_entry(entry)

    def _format_and_add_history_entry(self, entry):
        raw_type = getattr(entry, 'type', 'unknown') or 'unknown'
        content = str(getattr(entry, 'content', 'N/A')).replace('<', '&lt;').replace('>', '&gt;')
        action = str(getattr(entry, 'agent_action', 'N/A'))
        time = getattr(entry, 'system_time', 'N/A')

        log_type_key = raw_type.lower()

        color_map = {
            'create': current_theme.get('success', '#10B981'),
            'delete': current_theme.get('danger', '#EF4444'),
            'change': current_theme.get('warning', '#F59E0B'),
            'update': current_theme.get('info', '#3B82F6')
        }
        
        type_map = {
            'create': '[CREATE]',
            'delete': '[DELETE]',
            'change': '[CHANGE]',
            'update': '[UPDATE]'
        }

        color = color_map.get(log_type_key, current_theme.get('text_primary', '#FFFFFF'))
        type_str = type_map.get(log_type_key, f'[{raw_type.upper()}]')

        text_sec_color = current_theme.get('text_secondary', '#9CA3AF')
        text_pri_color = current_theme.get('text_primary', '#FFFFFF')

        html = (
            f'<span style="color:{text_sec_color};">[{time}]</span> '
            f'<span style="color:{color}; font-weight:bold;">{type_str}</span> '
            f'<span style="color:{text_pri_color};">{content}</span> '
            f'<span style="color:{text_sec_color}; font-style:italic;"> (Action: {action})</span>'
        )
        self.history_log.append(html)

    def on_timeline_state_changed(self, index):
        states_at_index = self.log_store.get_environment_states_at_index(index)
        self.on_environment_state_updated(states_at_index)
        
        if self.selected_environment:
            self.rebuild_history_log()
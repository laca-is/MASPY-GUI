import re
import ast
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame,
    QHBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView, 
    QListWidget, QListWidgetItem, QTabWidget, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from gui.assets.theme.theme_dark import theme_colors


class AgentDetailWindow(QWidget):
    def __init__(self, agent_name, data_model, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.data_model = data_model
        self.setObjectName("AgentDetailWindow")
        
        self.setWindowTitle(f"Detalhes do Agente: {self.agent_name}")
        self.setGeometry(150, 150, 900, 750) 
        
        self.setAttribute(Qt.WA_DeleteOnClose) 

        main_layout = QVBoxLayout(self)
        title = QLabel(f"Monitorando: {self.agent_name}")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        tab_widget.addTab(self._create_overview_tab(), "Visão Geral")
        tab_widget.addTab(self._create_mind_tab(), "Mente do Agente")
        tab_widget.addTab(self._create_perception_tab(), "Ambiente e Canais")
        
        self.data_model.agent_data_updated.connect(self.on_agent_data_updated)
        
        self.load_and_rebuild_data()

    def _create_section_title(self, text):
        title = QLabel(text)
        title.setProperty("class", "h2")
        return title
        
    def _create_frame(self):
        frame = QFrame()
        frame.setProperty("class", "card")
        return frame

    def _create_key_value_display(self, parent_layout, key_text):
        layout = QHBoxLayout()
        key_label = QLabel(f"<b>{key_text}</b>")
        key_label.setProperty("class", "detail-key")
        
        value_label = QLabel("<i>N/A</i>")
        value_label.setWordWrap(True)
        value_label.setProperty("class", "detail-value")
        value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        value_label.setMinimumWidth(100)
        
        layout.addWidget(key_label)
        layout.addStretch()
        layout.addWidget(value_label)
        parent_layout.addLayout(layout)
        return value_label

    def _create_list_display(self, min_height=120):
        list_widget = QListWidget()
        list_widget.setMinimumHeight(min_height)
        return list_widget

    def _create_log_display(self, min_height=150):
        log = QTextEdit()
        log.setReadOnly(True)
        log.setMinimumHeight(min_height)
        return log
        
    def _create_tree_display(self, headers):
        tree = QTreeWidget()
        tree.setHeaderLabels(headers)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        return tree
    
    def _create_overview_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab) 
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        left_col_layout = QVBoxLayout()
        left_col_layout.addWidget(self._create_section_title("Status em Tempo Real"))
        rt_frame = self._create_frame()
        rt_layout = QVBoxLayout(rt_frame)
        self.cycle_display = self._create_key_value_display(rt_layout, "Ciclo Atual:")
        self.action_display = self._create_key_value_display(rt_layout, "Ação Atual:")
        self.curr_event_display = self._create_key_value_display(rt_layout, "Processando Evento:")
        self.num_intentions_display = self._create_key_value_display(rt_layout, "Num. Intenções:")
        left_col_layout.addWidget(rt_frame)
        
        left_col_layout.addWidget(self._create_section_title("Intenções Ativas (running_intentions)"))
        self.running_intentions_list = self._create_list_display(min_height=150)
        left_col_layout.addWidget(self.running_intentions_list)
        left_col_layout.addStretch()
        layout.addLayout(left_col_layout)

        right_col_layout = QVBoxLayout()
        right_col_layout.addWidget(self._create_section_title("Crenças Atuais (Beliefs)"))
        self.current_beliefs_list = self._create_list_display()
        right_col_layout.addWidget(self.current_beliefs_list)
        
        right_col_layout.addWidget(self._create_section_title("Objetivos Atuais (Goals)"))
        self.current_goals_list = self._create_list_display()
        right_col_layout.addWidget(self.current_goals_list)
        right_col_layout.addStretch()
        layout.addLayout(right_col_layout)

        return tab

    def _create_mind_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab) 
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        belief_history_layout = QVBoxLayout()
        belief_history_layout.addWidget(self._create_section_title("Histórico de Crenças"))
        self.belief_history_log = self._create_log_display()
        belief_history_layout.addWidget(self.belief_history_log)
        top_layout.addLayout(belief_history_layout)

        goal_history_layout = QVBoxLayout()
        goal_history_layout.addWidget(self._create_section_title("Histórico de Objetivos"))
        self.goal_history_log = self._create_log_display()
        goal_history_layout.addWidget(self.goal_history_log)
        top_layout.addLayout(goal_history_layout)
        
        main_layout.addLayout(top_layout, stretch=1) 

        intention_history_layout = QVBoxLayout()
        intention_history_layout.addWidget(self._create_section_title("Histórico de Intenções"))
        self.intention_history_log = self._create_log_display()
        intention_history_layout.addWidget(self.intention_history_log)
        
        main_layout.addLayout(intention_history_layout, stretch=1) 

        return tab

    def _create_perception_tab(self):
        tab = QWidget()
        
        main_layout = QHBoxLayout(tab) 
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        percept_frame = self._create_frame()
        percept_layout = QVBoxLayout(percept_frame)
        percept_layout.addWidget(self._create_section_title("Percepções Atuais (Perceptions)"))
        self.perceptions_tree = self._create_tree_display(['Chave', 'Valor'])
        self.perceptions_tree.setMinimumHeight(200)
        percept_layout.addWidget(self.perceptions_tree)
        main_layout.addWidget(percept_frame, stretch=2) 

        lists_frame = self._create_frame()
        lists_layout = QVBoxLayout(lists_frame)
        
        lists_layout.addWidget(self._create_section_title("Ambientes (Envs)"))
        self.envs_list = self._create_list_display(min_height=80)
        lists_layout.addWidget(self.envs_list)
        
        lists_layout.addWidget(self._create_section_title("Canais (Chs)"))
        self.chs_list = self._create_list_display(min_height=80)
        lists_layout.addWidget(self.chs_list)
        
        lists_layout.addStretch()
        main_layout.addWidget(lists_frame, stretch=1) 
        
        return tab

    def on_agent_data_updated(self, updated_agent_name):
        if updated_agent_name == self.agent_name:
            self.load_and_rebuild_data()

    def load_and_rebuild_data(self):
        log_history = self.data_model.get_agent_log_history(self.agent_name)
        if not log_history:
            return
        
        latest_state = log_history[-1]

        self.cycle_display.setText(str(latest_state.get('cycle', 'N/A')))
        self.curr_event_display.setText(str(latest_state.get('curr_event', 'N/A')))
        running_intentions = latest_state.get('running_intentions', [])
        self.num_intentions_display.setText(str(len(running_intentions)))
        action_str = self._extract_action_from_log(latest_state)
        self.action_display.setText(action_str)
        self._update_list_widget(self.running_intentions_list, running_intentions)
        self._update_list_widget(self.current_beliefs_list, latest_state.get('beliefs', []))
        self._update_list_widget(self.current_goals_list, latest_state.get('goals', []))
        
        self._populate_tree(self.perceptions_tree, latest_state.get('perceptions', {}))
        self._update_list_widget(self.envs_list, latest_state.get('envs', []))
        self._update_list_widget(self.chs_list, latest_state.get('chs', [])) 

        self.belief_history_log.clear()
        self.goal_history_log.clear()
        self.intention_history_log.clear()

        last_intention_in_history = None
        previous_beliefs = set()
        previous_goals = set()

        for log in log_history:
            timestamp = log.get('system_time', 'N/A') 

            current_beliefs = set(log.get('beliefs', []))
            gained_beliefs = current_beliefs - previous_beliefs
            lost_beliefs = previous_beliefs - current_beliefs

            for belief_str in gained_beliefs:
                self._add_log_entry(self.belief_history_log, 'gain', {'raw': belief_str}, timestamp)
            for belief_str in lost_beliefs:
                self._add_log_entry(self.belief_history_log, 'lose', {'raw': belief_str}, timestamp)
            
            previous_beliefs = current_beliefs

            current_goals = set(log.get('goals', []))
            gained_goals = current_goals - previous_goals
            lost_goals = previous_goals - current_goals

            for goal_str in gained_goals:
                self._add_log_entry(self.goal_history_log, 'gain', {'raw': goal_str}, timestamp)
            for goal_str in lost_goals:
                self._add_log_entry(self.goal_history_log, 'lose', {'raw': goal_str}, timestamp)

            previous_goals = current_goals

            current_last_intention = log.get('last_intention')
            
            if (current_last_intention and 
                current_last_intention != 'null' and 
                current_last_intention != last_intention_in_history):
                
                event_str = log.get('last_event', 'Gatilho desconhecido')
                event_str = event_str.replace('gain:', '').replace('lose:', '')

                time_str = f'<span style="color:#888;">[{timestamp}]</span>'
                content_str = f"Gatilho: <b>{event_str}</b>  {current_last_intention}"
                
                self.intention_history_log.append(f'{time_str} <span style="color:{theme_colors["info"]};">{content_str}</span>')
                
                last_intention_in_history = current_last_intention

    def _add_log_entry(self, log_widget, status, data_dict, timestamp=""):
        status_map = {
            'gain': ('[GAIN]', theme_colors['success']),
            'lose': ('[LOSE]', theme_colors['danger']),
            'success': ('[SUCCESS]', theme_colors['success']), 
            'update': ('[UPDATE]', theme_colors['info']),
        }
        prefix, color = status_map.get(status, ('[EVENT]', theme_colors['text_primary']))
        content = data_dict.get('raw')
        if content is None:
            content = str(data_dict)
            
        time_str = f'<span style="color:#888;">[{timestamp}]</span>' if timestamp else ''
        log_widget.append(f'{time_str} <span style="color:{color}; font-weight:bold;">{prefix}</span> {content}')

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

    def _format_parsed_object_for_display(self, parsed_item):
        if not isinstance(parsed_item, dict):
            return str(parsed_item)
        if not parsed_item or parsed_item.get('type') == 'Unknown':
            return parsed_item.get('raw', str(parsed_item))
        
        tipo = parsed_item.get('type', '')
        predicate = parsed_item.get('predicate', '')
        args = parsed_item.get('args', [])
        source = parsed_item.get('source', '')
        args_str = ", ".join(map(str, args))
        return f"{tipo}: {predicate}({args_str}) [{source}]"

    def _parse_intention_list_for_display(self, intention_str):
        if not isinstance(intention_str, str):
            return str(intention_str)
        
        try:
            goal_match = re.search(r"^(gain:Goal.*?\[.*?\])", intention_str)
            plan_match = re.search(r"->\s*([\w\d_]+)\(.*\)", intention_str)
            
            goal_str = goal_match.group(1) if goal_match else "Objetivo complexo"
            plan_name = plan_match.group(1) if plan_match else "Plano complexo"
            
            return f"Plano: {plan_name} | Objetivo: {goal_str}"
        except Exception:
            return intention_str 
            
    def _update_list_widget(self, list_widget, items_list):
        list_widget.clear()
        if not items_list:
            item = QListWidgetItem("Nenhum item.")
            item.setForeground(QColor("#888"))
            list_widget.addItem(item)
        else:
            for item_data in items_list:
                display_text = ""
                if list_widget == self.running_intentions_list:
                    display_text = self._parse_intention_list_for_display(item_data)
                elif isinstance(item_data, dict):
                    display_text = self._format_parsed_object_for_display(item_data)
                else:
                    display_text = str(item_data)
                list_widget.addItem(QListWidgetItem(display_text))

    def _safe_eval(self, literal):
        try:
            return ast.literal_eval(literal)
        except (ValueError, SyntaxError):
            return literal

    def _populate_tree(self, tree, data, parent_item=None):
        if parent_item is None:
            tree.clear()
            parent_item = tree.invisibleRootItem()
        
        if isinstance(data, str):
            data = self._safe_eval(data)

        if isinstance(data, dict):
            for key, val in sorted(data.items()):
                key_str = str(self._safe_eval(key))
                child = QTreeWidgetItem([key_str])
                parent_item.addChild(child)
                self._populate_tree(tree, val, child)
        elif isinstance(data, (list, set, tuple)):
            for i, val in enumerate(data):
                child = QTreeWidgetItem([f"Item {i}"])
                parent_item.addChild(child)
                self._populate_tree(tree, val, child)
        else:
            if parent_item.childCount() == 0 and parent_item.text(0) != "root":
                parent_item.setText(1, str(data))
            else:
                pass
        
        tree.expandAll()
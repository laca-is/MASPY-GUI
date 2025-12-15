import re
import ast
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QHBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView, 
    QListWidget, QListWidgetItem, QTabWidget, QSizePolicy,
    QListView, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from gui.assets.theme.styler import current_theme

from gui.core.history_model import HistoryLogModel, HistoryLogDelegate, HistoryItem

class AgentDetailWindow(QWidget):
    def __init__(self, agent_name, data_model, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.data_model = data_model
        self.setObjectName("AgentDetailWindow")
        
        self.setWindowTitle(f"Agent's Details: {self.agent_name}")
        self.setGeometry(150, 150, 900, 750) 
        self.setAttribute(Qt.WA_DeleteOnClose) 

        self.last_log_index = 0
        self.last_intention_in_history = None
        self.regex_change = re.compile(r"(Adding|Removing) Info: (Belief|Goal) (.*?)\s+-\s+instant\[.*\]$")

        self.belief_items = []
        self.goal_items = []
        self.intention_items = []

        self.previous_beliefs_set = set()
        self.previous_goals_set = set()
        self.active_beliefs = set()
        self.active_goals = set()
        self.successful_goals = set()
        self.changes_this_cycle = set()

        self.belief_model = HistoryLogModel()
        self.goal_model = HistoryLogModel()
        self.intention_model = HistoryLogModel()

        main_layout = QVBoxLayout(self)
        title = QLabel(f"Monitoring: {self.agent_name}")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        tab_widget.addTab(self._create_overview_tab(), "Overview")
        tab_widget.addTab(self._create_mind_tab(), "Agent's mind")
        tab_widget.addTab(self._create_perception_tab(), "Environment and Channels")
        
        self.data_model.agent_data_updated.connect(self.on_agent_data_updated)

        self.update_data()

    def update_theme(self):
        for view in [self.belief_view, self.goal_view, self.intention_view]:
            delegate = view.itemDelegate()
            if hasattr(delegate, 'update_theme_colors'):
                delegate.update_theme_colors()
            view.viewport().update()

        self.perceptions_tree.viewport().update()
        
        self.repaint()

    def on_agent_data_updated(self, updated_agent_name):
        if updated_agent_name == self.agent_name:
            self.update_data()

    def update_data(self):
        full_history = self.data_model.get_agent_log_history(self.agent_name)
        if not full_history: return
        
        latest_state = full_history[-1]
        self._update_snapshots(latest_state)

        total_logs = len(full_history)
        if total_logs == self.last_log_index: return

        new_logs = full_history[self.last_log_index:]
        self.last_log_index = total_logs
        self._process_new_logs_to_models(new_logs, full_history)

    def _normalize_belief_or_goal(self, item):
        if isinstance(item, dict):
            tipo = item.get('type', '')
            predicate = item.get('predicate', '')
            args = item.get('args', [])
            source = item.get('source', '')
            args_str = ", ".join(map(str, args))
            return f"{tipo}: {predicate}({args_str}) [{source}]"
        return str(item)

    def _get_beliefs_set(self, log):
        beliefs = getattr(log, 'beliefs', []) or []
        return {self._normalize_belief_or_goal(b) for b in beliefs}

    def _get_goals_set(self, log):
        goals = getattr(log, 'goals', []) or []
        return {self._normalize_belief_or_goal(g) for g in goals}

    def _process_new_logs_to_models(self, new_logs, full_history):
        items_added = False
        
        for i, log in enumerate(new_logs):
            desc = log.desc
            timestamp = log.system_time
            cycle = log.cycle
            
            current_beliefs = self._get_beliefs_set(log)
            current_goals = self._get_goals_set(log)
            
            def record_change(item_type, msg_type, content):
                change_key = (cycle, item_type, msg_type, content)
                if change_key in self.changes_this_cycle:
                    return False
                self.changes_this_cycle.add(change_key)
                return True
            
            gained_beliefs = current_beliefs - self.previous_beliefs_set
            for belief_str in gained_beliefs:
                if belief_str not in self.active_beliefs:
                    if record_change('belief', 'GAIN', belief_str):
                        item = HistoryItem('GAIN', belief_str, timestamp, cycle)
                        self.belief_items.append(item)
                        self.active_beliefs.add(belief_str)
                        items_added = True
            
            lost_beliefs = self.previous_beliefs_set - current_beliefs
            for belief_str in lost_beliefs:
                if belief_str in self.active_beliefs:
                    if record_change('belief', 'LOSE', belief_str):
                        item = HistoryItem('LOSE', belief_str, timestamp, cycle)
                        self.belief_items.append(item)
                        self.active_beliefs.discard(belief_str)
                        items_added = True
            
            gained_goals = current_goals - self.previous_goals_set
            for goal_str in gained_goals:
                if goal_str not in self.active_goals:
                    if record_change('goal', 'GAIN', goal_str):
                        item = HistoryItem('GAIN', goal_str, timestamp, cycle)
                        self.goal_items.append(item)
                        self.active_goals.add(goal_str)
                        items_added = True
            
            lost_goals = self.previous_goals_set - current_goals
            for goal_str in lost_goals:
                if goal_str in self.active_goals:
                    if record_change('goal', 'LOSE', goal_str):
                        item = HistoryItem('LOSE', goal_str, timestamp, cycle)
                        self.goal_items.append(item)
                        self.active_goals.discard(goal_str)
                        items_added = True
            
            match = self.regex_change.match(desc)
            if not match:
                match = self.regex_change.search(desc)
            
            if match:
                action_type = match.group(1)
                item_type = match.group(2)
                content = match.group(3).strip()
                msg_type = 'GAIN' if action_type == "Adding" else 'LOSE'
                normalized_content = f"{item_type} {content}"
                
                if item_type == 'Belief':
                    if msg_type == 'GAIN' and normalized_content not in self.active_beliefs:
                        if record_change('belief', 'GAIN', normalized_content):
                            item = HistoryItem(msg_type, normalized_content, timestamp, cycle)
                            self.belief_items.append(item)
                            self.active_beliefs.add(normalized_content)
                            items_added = True
                    elif msg_type == 'LOSE' and normalized_content in self.active_beliefs:
                        if record_change('belief', 'LOSE', normalized_content):
                            item = HistoryItem(msg_type, normalized_content, timestamp, cycle)
                            self.belief_items.append(item)
                            self.active_beliefs.discard(normalized_content)
                            items_added = True
                elif item_type == 'Goal':
                    if msg_type == 'GAIN' and normalized_content not in self.active_goals:
                        if record_change('goal', 'GAIN', normalized_content):
                            item = HistoryItem(msg_type, normalized_content, timestamp, cycle)
                            self.goal_items.append(item)
                            self.active_goals.add(normalized_content)
                            items_added = True
                    elif msg_type == 'LOSE' and normalized_content in self.active_goals:
                        if record_change('goal', 'LOSE', normalized_content):
                            item = HistoryItem(msg_type, normalized_content, timestamp, cycle)
                            self.goal_items.append(item)
                            self.active_goals.discard(normalized_content)
                            items_added = True
            
            self.previous_beliefs_set = current_beliefs
            self.previous_goals_set = current_goals
            
            for evt in log.events:
                if "success:" in evt and "Goal" in evt:
                    content = evt.replace("success:", "")
                    if content not in self.successful_goals:
                        item = HistoryItem('SUCCESS', content, timestamp, cycle)
                        self.goal_items.append(item)
                        self.successful_goals.add(content)
                        items_added = True

            curr = log.last_intention
            if curr and curr != 'null' and curr != self.last_intention_in_history:
                event_str = log.last_event.replace('gain:', '').replace('lose:', '') if log.last_event else ''
                content_str = f"Trigger: {event_str} | {curr}"
                item = HistoryItem('INTENTION', content_str, timestamp, cycle)
                self.intention_items.append(item)
                self.last_intention_in_history = curr
                items_added = True

        if items_added:
            self.belief_model.set_items(self.belief_items)
            self.goal_model.set_items(self.goal_items)
            self.intention_model.set_items(self.intention_items)
            self._scroll_to_bottom(self.belief_view, self.belief_model)
            self._scroll_to_bottom(self.goal_view, self.goal_model)
            self._scroll_to_bottom(self.intention_view, self.intention_model)

    def _scroll_to_bottom(self, view, model):
        if model.rowCount() > 0:
            view.scrollTo(model.index(model.rowCount() - 1, 0), QAbstractItemView.EnsureVisible)

    def _update_snapshots(self, latest_state):
        self.cycle_display.setText(str(latest_state.cycle))
        self.curr_event_display.setText(str(latest_state.last_event))
        self.num_intentions_display.setText(str(len(latest_state.running_intentions)))
        self.action_display.setText(latest_state.action)
        self._update_list_widget(self.running_intentions_list, latest_state.running_intentions)
        self._update_list_widget(self.current_beliefs_list, latest_state.beliefs)
        self._update_list_widget(self.current_goals_list, latest_state.goals)
        self._populate_tree(self.perceptions_tree, latest_state.perceptions)
        self._update_list_widget(self.envs_list, latest_state.envs)
        self._update_list_widget(self.chs_list, latest_state.chs) 

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

    def _create_log_list_view(self, model, min_height=150):
        view = QListView()
        view.setModel(model)
        
        delegate = HistoryLogDelegate(view, current_theme)
        view.setItemDelegate(delegate)
        
        view.setStyleSheet("QListView { font-size: 13pt; font-family: Arial; }")
        view.setUniformItemSizes(True) 
        view.setAlternatingRowColors(False)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        view.setMinimumHeight(min_height)
        view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        return view
        
    def _create_tree_display(self, headers):
        tree = QTreeWidget()
        tree.setHeaderLabels(headers)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        if len(headers) > 1:
            tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tree.header().setStretchLastSection(False)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tree.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        return tree

    def _create_overview_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab) 
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        left_col_layout = QVBoxLayout()
        left_col_layout.addWidget(self._create_section_title("Real Time Status"))
        rt_frame = self._create_frame()
        rt_layout = QVBoxLayout(rt_frame)
        self.cycle_display = self._create_key_value_display(rt_layout, "Current Cycle:")
        self.action_display = self._create_key_value_display(rt_layout, "Current Action:")
        self.curr_event_display = self._create_key_value_display(rt_layout, "Processing Event:")
        self.num_intentions_display = self._create_key_value_display(rt_layout, "Num. Intentions:")
        left_col_layout.addWidget(rt_frame)
        
        left_col_layout.addWidget(self._create_section_title("Running Intentions"))
        self.running_intentions_list = self._create_list_display(min_height=150)
        left_col_layout.addWidget(self.running_intentions_list)
        left_col_layout.addStretch()
        layout.addLayout(left_col_layout)

        right_col_layout = QVBoxLayout()
        right_col_layout.addWidget(self._create_section_title("Beliefs"))
        self.current_beliefs_list = self._create_list_display()
        right_col_layout.addWidget(self.current_beliefs_list)
        
        right_col_layout.addWidget(self._create_section_title("Goals"))
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
        
        belief_layout = QVBoxLayout()
        belief_layout.addWidget(self._create_section_title("Beliefs History"))
        
        b_frame = self._create_frame()
        b_frame_layout = QVBoxLayout(b_frame)
        b_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.belief_view = self._create_log_list_view(self.belief_model)
        b_frame_layout.addWidget(self.belief_view)
        
        belief_layout.addWidget(b_frame)
        top_layout.addLayout(belief_layout)

        goal_layout = QVBoxLayout()
        goal_layout.addWidget(self._create_section_title("Goals History"))
        
        g_frame = self._create_frame()
        g_frame_layout = QVBoxLayout(g_frame)
        g_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.goal_view = self._create_log_list_view(self.goal_model)
        g_frame_layout.addWidget(self.goal_view)
        
        goal_layout.addWidget(g_frame)
        top_layout.addLayout(goal_layout)
        
        main_layout.addLayout(top_layout, stretch=1) 

        int_layout = QVBoxLayout()
        int_layout.addWidget(self._create_section_title("Intentions History"))
        
        i_frame = self._create_frame()
        i_frame_layout = QVBoxLayout(i_frame)
        i_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.intention_view = self._create_log_list_view(self.intention_model)
        i_frame_layout.addWidget(self.intention_view)
        
        int_layout.addWidget(i_frame)
        main_layout.addLayout(int_layout, stretch=1) 

        return tab

    def _create_perception_tab(self):
        tab = QWidget()
        main_layout = QHBoxLayout(tab) 
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        percept_frame = self._create_frame()
        percept_layout = QVBoxLayout(percept_frame)
        percept_layout.addWidget(self._create_section_title("Perceptions"))
        self.perceptions_tree = self._create_tree_display(['Key', 'Value'])
        self.perceptions_tree.setMinimumHeight(200)
        self.perceptions_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        percept_layout.addWidget(self.perceptions_tree)
        main_layout.addWidget(percept_frame, stretch=2) 

        lists_frame = self._create_frame()
        lists_layout = QVBoxLayout(lists_frame)
        
        lists_layout.addWidget(self._create_section_title("Environments"))
        self.envs_list = self._create_list_display(min_height=80)
        lists_layout.addWidget(self.envs_list)
        
        lists_layout.addWidget(self._create_section_title("Channels"))
        self.chs_list = self._create_list_display(min_height=80)
        lists_layout.addWidget(self.chs_list)
        
        lists_layout.addStretch()
        main_layout.addWidget(lists_frame, stretch=1) 
        
        return tab

    def _parse_intention_list_for_display(self, intention_str):
        if not isinstance(intention_str, str): return str(intention_str)
        try:
            goal_match = re.search(r"^(gain:Goal.*?\[.*?\])", intention_str)
            plan_match = re.search(r"->\s*([\w\d_]+)\(.*\)", intention_str)
            goal_str = goal_match.group(1) if goal_match else "Complex Goal"
            plan_name = plan_match.group(1) if plan_match else "Complex Plan"
            return f"Plan: {plan_name} | Goal: {goal_str}"
        except Exception: return intention_str 
            
    def _update_list_widget(self, list_widget, items_list):
        list_widget.clear()
        if not items_list:
            item = QListWidgetItem("No itens")
            item.setForeground(QColor(current_theme.get('text_disabled', '#888')))
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

    def _format_parsed_object_for_display(self, parsed_item):
        if not isinstance(parsed_item, dict): return str(parsed_item)
        if not parsed_item or parsed_item.get('type') == 'Unknown': return parsed_item.get('raw', str(parsed_item))
        tipo = parsed_item.get('type', '')
        predicate = parsed_item.get('predicate', '')
        args = parsed_item.get('args', [])
        source = parsed_item.get('source', '')
        args_str = ", ".join(map(str, args))
        return f"{tipo}: {predicate}({args_str}) [{source}]"

    def _safe_eval(self, literal):
        try: return ast.literal_eval(literal)
        except (ValueError, SyntaxError): return literal

    def _populate_tree(self, tree, data, parent_item=None):
        if parent_item is None:
            tree.clear()
            parent_item = tree.invisibleRootItem()
        if isinstance(data, str): data = self._safe_eval(data)
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
        if parent_item == tree.invisibleRootItem():
            tree.expandAll()
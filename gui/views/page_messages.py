import re
import math 
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QFrame, QButtonGroup, QLineEdit 
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from gui.assets.theme.theme_dark import theme_colors
from gui.assets.theme.utils import apply_shadow

class MessageCard(QFrame):
    def __init__(self, msg_dict, active_filter, action_string, parent=None):
        super().__init__(parent)
        self.setProperty("class", "page")
        self.setFrameShape(QFrame.StyledPanel)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        
        sender = msg_dict.get('sender', 'N/A')
        receiver_data = msg_dict.get('receiver', 'N/A')
        system_time = msg_dict.get('system_time', '00:00:00.000')
        
        sender_color = theme_colors['info']
        receiver_color = theme_colors['success']
        
        if isinstance(receiver_data, str):
            receivers_list = re.findall(r"[\"']?([\w\.-]+)[\"']?", receiver_data)
        elif isinstance(receiver_data, list):
            receivers_list = receiver_data
        else:
            receivers_list = [str(receiver_data)]

        if active_filter:
            if sender == active_filter:
                sender_color = theme_colors['danger'] 
                receiver_color = theme_colors['info'] 
            elif active_filter in receivers_list:
                sender_color = theme_colors['info']   
                receiver_color = theme_colors['danger'] 

        header_layout = QHBoxLayout()
        header_text = f"<b><font color='{sender_color}'>{sender}</font></b> → <b><font color='{receiver_color}'>{receiver_data}</font></b>"
        header_label = QLabel(header_text)
        header_label.setObjectName("MessageCardHeader")
        
        time_label = QLabel(f"[{system_time}]")
        time_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)

        performative = msg_dict.get('performative', 'MSG')
        content_raw = msg_dict.get('content', {}).get('raw', 'N/A')

        body_text = f"<b><font color='{theme_colors['warning']}'>[{performative}]</font></b> {content_raw}"
        body_label = QLabel(body_text)
        body_label.setObjectName("MessageCardBody")
        body_label.setWordWrap(True)
        
        action_label = QLabel(f"<i>Estado do Remetente: {action_string}</i>")
        action_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        action_label.setObjectName("MessageCardAction")

        main_layout.addLayout(header_layout) 
        main_layout.addWidget(action_label)  
        main_layout.addWidget(body_label)

        apply_shadow(self, blur_radius=10, offset_y=1, color="#0A0A0A")

class MensagensPage(QWidget):
    def __init__(self, log_store):
        super().__init__()
        self.log_store = log_store
        self.log_store_index = 0
        self.participants = set()
        self.active_filter = None
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        self.current_page = 0
        self.messages_per_page = 200 
        
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        card_frame = QFrame()
        card_frame.setFrameShape(QFrame.StyledPanel)
        card_frame.setObjectName("MainCard")
        card_frame.setProperty("class", "card")
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Monitor de Comunicação")
        title.setProperty("class", "h1")
        card_layout.addWidget(title)

        columns_layout = QHBoxLayout()
        card_layout.addLayout(columns_layout)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 5, 10, 5)

        filter_title = QLabel("Filtrar por Participante:")
        filter_title.setObjectName("ColumnTitle")
        filter_title.setProperty("class", "h2")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar participante...")
        self.search_input.textChanged.connect(self._on_participant_search_changed)

        self.show_all_button = QPushButton("Mostrar Todas")
        self.show_all_button.setObjectName("FilterButton")
        self.show_all_button.setCheckable(True)
        self.show_all_button.setChecked(True)
        self.show_all_button.clicked.connect(self._clear_filter)
        self.button_group.addButton(self.show_all_button)

        self.participants_scroll = QScrollArea()
        self.participants_scroll.setWidgetResizable(True)
        
        self.participants_widget = QWidget()
        self.participants_layout = QVBoxLayout(self.participants_widget)
        self.participants_layout.setAlignment(Qt.AlignTop)
        self.participants_layout.setSpacing(4)
        self.participants_scroll.setWidget(self.participants_widget)

        left_layout.addWidget(filter_title)
        left_layout.addWidget(self.search_input) 
        left_layout.addWidget(self.show_all_button)
        left_layout.addWidget(self.participants_scroll)
        columns_layout.addWidget(left_column, stretch=1) 

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(10, 5, 0, 5)

        log_title_layout = QHBoxLayout()
        log_title = QLabel("Histórico de Mensagens:")
        log_title.setObjectName("ColumnTitle")
        log_title.setProperty("class", "h2")
        
        self.message_count_label = QLabel("Total: 0")
        self.message_count_label.setStyleSheet("color: #9CA3AF; font-size: 14px; margin-top: 10px;")
        
        log_title_layout.addWidget(log_title)
        log_title_layout.addStretch()
        log_title_layout.addWidget(self.message_count_label)

        self.message_scroll_area = QScrollArea()
        self.message_scroll_area.setWidgetResizable(True)
        
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setAlignment(Qt.AlignTop)
        self.message_scroll_area.setWidget(self.message_container)
        
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 10, 0, 0)
        
        self.btn_prev = QPushButton("« Anterior")
        self.btn_prev.clicked.connect(self._go_to_prev_page)
        self.btn_prev.setEnabled(False)
        
        self.page_label = QLabel("Página 1 de 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.btn_next = QPushButton("Próxima »")
        self.btn_next.clicked.connect(self._go_to_next_page)
        self.btn_next.setEnabled(False)
        
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next)

        right_layout.addLayout(log_title_layout) 
        right_layout.addWidget(self.message_scroll_area, stretch=1) 
        right_layout.addLayout(pagination_layout) 
        columns_layout.addWidget(right_column, stretch=2)

        main_layout.addWidget(card_frame)

    def _on_participant_search_changed(self, text):
        search_text = text.strip().lower()
        for button in self.button_group.buttons():
            if button == self.show_all_button:
                continue
            
            button_text = button.text().lower()
            button.setVisible(search_text in button_text)
    
    def _extract_action_from_log(self, log_data):
        if not log_data: 
            return "Estado desconhecido"

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
            if match: return f"Plano: {match.group(1)}"
            match = re.search(r"\]\s*,\s*([\w\d_]+)\(.*\)", main_intention_str)
            if match: return f"Plano: {match.group(1)}"
        except (IndexError, TypeError):
            pass
        
        return "Executando Intenção"

    def on_store_updated(self):
        all_messages_from_store = self.log_store.get_all_messages()
        if len(all_messages_from_store) == self.log_store_index:
            return 

        new_messages = all_messages_from_store[self.log_store_index:]
        self.log_store_index = len(all_messages_from_store)
        
        new_messages_added = False
        for msg_dict in new_messages:
            new_messages_added = True
            
            sender = msg_dict.get('sender', 'N/A')
            self._add_participant(sender)
            
            receiver_data = msg_dict.get('receiver', 'N/A')
            if isinstance(receiver_data, str):
                receivers = re.findall(r"[\"']?([\w\.-]+)[\"']?", receiver_data)
            elif isinstance(receiver_data, list):
                receivers = receiver_data
            else:
                receivers = [str(receiver_data)]

            for r in receivers:
                self._add_participant(r)

        if not new_messages_added:
            return

        if self.current_page == 0:
             self._rebuild_message_display()
        else:
            self._update_pagination_labels()

    def _add_participant(self, agent_name):
        if agent_name not in self.participants and agent_name not in ['N/A', 'Desconhecido', 'broadcast', '[]']:
            self.participants.add(agent_name)
            self._add_participant_button(agent_name)
            return True 
        return False

    def _get_filtered_messages(self):
        current_messages = self.log_store.get_all_messages()
        
        if self.active_filter is None:
            filtered_messages = current_messages
        else:
            filtered_messages = []
            for msg in current_messages:
                sender = msg.get('sender', 'N/A')
                receiver_data = msg.get('receiver', 'N/A')
                
                if isinstance(receiver_data, str):
                    receivers = re.findall(r"[\"']?([\w\.-]+)[\"']?", receiver_data)
                elif isinstance(receiver_data, list):
                    receivers = receiver_data
                else:
                    receivers = [str(receiver_data)]
                
                if self.active_filter == sender or self.active_filter in receivers:
                    filtered_messages.append(msg)

        filtered_messages.sort(key=lambda m: m.get('system_time', '0'), reverse=True)
        return filtered_messages

    def _update_pagination_labels(self, total_filtered=None):
        if total_filtered is None:
            total_filtered = len(self._get_filtered_messages())

        total_pages = max(1, math.ceil(total_filtered / self.messages_per_page))
        
        if self.current_page >= total_pages:
            self.current_page = total_pages - 1
            
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        
        self.page_label.setText(f"Página {self.current_page + 1} de {total_pages}")
        
        if self.active_filter:
            self.message_count_label.setText(f"Filtrado: {total_filtered}")
        else:
            self.message_count_label.setText(f"Total: {total_filtered}")

    def _rebuild_message_display(self):
        self._clear_message_layout()
        
        filtered_messages = self._get_filtered_messages()
        total_filtered = len(filtered_messages)

        self._update_pagination_labels(total_filtered)
        
        start_index = self.current_page * self.messages_per_page
        end_index = start_index + self.messages_per_page
        display_messages = filtered_messages[start_index:end_index]
        
        for msg in display_messages:
            sender = msg.get('sender')
            log_index = msg.get('log_index')
            
            sender_state_log = self.log_store.get_latest_agent_state_before_index(sender, log_index)
            
            action_string = self._extract_action_from_log(sender_state_log)
            
            card = MessageCard(msg, self.active_filter, action_string)
            self.message_layout.addWidget(card)
        
        self.message_layout.addStretch() 

    def _go_to_next_page(self):
        self.current_page += 1
        self._rebuild_message_display()
        
    def _go_to_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._rebuild_message_display()
        
    def _clear_message_layout(self):
        item = self.message_layout.takeAt(self.message_layout.count() - 1)
        if item and not item.widget(): 
            del item
            
        while self.message_layout.count():
            child = self.message_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
    def _add_participant_button(self, agent_name):
        button = QPushButton(agent_name)
        button.setObjectName("FilterButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked, name=agent_name: self._set_filter(name))
        self.button_group.addButton(button)
        
        for i in range(self.participants_layout.count()):
            widget = self.participants_layout.itemAt(i).widget()
            if widget and widget.text() > agent_name:
                self.participants_layout.insertWidget(i, button)
                return
        self.participants_layout.addWidget(button)

    def _set_filter(self, agent_name):
        self.active_filter = agent_name
        self.current_page = 0 
        self._rebuild_message_display()

    def _clear_filter(self):
        self.active_filter = None
        self.current_page = 0 
        if self.button_group.checkedButton():
            self.button_group.checkedButton().setChecked(False)
        self.show_all_button.setChecked(True) 
        
        self._rebuild_message_display()
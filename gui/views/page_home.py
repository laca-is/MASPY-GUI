import math
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QFrame, QDoubleSpinBox, QAbstractSpinBox, QScrollArea,
                             QSizePolicy) 
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize
from gui.assets.theme.theme_dark import theme_colors
from gui.assets.theme.utils import apply_shadow

class IntentionCard(QFrame):
    def __init__(self, intention_data, parent=None):
        super().__init__(parent)
        self.setProperty("class", "page") 
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        system_time = intention_data.get('system_time', '00:00:00.000') 
        agent_name = intention_data.get('agent_name', 'N/A')
        last_event = intention_data.get('last_event', 'N/A').replace('gain:', '').replace('lose:', '')
        intention_str = intention_data.get('intention_str', 'N/A')

        header_layout = QHBoxLayout()
        header_text = f"<b><font color='{theme_colors['info']}'>{agent_name}</font></b>"
        header_label = QLabel(header_text)
        header_label.setObjectName("IntentionCardHeader")
        
        time_label = QLabel(f"[{system_time}]")
        time_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        
        trigger_label = QLabel(f"<i>Gatilho: {last_event}</i>")
        trigger_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        trigger_label.setObjectName("IntentionCardTrigger")

        body_label = QLabel(f"<b>{intention_str}</b>")
        body_label.setObjectName("IntentionCardBody")
        body_label.setWordWrap(True)

        layout.addLayout(header_layout)
        layout.addWidget(trigger_label)
        layout.addWidget(body_label)

        apply_shadow(self, blur_radius=10, offset_y=1, color="#0A0A0A")


class MenuInicialPage(QWidget):
    def __init__(self, command_queue, log_store):
        super().__init__()
        self.setProperty("class", "page")
        self.command_queue = command_queue
        self.log_store = log_store
        self.simulation_paused = False
        
        self.current_page = 0
        self.items_per_page = 200
        self.total_intentions = 0

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(25)

        title_label = QLabel("Dashboard da Simulação")
        title_label.setProperty("class", "h1")
        main_layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)

        #delay_label = QLabel("Atraso (s):")
        #self.delay_input = QDoubleSpinBox() 
        #self.delay_input.setRange(0.0, 60.0) 
        #self.delay_input.setValue(0.0)
        #self.delay_input.setSingleStep(0.1) 
        #self.delay_input.setDecimals(1) 
        #self.delay_input.setFixedWidth(100)
        #self.delay_input.setMinimumHeight(40) 
        #self.delay_input.setButtonSymbols(QAbstractSpinBox.NoButtons) 
        
        #self.start_button = QPushButton(" Iniciar Sistema") 
        #self.start_button.setMinimumHeight(40)
        #self.start_button.setMinimumWidth(150) 
        #self.start_button.setIcon(QIcon("gui/assets/icons/play-circle.svg"))
        #self.start_button.setIconSize(QSize(20, 20))
        #self.start_button.setCursor(Qt.PointingHandCursor)
        #self.start_button.clicked.connect(self._start_simulation)

        self.pause_button = QPushButton(" Pausar")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setMinimumWidth(150) 
        self.pause_button.setIcon(QIcon("gui/assets/icons/pause-circle.svg"))
        self.pause_button.setIconSize(QSize(20, 20))
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self._toggle_pause_simulation)

        #controls_layout.addWidget(delay_label)
        #controls_layout.addWidget(self.delay_input)
        controls_layout.addStretch()
        #controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.pause_button)
        main_layout.addLayout(controls_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        left_column_frame = QFrame()
        left_column_frame.setProperty("class", "card")
        left_layout = QVBoxLayout(left_column_frame)
        left_layout.setContentsMargins(15, 15, 15, 15)

        left_title_layout = QHBoxLayout()
        left_title = QLabel("Relatório Geral de Intenções")
        left_title.setProperty("class", "h2")
        self.intention_count_label = QLabel("Total: 0")
        self.intention_count_label.setStyleSheet("color: #9CA3AF; font-size: 14px; margin-top: 10px;")
        
        left_title_layout.addWidget(left_title)
        left_title_layout.addStretch()
        left_title_layout.addWidget(self.intention_count_label)
        left_layout.addLayout(left_title_layout)

        self.intention_scroll_area = QScrollArea()
        self.intention_scroll_area.setWidgetResizable(True)
        self.intention_container = QWidget()
        self.intention_layout = QVBoxLayout(self.intention_container)
        self.intention_layout.setAlignment(Qt.AlignTop)
        self.intention_scroll_area.setWidget(self.intention_container)
        left_layout.addWidget(self.intention_scroll_area, stretch=1)
        
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 10, 0, 0)
        self.btn_prev = QPushButton("« Anterior")
        self.btn_prev.clicked.connect(self._go_to_prev_page)
        self.page_label = QLabel("Página 1 de 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Próxima »")
        self.btn_next.clicked.connect(self._go_to_next_page)
        
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next)
        left_layout.addLayout(pagination_layout)
        
        content_layout.addWidget(left_column_frame, stretch=4) 

        right_column_frame = QFrame()
        right_column_frame.setProperty("class", "card")
        right_layout = QVBoxLayout(right_column_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)

        right_title = QLabel("Outras Informações (60%)")
        right_title.setProperty("class", "h2")
        right_layout.addWidget(right_title)
        
        placeholder_label = QLabel("Este espaço será usado futuramente.")
        placeholder_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(placeholder_label, stretch=1)
        
        content_layout.addWidget(right_column_frame, stretch=6) 

        main_layout.addLayout(content_layout, stretch=1)

    def _start_simulation(self):
        #delay_value = self.delay_input.value() 
        #self.command_queue.put(('START_SIMULATION', delay_value))
        #self.start_button.setEnabled(False)
        #self.start_button.setText(" Sistema Ativo") 
        #self.start_button.setProperty("class", "primary")
        self.pause_button.setEnabled(True)
        #self.delay_input.setEnabled(False)

    def _toggle_pause_simulation(self):
        self.command_queue.put('TOGGLE_PAUSE')
        
        if self.log_store:
            self.log_store.toggle_live_mode()
            
        self.simulation_paused = not self.simulation_paused
        
        if self.simulation_paused:
            self.pause_button.setText(" Retomar")
            self.pause_button.setIcon(QIcon("gui/assets/icons/play-circle.svg"))
        else:
            self.pause_button.setText(" Pausar")
            self.pause_button.setIcon(QIcon("gui/assets/icons/pause-circle.svg"))
            
    
    def on_store_updated(self):
        all_intentions = self.log_store.get_all_intentions_history()
        new_total = len(all_intentions)
        
        if new_total == self.total_intentions and not self.log_store.is_live:
             return
        
        self.total_intentions = new_total
        
        if self.current_page == 0:
            self._rebuild_intention_display(all_intentions)
        else:
            self._update_pagination_labels(self.total_intentions)

    def _get_filtered_intentions(self):
        current_intentions = self.log_store.get_all_intentions_history()
        
        current_intentions.reverse() 
        
        return current_intentions

    def _update_pagination_labels(self, total_filtered):
        total_pages = max(1, math.ceil(total_filtered / self.items_per_page))
        
        if self.current_page >= total_pages:
            self.current_page = total_pages - 1
            
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < total_pages - 1)
        
        self.page_label.setText(f"Página {self.current_page + 1} de {total_pages}")
        self.intention_count_label.setText(f"Total: {total_filtered}")

    def _rebuild_intention_display(self, filtered_intentions):
        self._clear_intention_layout()
        
        total_filtered = len(filtered_intentions)

        self._update_pagination_labels(total_filtered)
        
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        display_intentions = filtered_intentions[start_index:end_index]
        
        for intention_data in display_intentions:
            card = IntentionCard(intention_data)
            self.intention_layout.addWidget(card)
        
        self.intention_layout.addStretch() 

    def _go_to_next_page(self):
        self.current_page += 1
        self._rebuild_intention_display(self._get_filtered_intentions())
        
    def _go_to_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._rebuild_intention_display(self._get_filtered_intentions())
        
    def _clear_intention_layout(self):
        while self.intention_layout.count():
            child = self.intention_layout.takeAt(0)
            if child.widget(): 
                child.widget().deleteLater()
            elif child.spacerItem():
                self.intention_layout.removeItem(child)
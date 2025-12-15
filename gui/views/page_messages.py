import re
import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QButtonGroup,
    QListView, QAbstractItemView, QStyledItemDelegate, QScrollArea
)
from PyQt5.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QSize, QRectF, QRect
)
from PyQt5.QtGui import (
    QColor, QPainter, QFontMetrics, QFont, QPen, QPainterPath
)
from gui.assets.theme.styler import current_theme

PADDING = 10
CARD_MARGIN = 6

class PaginatedMessageModel(QAbstractListModel):
    def __init__(self, log_store, items_per_page=100, parent=None):
        super().__init__(parent)
        self.log_store = log_store
        self.items_per_page = items_per_page
        self.current_page = 0
        
        self._raw_list_ref = []  
        self._limit_index = 0    
        self._filtered_indices = None 
        self._total_count = 0

    def update_data_cache(self):
        self._raw_list_ref = self.log_store.get_messages_reference()
        self._limit_index = self.log_store.get_message_count_limit()
        
        if self._filtered_indices is not None:
            self._total_count = len(self._filtered_indices)
        else:
            self._total_count = self._limit_index

    def rowCount(self, parent=QModelIndex()):
        remaining = self._total_count - (self.current_page * self.items_per_page)
        return max(0, min(remaining, self.items_per_page))

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        
        if role == Qt.DisplayRole:
            row = index.row()
            real_offset = (self.current_page * self.items_per_page) + row
            
            target_msg = None
            if self._filtered_indices is None:
                if real_offset < self._limit_index:
                    actual_index = self._limit_index - 1 - real_offset
                    if 0 <= actual_index < len(self._raw_list_ref):
                        target_msg = self._raw_list_ref[actual_index]
            else:
                total = len(self._filtered_indices)
                if real_offset < total:
                    idx = self._filtered_indices[total - 1 - real_offset]
                    if idx < len(self._raw_list_ref):
                        target_msg = self._raw_list_ref[idx]
            return target_msg
                
        return None

    def set_page(self, page):
        self.beginResetModel()
        self.current_page = page
        self.endResetModel()

    def set_filter(self, participant_name):
        self.beginResetModel()
        self.current_page = 0
        if not participant_name:
            self._filtered_indices = None
        else:
            self._raw_list_ref = self.log_store.get_messages_reference()
            limit = self.log_store.get_message_count_limit()
            indices = []
            for i in range(limit):
                m = self._raw_list_ref[i]
                sender = m.sender
                receiver_str = m.receiver 
                
                receivers = []
                if "[" in receiver_str:
                     receivers = re.findall(r"[\"']?([\w\.-]+)[\"']?", receiver_str)
                else:
                     receivers = [receiver_str]

                if sender == participant_name or participant_name in receivers:
                    indices.append(i)
            self._filtered_indices = indices
        
        self.update_data_cache()
        self.endResetModel()

    def get_total_items(self): return self._total_count
    def get_total_pages(self): return max(1, math.ceil(self._total_count / self.items_per_page))

class MessageCardDelegate(QStyledItemDelegate):
    def __init__(self, parent_view):
        super().__init__(parent_view)
        self.active_filter = None
        self._update_colors()

    def _update_colors(self):
        self.c_bg = QColor(current_theme.get('background_secondary', '#1F2937'))
        self.c_border = QColor(current_theme.get('background_tertiary', '#4B5563'))

        is_light = current_theme.get('background_primary', '#111827') != "#111827"
        shadow_alpha = 60 if is_light else 30
        self.c_shadow = QColor(0, 0, 0, shadow_alpha)
        
        self.c_info = QColor(current_theme.get('info', '#0EA5E9'))
        self.c_success = QColor(current_theme.get('success', '#10B981'))
        self.c_danger = QColor(current_theme.get('danger', '#EF4444'))
        self.c_warning = QColor(current_theme.get('warning', '#F59E0B'))
        
        self.c_text_sec = QColor(current_theme.get('text_secondary', '#9CA3AF'))
        self.c_text_pri = QColor(current_theme.get('text_primary', '#F9FAFB'))
        self.c_arrow = QColor(current_theme.get('text_disabled', '#6B7280'))
        
        base_font = QFont("Segoe UI", 11)
        self.font_bold = QFont(base_font); self.font_bold.setBold(True)
        self.font_italic = QFont(base_font); self.font_italic.setPointSize(10); self.font_italic.setItalic(True)
        self.font_normal = base_font
        self.font_small = QFont(base_font); self.font_small.setPointSize(10)
        self.fm_normal = QFontMetrics(self.font_normal)

    def update_theme(self):
        self._update_colors()

    def set_filter_state(self, active_filter):
        self.active_filter = active_filter

    def sizeHint(self, option, index):
        msg = index.data(Qt.DisplayRole)
        if not msg: return QSize(0,0)

        width = option.rect.width() - (2 * PADDING) - 10
        if width <= 0: width = 200

        header_height = 55 
        content_txt = f"[{msg.performative}] {msg.content}"
        rect = self.fm_normal.boundingRect(0, 0, width, 10000, Qt.TextWordWrap, content_txt)
        
        total_height = header_height + rect.height() + 10 
        return QSize(option.rect.width(), int(total_height))

    def paint(self, painter, option, index):
        msg = index.data(Qt.DisplayRole)
        if not msg: return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = option.rect.adjusted(5, 5, -5, -5)
        
        path_shadow = QPainterPath()
        path_shadow.addRoundedRect(QRectF(rect.adjusted(2, 2, 2, 2)), 6, 6)
        painter.fillPath(path_shadow, self.c_shadow)

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 6, 6)
        painter.setBrush(self.c_bg)
        painter.setPen(QPen(self.c_border, 1))
        painter.drawPath(path)

        sender = msg.sender
        receiver_data = msg.receiver
        system_time = f"[{msg.system_time}]"
        performative = f"[{msg.performative}]"
        content = msg.content
        action_str = f"Sender state: {msg.sender_action}"

        c_snd = self.c_info
        c_rcv = self.c_success
        
        if self.active_filter:
            is_receiver = self.active_filter in receiver_data 
            if sender == self.active_filter:
                c_snd = self.c_danger
                c_rcv = self.c_info
            elif is_receiver:
                c_snd = self.c_info
                c_rcv = self.c_danger

        current_y = rect.top() + PADDING + self.fm_normal.ascent()
        current_x = rect.left() + PADDING
        
        painter.setFont(self.font_bold)
        painter.setPen(c_snd)
        painter.drawText(current_x, current_y, sender)
        current_x += QFontMetrics(self.font_bold).width(sender) + 5

        painter.setFont(self.font_normal)
        painter.setPen(self.c_arrow)
        painter.drawText(current_x, current_y, "→")
        current_x += QFontMetrics(self.font_normal).width("→") + 5

        painter.setFont(self.font_bold)
        painter.setPen(c_rcv)
        painter.drawText(current_x, current_y, receiver_data)
        
        painter.setFont(self.font_small)
        painter.setPen(self.c_text_sec)
        time_width = QFontMetrics(self.font_small).width(system_time)
        painter.drawText(rect.right() - PADDING - time_width, current_y, system_time)

        current_y += 18 
        painter.setFont(self.font_italic)
        painter.setPen(self.c_text_sec)
        painter.drawText(rect.left() + PADDING, current_y, action_str)

        current_y += 20 
        
        painter.setFont(self.font_bold)
        painter.setPen(self.c_warning)
        painter.drawText(rect.left() + PADDING, current_y, performative)
        
        perf_width = QFontMetrics(self.font_bold).width(performative)
        
        text_rect = QRectF(
            rect.left() + PADDING + perf_width + 5, 
            current_y - self.fm_normal.ascent(), 
            rect.width() - (2 * PADDING) - perf_width - 5,
            rect.bottom() - current_y + self.fm_normal.ascent() - PADDING
        )
        
        painter.setFont(self.font_normal)
        painter.setPen(self.c_text_pri)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.TextWordWrap, content)

        painter.restore()

class MensagensPage(QWidget):
    def __init__(self, log_store):
        super().__init__()
        self.setProperty("class", "page")
        self.log_store = log_store
        
        self.log_store_index = 0
        self.participants = set()
        self.active_filter = None
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        card_frame = QFrame()
        card_frame.setFrameShape(QFrame.StyledPanel)
        card_frame.setProperty("class", "card")
        
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Communication Monitor")
        title.setProperty("class", "h1")
        card_layout.addWidget(title)

        columns_layout = QHBoxLayout()
        card_layout.addLayout(columns_layout)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 5, 10, 5)

        filter_title = QLabel("Agent Filter:")
        filter_title.setObjectName("ColumnTitle")
        filter_title.setProperty("class", "h2")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Agent")
        self.search_input.textChanged.connect(self._on_participant_search_changed)

        self.show_all_button = QPushButton("Show all")
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
        log_title = QLabel("Messages History:")
        log_title.setProperty("class", "h2")

        self.message_count_label = QLabel("Total: 0")
        self.message_count_label.setProperty("class", "text-secondary")
        
        log_title_layout.addWidget(log_title)
        log_title_layout.addStretch()
        log_title_layout.addWidget(self.message_count_label)

        self.message_list_view = QListView()
        self.message_list_view.setFrameShape(QFrame.NoFrame)
        self.message_list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.message_list_view.setStyleSheet("background: transparent; border: none;")
        self.message_list_view.setUniformItemSizes(False)
        self.message_list_view.setResizeMode(QListView.Adjust)
        
        self.model = PaginatedMessageModel(self.log_store, items_per_page=100)
        self.delegate = MessageCardDelegate(self.message_list_view)
        
        self.message_list_view.setModel(self.model)
        self.message_list_view.setItemDelegate(self.delegate)

        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("« Previous")
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.btn_next = QPushButton("Next »")
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)
        
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next)

        right_layout.addLayout(log_title_layout) 
        right_layout.addWidget(self.message_list_view, stretch=1) 
        right_layout.addLayout(pagination_layout)
        
        columns_layout.addWidget(right_column, stretch=2)
        main_layout.addWidget(card_frame)

    def on_store_updated(self):
        self.model.update_data_cache()
        self._update_pagination_ui()
        if self.model.current_page == 0:
             self.message_list_view.viewport().update()

        all_msgs = self.log_store.get_all_messages()
        if len(all_msgs) > self.log_store_index:
            new_msgs = all_msgs[self.log_store_index:]
            self.log_store_index = len(all_msgs)
            
            for m in new_msgs:
                self._add_participant(m.sender)
                
                recv_str = m.receiver
                if "[" in recv_str: 
                    found = re.findall(r"[\"']?([\w\.-]+)[\"']?", recv_str)
                    for x in found: self._add_participant(x)
                else:
                    self._add_participant(recv_str)

    def _update_pagination_ui(self):
        total_items = self.model.get_total_items()
        total_pages = self.model.get_total_pages()
        current = self.model.current_page
        
        self.page_label.setText(f"Page {current + 1} of {total_pages}")
        
        txt_total = f"Total: {total_items}"
        if self.active_filter: txt_total = f"Filtering: {total_items}"
        self.message_count_label.setText(txt_total)
        
        self.btn_prev.setEnabled(current > 0)
        self.btn_next.setEnabled(current < total_pages - 1)

    def _next_page(self):
        if self.model.current_page < self.model.get_total_pages() - 1:
            self.model.set_page(self.model.current_page + 1)
            self._update_pagination_ui()
            self.message_list_view.scrollToTop()

    def _prev_page(self):
        if self.model.current_page > 0:
            self.model.set_page(self.model.current_page - 1)
            self._update_pagination_ui()
            self.message_list_view.scrollToTop()

    def _on_participant_search_changed(self, text):
        search_text = text.strip().lower()
        for button in self.button_group.buttons():
            if button == self.show_all_button:
                continue
            
            button_text = button.text().lower()
            button.setVisible(search_text in button_text)

    def _add_participant(self, agent_name):
        if not agent_name or agent_name in self.participants or agent_name in ['N/A', 'Unknown', 'broadcast', '[]']:
            return False
        
        self.participants.add(agent_name)
        self._add_participant_button(agent_name)
        return True

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

    def _set_filter(self, name):
        self.active_filter = name
        self.model.set_filter(name)
        self.delegate.set_filter_state(name)
        self._update_pagination_ui()
        self.message_list_view.scrollToTop()

    def _clear_filter(self):
        self.active_filter = None
        
        if self.button_group.checkedButton():
            self.button_group.checkedButton().setChecked(False)
        self.show_all_button.setChecked(True)
        
        self.model.set_filter(None)
        self.delegate.set_filter_state(None)
        self._update_pagination_ui()
        self.message_list_view.scrollToTop()

    def update_theme(self):
        self.delegate.update_theme()

        self.message_list_view.viewport().update()
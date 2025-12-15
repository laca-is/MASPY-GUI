import math
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFrame, QListView, QAbstractItemView, QStyledItemDelegate, QSizePolicy
) 
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QPen, QFontMetrics, QPainterPath
from PyQt5.QtCore import Qt, QSize, QAbstractListModel, QModelIndex, QRectF
from gui.assets.theme.styler import current_theme
from pathlib import Path

class PaginatedIntentionModel(QAbstractListModel):
    def __init__(self, log_store, items_per_page=100, parent=None):
        super().__init__(parent)
        self.log_store = log_store
        self.items_per_page = items_per_page
        self.current_page = 0
        self._total_count = 0

    def rowCount(self, parent=QModelIndex()):
        total = len(self.log_store.get_all_intentions_history())
        self._total_count = total
        remaining = total - (self.current_page * self.items_per_page)
        return max(0, min(remaining, self.items_per_page))

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            source_list = self.log_store.get_all_intentions_history()
            total = len(source_list)
            
            real_offset = (self.current_page * self.items_per_page) + index.row()
            if real_offset >= total: return None
            
            actual_index = total - 1 - real_offset
            return source_list[actual_index]
        return None

    def set_page(self, page):
        self.beginResetModel()
        self.current_page = page
        self.endResetModel()

    def refresh_if_needed(self):
        if self.current_page == 0:
            self.layoutChanged.emit()

    def get_total_pages(self):
        total = len(self.log_store.get_all_intentions_history())
        return max(1, math.ceil(total / self.items_per_page))

class IntentionDelegateCard(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.padding = 15
        self.spacing = 5
        self._update_colors()

    def _update_colors(self):
        self.c_bg_secondary = QColor(current_theme.get('background_secondary', '#1F2937'))
        self.c_bg_tertiary = QColor(current_theme.get('background_tertiary', '#4B5563'))
        self.c_text_pri = QColor(current_theme.get('text_primary', '#F9FAFB'))
        self.c_text_sec = QColor(current_theme.get('text_secondary', '#9CA3AF'))
        self.c_info = QColor(current_theme.get('info', '#0EA5E9')) 

        is_light = current_theme.get('background_primary', '#111827') != "#111827"
        self.c_shadow = QColor("#000000")
        self.c_shadow.setAlpha(60 if is_light else 30)

    def update_theme(self):
        self._update_colors()

    def paint(self, painter, option, index):
        item = index.data(Qt.DisplayRole)
        if not item: return

        try:
            agent_name = getattr(item, 'agent_name', 'N/A')
            time_str = getattr(item, 'system_time', '00:00:00')
            trigger_raw = getattr(item, 'trigger', 'N/A')
            intention = getattr(item, 'intention', 'N/A')
        except AttributeError:
            agent_name = item.get('agent_name', 'N/A')
            time_str = item.get('system_time', '00:00:00.000')
            trigger_raw = item.get('last_event', 'N/A')
            intention = item.get('intention_str', 'N/A')

        trigger = str(trigger_raw).replace('gain:', '').replace('lose:', '')

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(option.rect).adjusted(5, 5, -5, -5)

        shadow_rect = rect.translated(0, 1)
        path_shadow = QPainterPath()
        path_shadow.addRoundedRect(shadow_rect, 4, 4)
        painter.setBrush(self.c_shadow)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path_shadow)

        path_bg = QPainterPath()
        path_bg.addRoundedRect(rect, 4, 4)
        painter.setBrush(self.c_bg_secondary)
        painter.setPen(QPen(self.c_bg_tertiary, 1)) 
        painter.drawPath(path_bg)

        f_default = QFont("Segoe UI", 11)
        f_bold = QFont("Segoe UI", 11, QFont.Bold)
        f_italic = QFont("Segoe UI", 11); f_italic.setItalic(True)
        
        fm_bold = QFontMetrics(f_bold)
        fm_italic = QFontMetrics(f_italic)

        content_rect = rect.adjusted(self.padding, self.padding, -self.padding, -self.padding)
        y = content_rect.top()
        w = content_rect.width()

        painter.setFont(f_bold)
        painter.setPen(self.c_info)
        painter.drawText(QRectF(content_rect.left(), y, w, fm_bold.height()), Qt.AlignLeft, agent_name)

        time_txt = f"[{time_str}]"
        painter.setFont(f_default)
        painter.setPen(self.c_text_sec)
        painter.drawText(QRectF(content_rect.left(), y, w, fm_bold.height()), Qt.AlignRight, time_txt)

        y += fm_bold.height() + self.spacing

        painter.setFont(f_italic)
        painter.setPen(self.c_text_sec)
        trig_txt = f"Trigger: {trigger}"
        painter.drawText(QRectF(content_rect.left(), y, w, fm_italic.height()), Qt.AlignLeft, trig_txt)

        y += fm_italic.height() + self.spacing

        painter.setFont(f_bold) 
        painter.setPen(self.c_text_pri)
        
        text_rect = QRectF(content_rect.left(), y, w, content_rect.bottom() - y)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.TextWordWrap, intention)

        painter.restore()

    def sizeHint(self, option, index):
        item = index.data(Qt.DisplayRole)
        if not item: return QSize(0, 0)
        
        try:
            intention = getattr(item, 'intention', '')
        except AttributeError:
            intention = item.get('intention_str', '')

        w = option.rect.width() - 10 - (2 * self.padding)
        if w <= 0: w = 200

        fm = QFontMetrics(QFont("Segoe UI", 11, QFont.Bold))
        h_header = fm.height()
        h_trigger = fm.height()
        
        rect_text = fm.boundingRect(0, 0, int(w), 5000, Qt.AlignLeft | Qt.TextWordWrap, intention)
        
        h_total = (
            10 +
            (2 * self.padding) + 
            h_header + 
            self.spacing + 
            h_trigger + 
            self.spacing + 
            rect_text.height()
        )

        return QSize(option.rect.width(), int(h_total))

class MenuInicialPage(QWidget):
    def __init__(self, command_queue, log_store):
        super().__init__()
        self.setProperty("class", "page")
        self.command_queue = command_queue
        self.log_store = log_store
        self.simulation_paused = False
        self.gui_path = Path(__file__).resolve().parent.parent
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(25)

        title_label = QLabel("Simulation Dashboard")
        title_label.setProperty("class", "h1")
        main_layout.addWidget(title_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(20)
        
        self.pause_button = QPushButton(" Pause")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setMinimumWidth(150)
        try:
            self.pause_button.setIcon(QIcon(f"{self.gui_path}/assets/icons/pause-circle.svg"))
        except: pass
        self.pause_button.setIconSize(QSize(20, 20))
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self._toggle_pause_simulation)

        controls_layout.addStretch()
        controls_layout.addWidget(self.pause_button)
        main_layout.addLayout(controls_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        left_column_frame = QFrame()
        left_column_frame.setProperty("class", "card") 
        left_layout = QVBoxLayout(left_column_frame)
        left_layout.setContentsMargins(15, 15, 15, 15)

        left_title_layout = QHBoxLayout()
        left_title = QLabel("Intentions Report")
        left_title.setProperty("class", "h2")

        self.intention_count_label = QLabel("Total: 0")
        self.intention_count_label.setProperty("class", "text-secondary")
        
        left_title_layout.addWidget(left_title)
        left_title_layout.addStretch()
        left_title_layout.addWidget(self.intention_count_label)
        left_layout.addLayout(left_title_layout)

        self.intention_list = QListView()
        self.intention_list.setFrameShape(QFrame.NoFrame)
        self.intention_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.intention_list.setUniformItemSizes(False)
        self.intention_list.setResizeMode(QListView.Adjust)
        self.intention_list.setStyleSheet("background: transparent; border: none;")
        
        self.model = PaginatedIntentionModel(self.log_store, items_per_page=200)
        self.delegate = IntentionDelegateCard()
        
        self.intention_list.setModel(self.model)
        self.intention_list.setItemDelegate(self.delegate)

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
        
        left_layout.addWidget(self.intention_list, stretch=1)
        left_layout.addLayout(pagination_layout)
        
        content_layout.addWidget(left_column_frame, stretch=4) 

        right_column_frame = QFrame()
        right_column_frame.setProperty("class", "card")
        right_layout = QVBoxLayout(right_column_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)

        right_title = QLabel("Another Informations (60%)")
        right_title.setProperty("class", "h2")
        right_layout.addWidget(right_title)
        
        placeholder_label = QLabel("This place will be used.")
        placeholder_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(placeholder_label, stretch=1)
        
        content_layout.addWidget(right_column_frame, stretch=6) 
        main_layout.addLayout(content_layout, stretch=1)

        self.pause_button.setEnabled(True) 

    def _toggle_pause_simulation(self):
        self.command_queue.put('TOGGLE_PAUSE')
        self.log_store.toggle_live_mode()
        self.simulation_paused = not self.simulation_paused
        
        if self.simulation_paused:
            self.pause_button.setText(" Play")
            try: self.pause_button.setIcon(QIcon(f"{self.gui_path}/assets/icons/play-circle.svg"))
            except: pass
        else:
            self.pause_button.setText(" Pause")
            try: self.pause_button.setIcon(QIcon(f"{self.gui_path}/assets/icons/pause-circle.svg"))
            except: pass
            
    def on_store_updated(self):
        total = len(self.log_store.get_all_intentions_history())
        if self.model._total_count != total:
             self._update_pagination_ui()
             self.model.refresh_if_needed()

    def _update_pagination_ui(self):
        total = len(self.log_store.get_all_intentions_history())
        total_pages = self.model.get_total_pages()
        current = self.model.current_page
        
        self.page_label.setText(f"Page {current + 1} of {total_pages}")
        self.intention_count_label.setText(f"Total: {total}")
        
        self.btn_prev.setEnabled(current > 0)
        self.btn_next.setEnabled(current < total_pages - 1)

    def _next_page(self):
        if self.model.current_page < self.model.get_total_pages() - 1:
            self.model.set_page(self.model.current_page + 1)
            self._update_pagination_ui()
            self.intention_list.scrollToTop()

    def _prev_page(self):
        if self.model.current_page > 0:
            self.model.set_page(self.model.current_page - 1)
            self._update_pagination_ui()
            self.intention_list.scrollToTop()

    def update_theme(self):
        self.delegate.update_theme()
        
        self.intention_list.viewport().update()
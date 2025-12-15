import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, 
    QListView, QStyledItemDelegate, QStyle, QApplication
)
from PyQt5.QtCore import Qt, QSize, QAbstractListModel, QModelIndex, QRect, QRectF
from PyQt5.QtGui import QColor, QPainter, QFont, QPen, QFontMetrics, QPainterPath

from gui.widgets.agent_detail_window import AgentDetailWindow
from gui.assets.theme.styler import current_theme
def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

class AgentListModel(QAbstractListModel):
    def __init__(self, agents_list=None, parent=None):
        super().__init__(parent)
        self._agents = agents_list or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._agents)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self._agents[index.row()]
        return None

    def update_list(self, new_list):
        self.beginResetModel()
        self._agents = new_list
        self.endResetModel()

class AgentVisualDelegate(QStyledItemDelegate):
    def __init__(self, data_model, parent_view, parent=None):
        super().__init__(parent)
        self.data_model = data_model
        self.parent_view = parent_view
        self._update_colors()

    def _update_colors(self):

        self.c_bg = QColor(current_theme.get('background_secondary', '#1F2937'))
        self.c_border = QColor(current_theme.get('background_tertiary', '#4B5563'))
        self.c_border_hover = QColor(current_theme.get('interactive_primary', '#3B82F6'))
        self.c_text_pri = QColor(current_theme.get('text_primary', '#F9FAFB'))
        self.c_text_sec = QColor(current_theme.get('text_secondary', '#9CA3AF'))
        
        self.c_btn_bg = QColor(current_theme.get('interactive_primary', '#3B82F6'))
        self.c_btn_txt = QColor(current_theme.get('interactive_text', '#FFFFFF'))
        self.c_accent = QColor(current_theme.get('info', '#0EA5E9'))

    def update_theme(self):
        self._update_colors()

    def _extract_action_from_log(self, log_data):
        desc = getattr(log_data, "desc", "")
        if desc:
            match = re.search(r"doing action \*(\w+)", desc)
            if match: return f"Running: {match.group(1)}"
            match = re.search(r"action:\s*\*(\w+)", desc)
            if match: return f"Running: {match.group(1)}"
        
        running_intentions = getattr(log_data, "running_intentions", [])
        if not running_intentions: return "Idle"
        try:
            main_intention_str = running_intentions[0]
            match = re.search(r"->\s*([\w\d_]+)\(.*\)\s*Context=", main_intention_str)
            if match: return f"Plano: {match.group(1)}"
            match = re.search(r"\]\s*,\s*([\w\d_]+)\(.*\)", main_intention_str)
            if match: return f"Plano: {match.group(1)}"
        except (IndexError, TypeError): pass
        return "Running Intention"

    def paint(self, painter, option, index):
        agent_name = index.data(Qt.DisplayRole)
        state = self.data_model.get_latest_agent_state(agent_name)
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect.adjusted(5, 5, -5, -5)
        is_hover = option.state & QStyle.State_MouseOver
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 8, 8) 
        
        painter.setBrush(self.c_bg)
        if is_hover:
            painter.setPen(QPen(self.c_border_hover, 2))
        else:
            painter.setPen(QPen(self.c_border, 2))
        
        painter.drawPath(path)

        f_title = QFont(option.font); f_title.setBold(True); f_title.setPointSize(12)
        f_meta = QFont(option.font); f_meta.setPointSize(10)
        f_stat = QFont(option.font); f_stat.setBold(True); f_stat.setPointSize(11)
        f_btn = QFont(option.font); f_btn.setBold(True); f_btn.setPointSize(9)

        padding = 15
        current_y = rect.top() + padding

        fm_title = QFontMetrics(f_title)
        title_rect = QRect(rect.left() + padding, current_y, rect.width() - (2*padding), fm_title.height())
        
        painter.setFont(f_title)
        painter.setPen(self.c_text_pri)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, agent_name)
        
        cycle_val = str(getattr(state, 'cycle', 0)) if state else "0"
        painter.setFont(f_meta)
        painter.setPen(self.c_text_sec)
        painter.drawText(title_rect, Qt.AlignRight | Qt.AlignVCenter, f"Cycle: {cycle_val}")

        current_y += title_rect.height() + 8

        beliefs_list = getattr(state, 'beliefs', []) if state else []
        goals_list = getattr(state, 'goals', []) if state else []
        
        painter.setFont(f_meta)
        painter.setPen(self.c_text_sec)
        
        stats_rect = QRect(rect.left() + padding, current_y, rect.width() - (2*padding), 20)
        painter.drawText(stats_rect, Qt.AlignLeft, f"Beliefs: {len(beliefs_list)}")
        painter.drawText(stats_rect.adjusted(100, 0, 0, 0), Qt.AlignLeft, f"Goals: {len(goals_list)}")

        current_y += 25

        action_str = self._extract_action_from_log(state) if state else "Aguardando..."
        action_rect = QRect(rect.left() + padding, current_y, rect.width() - (2*padding), 40)
        painter.setFont(f_stat)
        painter.setPen(self.c_accent)
        painter.drawText(action_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, action_str)

        btn_height = 30
        btn_rect = QRect(rect.left() + padding, rect.bottom() - padding - btn_height + 5, 
                         rect.width() - (2*padding), btn_height)
        
        btn_path = QPainterPath()
        btn_path.addRoundedRect(QRectF(btn_rect), 6, 6)
        
        painter.setBrush(self.c_btn_bg)
        painter.setPen(Qt.NoPen)
        painter.drawPath(btn_path)

        painter.setPen(self.c_btn_txt)
        painter.setFont(f_btn)
        painter.drawText(btn_rect, Qt.AlignCenter, "View Details")

        painter.restore()

    def sizeHint(self, option, index):
        if not self.parent_view or self.parent_view.viewport().width() <= 0:
            return QSize(250, 170)
        
        view_width = self.parent_view.viewport().width()
        available_width = view_width - 30
        
        cols = max(1, available_width // 260)
        card_width = int(available_width / cols) - 10
        
        if card_width < 220: card_width = 220
        
        return QSize(card_width, 170)

class AgentesPage(QWidget):
    def __init__(self, log_store, data_model):
        super().__init__()
        self.setProperty("class", "page")
        self.data_model = data_model
        self.log_store = log_store
        self.all_agents_list = []
        self.open_windows = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search agents by name")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.on_search_changed)
        
        self.status_label = QLabel("Awaiting data...")
        self.status_label.setProperty("class", "text-secondary")
        
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        self.agent_view = QListView()
        self.agent_view.setViewMode(QListView.IconMode) 
        self.agent_view.setResizeMode(QListView.Adjust) 
        self.agent_view.setUniformItemSizes(True)
        self.agent_view.setSpacing(10)
        
        self.agent_view.setStyleSheet("""
            QListView { 
                background: transparent; 
                border: none; 
                outline: none;
            }
            QListView::item {
                background: transparent;
            }
            QListView::item:selected {
                background: transparent;
                border: none;
            }
        """)
        
        self.agent_view.clicked.connect(self.on_agent_clicked)
        
        self.model = AgentListModel()
        self.delegate = AgentVisualDelegate(self.data_model, self.agent_view)
        
        self.agent_view.setModel(self.model)
        self.agent_view.setItemDelegate(self.delegate)
        
        layout.addWidget(self.agent_view)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.agent_view.scheduleDelayedItemsLayout()

    def on_agent_list_updated(self, agents):
        self.all_agents_list = sorted(agents, key=natural_sort_key)
        self._update_filter()

    def on_search_changed(self):
        self._update_filter()

    def _update_filter(self):
        txt = self.search_input.text().strip().lower()
        
        if not txt: 
            final_list = self.all_agents_list
        else: 
            final_list = [a for a in self.all_agents_list if txt in a.lower()]
            
        self.model.update_list(final_list)
        self.status_label.setText(f"Total: {len(final_list)} agents")

    def on_store_updated(self):
        self.agent_view.viewport().update()

    def on_agent_clicked(self, index):
        agent_name = index.data(Qt.DisplayRole)
        if not agent_name: 
            return

        if agent_name in self.open_windows:
            try:
                if self.open_windows[agent_name].isVisible():
                    self.open_windows[agent_name].activateWindow()
                    return
            except RuntimeError:
                pass

        detail_window = AgentDetailWindow(agent_name, self.data_model)
        detail_window.destroyed.connect(lambda: self.on_window_closed(agent_name))
        self.open_windows[agent_name] = detail_window
        detail_window.show()

    def on_window_closed(self, agent_name):
        self.data_model.stop_observing_agent(agent_name)
        if agent_name in self.open_windows:
            del self.open_windows[agent_name]

    def update_theme(self):

        self.delegate.update_theme()

        self.agent_view.viewport().update()
        for agent_name, window in list(self.open_windows.items()):
            try:
                if window.isVisible() and hasattr(window, 'update_theme'):
                    window.update_theme()
            except RuntimeError:
                pass
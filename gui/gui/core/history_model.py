from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex, QSize
from PyQt5.QtGui import QColor, QPainter, QFontMetrics
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

from gui.assets.theme.styler import current_theme

class HistoryItem:
    __slots__ = ('type', 'content', 'time', 'cycle')

    def __init__(self, msg_type, content, time, cycle):
        self.type = msg_type  
        self.content = content
        self.time = time
        self.cycle = cycle

class HistoryLogModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None
        
        if role == Qt.UserRole:
            return self._data[index.row()]
        
        return None

    def set_items(self, new_items):
        self.beginResetModel()
        self._data = new_items
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

class HistoryLogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, theme_colors_dict=None):
        super().__init__(parent)
        self.padding_left = 5
        self.padding_top = 6
        
        self._update_colors()

    def update_theme_colors(self, new_theme_dict=None):
        self._update_colors()

    def _update_colors(self):
        self.c_gain = QColor(current_theme.get("success", "#10B981"))
        self.c_lose = QColor(current_theme.get("danger", "#EF4444"))
        self.c_info = QColor(current_theme.get("info", "#0EA5E9"))

        self.c_time = QColor(current_theme.get("text_secondary", "#9CA3AF"))
        self.c_text = QColor(current_theme.get("text_primary", "#F9FAFB"))
        self.c_bg = QColor(current_theme.get("background_primary", "#111827"))
        self.c_bg_sel = QColor(current_theme.get("background_secondary", "#1F2937"))

    def paint(self, painter, option, index):
        item = index.data(Qt.UserRole)
        if not item:
            return

        painter.save()
        rect = option.rect
        
        bg_color = self.c_bg
        if option.state & QStyle.State_Selected:
            bg_color = self.c_bg_sel
        elif option.state & QStyle.State_MouseOver:
            bg_color = self.c_bg.lighter(110)
        painter.fillRect(rect, bg_color)
        
        font_main = option.font
        font_bold = option.font
        font_bold.setBold(True)
        
        fm = QFontMetrics(font_main)
        fm_bold = QFontMetrics(font_bold)

        text_y = rect.top() + self.padding_top + fm.ascent()
        current_x = rect.left() + self.padding_left

        time_str = f"[{item.time}][C:{item.cycle}] "
        painter.setFont(font_main)
        painter.setPen(self.c_time)
        painter.drawText(current_x, text_y, time_str)
        current_x += fm.width(time_str)

        type_label = item.type
        color = self.c_text
        
        if item.type == 'GAIN': 
            color = self.c_gain
            type_label = "[GAIN]"
        elif item.type == 'LOSE': 
            color = self.c_lose
            type_label = "[LOSE]"
        elif item.type == 'SUCCESS': 
            color = self.c_gain
            type_label = "[SUCCESS]"
        elif item.type == 'UPDATE': 
            color = self.c_info
            type_label = "[UPDATE]"
        elif item.type == 'INTENTION': 
            color = self.c_info
            type_label = ""
            
        type_str = f"{type_label} "
        painter.setFont(font_bold)
        painter.setPen(color)
        painter.drawText(current_x, text_y, type_str)
        current_x += fm_bold.width(type_str)

        content_str = item.content
        painter.setFont(font_main)
        painter.setPen(self.c_text)
        
        width_left = rect.right() - current_x - 5 
        if width_left > 0:
            elided_text = fm.elidedText(content_str, Qt.ElideRight, width_left)
            painter.drawText(current_x, text_y, elided_text)

        painter.restore()

    def sizeHint(self, option, index):
        height = option.fontMetrics.height() + (self.padding_top * 2)
        return QSize(option.rect.width(), height)
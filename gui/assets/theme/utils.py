from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor

def apply_shadow(widget, blur_radius=20, offset_x=0, offset_y=5, color="#000000"):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(color))
    shadow.setOffset(offset_x, offset_y)
    widget.setGraphicsEffect(shadow)
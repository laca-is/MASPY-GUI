from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton, QButtonGroup, QLabel
from PyQt5.QtCore import Qt

class SideBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setProperty("class", "sidebar")

        self.setFixedWidth(180)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignTop)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self.buttons = {}
        button_names = ["Menu", "Agents", "Environment", "Messages"]

        for text in button_names:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("class", "sidebar-button")
            
            self.buttons[text] = btn
            layout.addWidget(btn)
            self.button_group.addButton(btn)

        versao = QLabel("ver.2025.12.15")
        versao.setAlignment(Qt.AlignRight)
        versao.setProperty("class", "text-secondary")
        layout.addStretch(1)
        layout.addWidget(versao)

        self.setLayout(layout)
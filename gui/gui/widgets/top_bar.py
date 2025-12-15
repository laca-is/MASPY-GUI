from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon
from pathlib import Path

class TopBar(QWidget):
    settings_button_clicked = pyqtSignal()

    def __init__(self, title="Menu"):
        super().__init__()
        self.setFixedHeight(60)
        self.setProperty("class", "topbar")

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setProperty("class", "topbar-title")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.settings_button = QPushButton()
        self.gui_path = Path(__file__).resolve().parent.parent
        self.settings_button.setIcon(QIcon(f"{self.gui_path}/assets/icons/settings.svg"))
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setFlat(True)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setObjectName("SettingsButton")
        
        self.settings_button.clicked.connect(self.settings_button_clicked)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 0, 20, 0)
        
        main_layout.addWidget(self.title_label)
        main_layout.addStretch()
        main_layout.addWidget(self.settings_button)
        
        self.setLayout(main_layout)

    def set_title(self, title):
        self.title_label.setText(title)
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QPushButton, QComboBox, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal

class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(500)
        
        main_layout = QVBoxLayout(self)
        
        title = QLabel("Interface Settings")
        title.setProperty("class", "h2")
        main_layout.addWidget(title)

        theme_frame = QFrame()
        theme_frame.setFrameShape(QFrame.StyledPanel)
        theme_layout = QVBoxLayout(theme_frame)
        
        theme_title = QLabel("Style")
        theme_title.setProperty("class", "h3")
        theme_layout.addWidget(theme_title)
        
        self.button_group_theme = QButtonGroup(self)
        
        btn_layout = QHBoxLayout()
        self.btn_light = QPushButton("Light")
        self.btn_light.setCheckable(True)
        
        self.btn_dark = QPushButton("Dark")
        self.btn_dark.setCheckable(True)
        self.btn_dark.setChecked(True)
        
        self.button_group_theme.addButton(self.btn_light)
        self.button_group_theme.addButton(self.btn_dark)
        
        btn_layout.addWidget(self.btn_light)
        btn_layout.addWidget(self.btn_dark)
        theme_layout.addLayout(btn_layout)
        
        main_layout.addWidget(theme_frame)

        self.btn_light.clicked.connect(lambda: self.theme_changed.emit("light"))
        self.btn_dark.clicked.connect(lambda: self.theme_changed.emit("dark"))

        lang_frame = QFrame()
        lang_frame.setFrameShape(QFrame.StyledPanel)
        lang_layout = QVBoxLayout(lang_frame)

        lang_title = QLabel("Language")
        lang_title.setProperty("class", "h3")
        lang_layout.addWidget(lang_title)
        
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English")
        self.combo_lang.addItem("Portuguese (not implemented yet)")
        self.combo_lang.setEnabled(False)
        
        lang_layout.addWidget(self.combo_lang)
        main_layout.addWidget(lang_frame)
        
        main_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        main_layout.addWidget(self.close_button, alignment=Qt.AlignRight)
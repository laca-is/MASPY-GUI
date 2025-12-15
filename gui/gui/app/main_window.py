from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QSlider, QLabel, QFrame,
                             QApplication, QLineEdit) 
from gui.widgets.side_bar import SideBar
from gui.widgets.top_bar import TopBar
from gui.views.page_home import MenuInicialPage
from gui.views.page_agents import AgentesPage
from gui.views.page_messages import MensagensPage
from gui.views.page_environment import AmbientePage
from gui.core.log_store import LogStore
from gui.core.data_model import AgentDataModel

from gui.widgets.settings_dialog import SettingsDialog
from gui.assets.theme.styler import load_stylesheet, set_active_theme, current_theme

class InterfaceWindow(QWidget):
    
    timeline_index_changed = pyqtSignal(int)

    def __init__(self, command_queue, num_agents, new_queue):
        super().__init__()
        self.setWindowTitle("MASPY GUI")
        self.setGeometry(100, 100, 1200, 700)
        
        self._current_theme = "dark" 

        self.command_queue = command_queue

        self.log_thread = QThread()
        self.log_store = LogStore(new_queue)
        self.log_store.moveToThread(self.log_thread)
        self.log_thread.started.connect(self.log_store.start_polling)
        self.log_thread.finished.connect(self.log_thread.deleteLater)

        self.data_model = AgentDataModel(self.log_store)

        self._setup_ui()

        self.timeline_index_changed.connect(self.log_store.set_current_timeline_index)
        
        self.timeline_index_changed.connect(self.page_agentes.on_store_updated)
        self.timeline_index_changed.connect(self.page_mensagens.on_store_updated)
        self.timeline_index_changed.connect(self.page_ambiente.on_timeline_state_changed)
        self.timeline_index_changed.connect(self.page_menu.on_store_updated)
        self.timeline_index_changed.connect(self.data_model.on_store_updated)

        self.log_thread.start()
        
        self.settings_dialog = None

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SideBar()
        main_layout.addWidget(self.sidebar)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.topbar = TopBar("Menu")
        self.topbar.settings_button_clicked.connect(self._open_settings)
        right_layout.addWidget(self.topbar)
        
        self.timeline_frame = QFrame()
        self.timeline_frame.setProperty("class", "timeline-frame")
        self.timeline_frame.setMinimumHeight(50)
        self.timeline_frame.setMaximumHeight(50)
        timeline_layout = QHBoxLayout(self.timeline_frame)
        timeline_layout.setContentsMargins(10, 5, 10, 5)
        
        self.timeline_label = QLabel("Time: 00:00:00.000 / 00:00:00.000") 
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(0) 
        
        self.timeline_input = QLineEdit()
        self.timeline_input.setPlaceholderText("Go to(ms)...")
        self.timeline_input.setMinimumWidth(100) 
        self.timeline_input.returnPressed.connect(self._on_timeline_input)
        
        timeline_layout.addWidget(QLabel("Timeline:"))
        timeline_layout.addWidget(self.timeline_slider, stretch=1) 
        timeline_layout.addWidget(self.timeline_input) 
        timeline_layout.addWidget(self.timeline_label)
        
        right_layout.addWidget(self.timeline_frame)

        self.stack = QStackedWidget()
        
        self.page_menu = MenuInicialPage(self.command_queue, self.log_store)
        self.page_agentes = AgentesPage(self.log_store, self.data_model)
        self.page_mensagens = MensagensPage(self.log_store)
        
        self.page_ambiente = AmbientePage(self.log_store)
        self.page_ambiente.setObjectName("page_ambiente") 

        self.stack.addWidget(self.page_menu)
        self.stack.addWidget(self.page_agentes)
        self.stack.addWidget(self.page_ambiente)
        self.stack.addWidget(self.page_mensagens)
        
        right_layout.addWidget(self.stack)
        main_layout.addLayout(right_layout)

        self.log_store.agent_list_updated.connect(self.page_agentes.on_agent_list_updated)
        
        self.log_store.store_updated.connect(self.page_agentes.on_store_updated)
        self.log_store.store_updated.connect(self.page_mensagens.on_store_updated)
        self.log_store.store_updated.connect(self.page_menu.on_store_updated)

        self.log_store.store_updated.connect(self._update_timeline_slider_range)
        self.timeline_slider.valueChanged.connect(self._on_timeline_slider_changed)
        self.timeline_slider.sliderReleased.connect(self._on_timeline_slider_released)
        
        self.sidebar.buttons["Menu"].clicked.connect(lambda: self.show_page(0, "Menu"))
        self.sidebar.buttons["Agents"].clicked.connect(lambda: self.show_page(1, "Agents"))
        self.sidebar.buttons["Environment"].clicked.connect(lambda: self.show_page(2, "Environment"))
        self.sidebar.buttons["Messages"].clicked.connect(lambda: self.show_page(3, "Messages"))

        self.sidebar.buttons["Menu"].setChecked(True)

    def _open_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
            self.settings_dialog.theme_changed.connect(self._apply_theme)
            self.settings_dialog.setAttribute(Qt.WA_DeleteOnClose)
            self.settings_dialog.destroyed.connect(self._on_settings_closed)

        if self._current_theme == 'light':
            self.settings_dialog.btn_light.setChecked(True)
        else:
            self.settings_dialog.btn_dark.setChecked(True)
            
        self.settings_dialog.show()
        self.settings_dialog.activateWindow()

    def _on_settings_closed(self):
        self.settings_dialog = None

    def _apply_theme(self, theme_name):
        if theme_name == self._current_theme:
            return 

        set_active_theme(theme_name)
        self._current_theme = theme_name 

        app_instance = QApplication.instance()
        if app_instance:
            stylesheet = load_stylesheet(theme_name)
            app_instance.setStyleSheet(stylesheet)
        self._propagate_theme_to_pages()

    def _propagate_theme_to_pages(self):
        pages = [
            self.page_menu,
            self.page_agentes,
            self.page_mensagens,
            self.page_ambiente
        ]
        
        for page in pages:
            if hasattr(page, 'update_theme'):
                try:
                    page.update_theme()
                except Exception as e:
                    print(f"[Theme] Erro ao atualizar tema em {page}: {e}")

    def _ms_to_time_str(self, ms_value):
        if ms_value < 0:
            ms_value = 0
            
        total_seconds = ms_value // 1000
        ms = ms_value % 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"
    
    def _on_timeline_input(self):
        try:
            ms_value_str = self.timeline_input.text().strip()
            if not ms_value_str:
                return
                
            ms_value = int(ms_value_str)
            max_val = self.timeline_slider.maximum()
            
            if ms_value < 0:
                ms_value = 0
            elif ms_value > max_val:
                ms_value = max_val
                
            self.timeline_slider.setValue(ms_value)
            
            self.timeline_input.clear()
            self._on_timeline_slider_released()
            
        except ValueError:
            self.timeline_input.clear()
        except Exception as e:
            print(f"Erro em _on_timeline_input: {e}")
            self.timeline_input.clear()

    def _update_timeline_slider_range(self):
        new_max_ms = self.log_store.get_total_duration_ms()
        if new_max_ms == 0: 
            return

        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setMaximum(new_max_ms)

        if self.log_store.is_live:
            self.timeline_slider.setValue(new_max_ms)
            max_time_str = self._ms_to_time_str(new_max_ms)
            self.timeline_label.setText(f"Time: {max_time_str} / {max_time_str}")
        
        self.timeline_slider.blockSignals(False)

    def _on_timeline_slider_changed(self, ms_value):
        max_val_ms = self.timeline_slider.maximum()
        
        index = self.log_store.get_index_from_ms(ms_value)
        self.log_store.set_current_timeline_index(index)
        
        is_live = (ms_value == max_val_ms)
        self.log_store.is_live = is_live 
        
        current_time_str = self._ms_to_time_str(ms_value)
        max_time_str = self._ms_to_time_str(max_val_ms)
        
        self.timeline_label.setText(f"Time: {current_time_str} / {max_time_str}")

    def _on_timeline_slider_released(self):
        index = self.log_store.get_index_from_ms(self.timeline_slider.value())
        self.timeline_index_changed.emit(index)

    def show_page(self, index, title):
        self.stack.setCurrentIndex(index)
        self.topbar.set_title(title)

    def closeEvent(self, event):
        self.log_thread.quit()
        self.log_thread.wait()
        super().closeEvent(event)
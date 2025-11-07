import ast
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, 
    QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt

class EnvironmentDetailWindow(QWidget):
    def __init__(self, env_name, log_store, parent=None):
        super().__init__(parent)
        self.env_name = env_name
        self.log_store = log_store

        self.setWindowTitle(f"Detalhes do Ambiente: {self.env_name}")
        self.setGeometry(200, 200, 500, 600)

        layout = QVBoxLayout(self)
        title = QLabel(f"Monitorando Ambiente: {self.env_name}")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.details_tree = QTreeWidget()
        self.details_tree.setHeaderLabels(['Propriedade', 'Valor'])
        self.details_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(self.details_tree)

        self.log_store.environment_state_updated.connect(self.on_environment_update)

        self.load_initial_data()
        
        self.setAttribute(Qt.WA_DeleteOnClose)

    def load_initial_data(self):
        all_states = self.log_store.get_latest_environment_states()
        initial_data = all_states.get(self.env_name, {})
        if initial_data:
            self.update_details(initial_data)

    def on_environment_update(self, all_envs_data):
        if self.env_name in all_envs_data:
            env_data = all_envs_data[self.env_name]
            self.update_details(env_data)

    def _safe_eval(self, literal):
        try:
            return ast.literal_eval(literal)
        except (ValueError, SyntaxError):
            return literal

    def update_details(self, data):
        self.details_tree.clear()
        self._populate_tree(self.details_tree, data)
        self.details_tree.expandAll()

    def _populate_tree(self, parent, data):
        if isinstance(parent, QTreeWidget):
            parent.clear()
            root_item = parent.invisibleRootItem()
        else:
            root_item = parent

        if isinstance(data, str):
            data = self._safe_eval(data)

        if isinstance(data, dict):
            for key, val in sorted(data.items()):
                key_str = str(self._safe_eval(key))
                child = QTreeWidgetItem([key_str])
                root_item.addChild(child)
                self._populate_tree(child, val)
        elif isinstance(data, (list, set, tuple)):
            for i, val in enumerate(data):
                child = QTreeWidgetItem([f"Item {i}"])
                root_item.addChild(child)
                self._populate_tree(child, val)
        else:
            if not isinstance(parent, QTreeWidget):
                parent.setText(1, str(data))
            else:
                child = QTreeWidgetItem(["Valor", str(data)])
                root_item.addChild(child)
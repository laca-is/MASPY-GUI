from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from gui.assets.theme.theme_dark import theme_colors
from gui.assets.theme.utils import apply_shadow

class AgentCard(QFrame):
    def __init__(self, agent_name, parent=None):
        super().__init__(parent)
        self.agent_name = agent_name

        self.setFrameShape(QFrame.StyledPanel)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)

        title_layout = QHBoxLayout()
        self.name_label = QLabel(f"{self.agent_name}")
        self.name_label.setProperty("class", "card-title-bold")

        self.cycle_label = QLabel("Ciclo: ?")
        self.cycle_label.setProperty("class", "card-metadata")
        
        title_layout.addWidget(self.name_label)
        title_layout.addStretch()
        title_layout.addWidget(self.cycle_label)
        self.layout.addLayout(title_layout)

        stats_layout = QHBoxLayout()
        self.beliefs_label = QLabel("Crenças: 0")
        self.goals_label = QLabel("Objetivos: 0")
        stats_layout.addWidget(self.beliefs_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.goals_label)
        self.layout.addLayout(stats_layout)

        action_title = QLabel("Ação Atual:")
        self.action_label = QLabel("Inicializando")
        self.action_label.setWordWrap(True)
        self.layout.addWidget(action_title)
        self.layout.addWidget(self.action_label)

        self.details_button = QPushButton("Ver Detalhes")
        self.details_button.setCursor(Qt.PointingHandCursor)
        self.details_button.setProperty("class", "primary")

        self.layout.addWidget(self.details_button)
        apply_shadow(self, blur_radius=15, offset_y=2)

    def update_belief_goal_counts(self, state_data):
        num_beliefs = len(state_data.get('beliefs', []))
        num_goals = len(state_data.get('goals', []))
        self.beliefs_label.setText(f"Crenças: {num_beliefs}")
        self.goals_label.setText(f"Objetivos: {num_goals}")
    def update_cycle(self, cycle_count):
        self.cycle_label.setText(f"Ciclo: {cycle_count}")
    def update_action(self, action_str):
        self.action_label.setText(f"<b>{action_str}</b>")
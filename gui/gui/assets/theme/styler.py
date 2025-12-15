from gui.assets.theme.theme_dark import theme_colors as theme_dark
from gui.assets.theme.theme_light import theme_colors as theme_light
from pathlib import Path

current_theme = theme_dark.copy()

def set_active_theme(mode="dark"):
    current_theme.clear()
    
    if mode == "light":
        current_theme.update(theme_light)
    else:
        current_theme.update(theme_dark)

def load_stylesheet(theme_name="dark"):
    try:
        current_script_dir = Path(__file__).resolve().parent.parent
        with open(f'{current_script_dir}/styles/theme.qss', 'r', encoding='utf-8') as f:
            stylesheet = f.read()

        target_theme = theme_light if theme_name == "light" else theme_dark
            
        for color_name, color_value in target_theme.items():
            placeholder = f"{{{color_name}}}"
            stylesheet = stylesheet.replace(placeholder, color_value)
        
        return stylesheet
    except Exception as e:
        print(f"Erro style: {e}")
        return ""
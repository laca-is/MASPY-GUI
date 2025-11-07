from gui.assets.theme.theme_dark import theme_colors as theme_dark
from gui.assets.theme.theme_light import theme_colors as theme_light

def load_stylesheet(theme_name="dark"):
    try:
        with open('gui/assets/styles/theme.qss', 'r', encoding='utf-8') as f:
            stylesheet = f.read()

        if theme_name == "light":
            theme_colors = theme_light
        else:
            theme_colors = theme_dark
            
        for color_name, color_value in theme_colors.items():
            placeholder = f"{{{color_name}}}"
            stylesheet = stylesheet.replace(placeholder, color_value)
        
        return stylesheet
    
    except FileNotFoundError:
        print("Aviso: Arquivo 'gui/assets/styles/theme.qss' não encontrado. A aplicação rodará sem estilo customizado.")
        return ""
    except Exception as e:
        print(f"Erro ao processar a folha de estilo: {e}")
        return ""
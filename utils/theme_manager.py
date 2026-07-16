THEME_COLORS = {
    "cyberpunk": {
        "accent": "#FF007F",
        "secondary": "#00F5FF",
        "bg_start": "#080810",
        "card": "#0f0f1b",
        "border": "#FF007F",
        "text": "#FFFFFF"
    },
    "blue": {
        "accent": "#0099FF",
        "secondary": "#00F5FF",
        "bg_start": "#050B1A",
        "card": "#0E1A30",
        "border": "#0099FF",
        "text": "#E0EEFF"
    },
    "tesla": {
        "accent": "#E82127",
        "secondary": "#A0A0A0",
        "bg_start": "#151515",
        "card": "#202020",
        "border": "#E82127",
        "text": "#EAEAEA"
    },
    "ferrari": {
        "accent": "#FF2800",
        "secondary": "#FFF200",
        "bg_start": "#0C0C0C",
        "card": "#181818",
        "border": "#FF2800",
        "text": "#FFFFFF"
    },
    "minimal": {
        "accent": "#FFFFFF",
        "secondary": "#555555",
        "bg_start": "#0F0F12",
        "card": "#1A1A20",
        "border": "#555555",
        "text": "#D0D0D5"
    },
    "glass": {
        "accent": "#8BE9FD",
        "secondary": "#F8F8F2",
        "bg_start": "#050515",
        "card": "#121230",
        "border": "#8BE9FD",
        "text": "#EEEEFF"
    },
    "night": {
        "accent": "#F5E050",
        "secondary": "#1E272C",
        "bg_start": "#050A10",
        "card": "#0D1620",
        "border": "#F5E050",
        "text": "#E0E6ED"
    },
    "rain": {
        "accent": "#4A90E2",
        "secondary": "#333333",
        "bg_start": "#030914",
        "card": "#0B132B",
        "border": "#4A90E2",
        "text": "#A5B1C2"
    },
    "neon": {
        "accent": "#39FF14",
        "secondary": "#8A2BE2",
        "bg_start": "#020205",
        "card": "#0D0D15",
        "border": "#39FF14",
        "text": "#E2E2F0"
    },
    "future": {
        "accent": "#00D2FF",
        "secondary": "#FFFFFF",
        "bg_start": "#000000",
        "card": "#0E1B29",
        "border": "#00D2FF",
        "text": "#A9C2F0"
    }
}

def get_theme_colors(theme_name: str) -> dict:
    return THEME_COLORS.get(theme_name, THEME_COLORS["cyberpunk"])

import os
import json
from typing import Dict, Any

CONFIG_FILE = "config.json"

def load_config() -> Dict[str, Any]:
    """Charge la configuration depuis le fichier config.json ou crée une configuration par défaut"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement de la configuration: {str(e)}")
    
    # Configuration par défaut
    default_config = {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "max_pages": 10,
        "chunk_size": 500,
        "max_concurrent": 5,
        "search_threshold": 0.4
    }
    
    # Sauvegarder la configuration par défaut
    save_config(default_config)
    
    return default_config

def save_config(config: Dict[str, Any]) -> bool:
    """Sauvegarde la configuration dans le fichier config.json"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
        return False

def update_config(key: str, value: Any) -> bool:
    """Met à jour une clé spécifique dans la configuration"""
    config = load_config()
    config[key] = value
    return save_config(config)
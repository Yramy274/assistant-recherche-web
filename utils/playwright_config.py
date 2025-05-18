import os
import sys
import subprocess
import logging

def ensure_playwright_browsers():
    """Vérifie et installe les navigateurs Playwright si nécessaires"""
    try:
        logging.info("Vérification de l'installation des navigateurs Playwright...")
        # Vérifier si les navigateurs sont déjà installés
        chrome_path = os.path.expanduser("~/.cache/ms-playwright/chromium-1097/chrome-linux/chrome")
        if not os.path.exists(chrome_path):
            logging.info("Installation des navigateurs Playwright...")
            # Installer les navigateurs
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                          check=True, capture_output=True)
            logging.info("Installation réussie des navigateurs Playwright")
        else:
            logging.info("Les navigateurs Playwright sont déjà installés")
        return True
    except Exception as e:
        logging.error(f"Erreur lors de l'installation des navigateurs Playwright: {str(e)}")
        return False

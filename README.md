# Assistant de Recherche Web

Un assistant de recherche intelligent basé sur l'IA qui permet de chercher et d'analyser des informations sur le web en utilisant des techniques avancées de traitement du langage naturel et de stockage vectoriel.

## 🚀 Fonctionnalités

- 🔍 Recherche et extraction de contenu web avancée
- 🧠 Stockage et indexation vectorielle avec ChromaDB
- 🤖 Réponses précises basées sur des sources fiables
- 🎨 Interface utilisateur Streamlit moderne et intuitive
- ⚙️ Configuration personnalisable via fichier JSON
- 🚀 Déploiement facile avec Docker ou Streamlit Cloud

## 📋 Prérequis

- Python 3.9+
- Compte OpenAI avec clé API valide
- Git pour la gestion de version
- Navigateurs web pour Playwright (installés automatiquement)

## 🛠 Installation Locale

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Yramy274/assistant-recherche-web.git
   cd assistant-recherche-web
   ```

2. **Créer et activer un environnement virtuel** :
   ```bash
   # Créer l'environnement
   python -m venv venv
   
   # Activer l'environnement
   # Sur Windows :
   .\venv\Scripts\activate
   # Sur macOS/Linux :
   # source venv/bin/activate
   ```

3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

4. **Installer Playwright** :
   ```bash
   python -m playwright install
   python -m playwright install-deps
   ```

5. **Configuration** :
   - Créez un fichier `.env` à la racine du projet
   - Ajoutez votre clé API OpenAI :
     ```env
     OPENAI_API_KEY=votre_cle_api_ici
     ```

## 🚀 Démarrage Rapide

```bash
# Activer l'environnement virtuel
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Lancer l'application
streamlit run app.py
```

## ☁️ Déploiement sur Streamlit Cloud

1. Créez un compte sur [Streamlit Cloud](https://streamlit.io/cloud)
2. Connectez votre compte GitHub
3. Cliquez sur "New App"
4. Sélectionnez votre dépôt et la branche
5. Spécifiez le fichier principal : `app.py`
6. Ajoutez votre clé API OpenAI dans les paramètres avancés
7. Cliquez sur "Deploy"

## 🐳 Déploiement avec Docker

```bash
# Construire l'image
docker build -t assistant-recherche .

# Lancer le conteneur
docker run -p 8501:8501 -e OPENAI_API_KEY=votre_cle_api_ici assistant-recherche
```

## 🏗 Structure du Projet

```
assistant-recherche-web/
├── app.py                    # Application Streamlit principale
├── modules/
│   ├── __init__.py
│   ├── scraper.py            # Module de scraping web avancé
│   └── vector_store.py       # Module RAG avec ChromaDB
├── utils/
│   ├── __init__.py
│   └── config.py             # Gestion de configuration
├── .env.example              # Exemple de configuration
├── requirements.txt          # Dépendances Python
├── Dockerfile               # Configuration Docker
└── README.md                # Ce fichier
```

## ⚙️ Configuration

Le fichier `config.json` est automatiquement généré au premier lancement. Vous pouvez le modifier pour personnaliser :
- Paramètres de recherche
- Comportement du chatbot
- Paramètres d'indexation

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👨‍💻 Auteur

**Yassine Ramy**  
[GitHub](https://github.com/Yramy274)  
Email: yassineramy01@gmail.com

## 🙌 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

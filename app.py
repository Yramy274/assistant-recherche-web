import os
import streamlit as st
from dotenv import load_dotenv
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)

# Importer les modules personnalisés
from modules.scraper import WebScraper
from modules.vector_store import VectorStore
from utils.config import load_config, save_config
from utils.playwright_config import ensure_playwright_browsers

# S'assurer que les navigateurs Playwright sont installés
ensure_playwright_browsers()

# Charger la configuration
load_dotenv()
config = load_config()

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant de Recherche Web",
    page_icon="🔍",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5em;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5em;
    }
    .subtitle {
        color: #666;
        text-align: center;
        margin-bottom: 2em;
    }
    .success-msg {
        color: #4CAF50;
        font-weight: bold;
    }
    .error-msg {
        color: #F44336;
    }
    .query-box {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de l'état de session
def init_session_state():
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = None
    if 'scraper' not in st.session_state:
        st.session_state.scraper = WebScraper(max_concurrent=5, chunk_size=500)
    if 'collection_name' not in st.session_state:
        st.session_state.collection_name = None
    if 'scrape_progress' not in st.session_state:
        st.session_state.scrape_progress = 0
    if 'scrape_status' not in st.session_state:
        st.session_state.scrape_status = ""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []

init_session_state()

# Fonction pour scraper un site et charger dans le vector store
def scrape_and_load(url: str, max_pages: int) -> Dict[str, Any]:
    print(f"\n=== DÉBUT DU SCRAPING ===")
    print(f"URL: {url}")
    print(f"Max pages: {max_pages}")
    
    try:
        # Mettre à jour l'état du scraping
        st.session_state.scrape_status = "Démarrage du scraping..."
        st.session_state.scrape_progress = 5
        print("État de la session mis à jour")
        
        # Récupérer les données
        print("Appel de scrape_website...")
        result = st.session_state.scraper.scrape_website(url, max_pages=max_pages)
        print("Scraping terminé, résultat:", bool(result))
        
        if not result or result.get('total_pages', 0) == 0:
            print("Aucune page trouvée ou erreur lors du scraping")
            st.session_state.scrape_status = "Échec : aucune page trouvée"
            st.session_state.scrape_progress = 0
            return None
            
        st.session_state.scrape_status = f"Scraping terminé. Création de la base vectorielle..."
        st.session_state.scrape_progress = 60
            
        # Créer un nom de collection unique basé sur l'URL
        from datetime import datetime
        domain = url.split('//')[-1].split('/')[0].replace('.', '_')
        st.session_state.collection_name = f"{domain}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
        # Initialiser le vector store
        vector_store = VectorStore(
            collection_name=st.session_state.collection_name,
            api_key=st.session_state.openai_api_key if 'openai_api_key' in st.session_state else None
        )
        
        # Charger directement les données (sans passer par un fichier JSON)
        vector_store.load_from_dict(result)
        
        st.session_state.vector_store = vector_store
        st.session_state.scrape_status = "Terminé avec succès!"
        st.session_state.scrape_progress = 100
        print("=== SCRAPING RÉUSSI ===")
        return result
    except Exception as e:
        error_msg = f"Erreur: {str(e)}"
        print(f"=== ERREUR: {error_msg}")
        import traceback
        traceback.print_exc()
        st.session_state.scrape_status = error_msg
        st.session_state.scrape_progress = 0
        return None

# Sidebar pour la configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("---")
    
    # Champ pour la clé API OpenAI
    openai_api_key = st.text_input(
        "Clé API OpenAI", 
        type="password",
        placeholder="sk-...",
        help="Entrez votre clé API OpenAI pour utiliser l'application"
    )
    
    # Enregistrer la clé dans une variable de session
    if openai_api_key:
        st.session_state.openai_api_key = openai_api_key
        os.environ["OPENAI_API_KEY"] = openai_api_key
        st.success("✅ Clé API enregistrée")
    
    # Section Scraping
    st.subheader("Scraping de site web")
    
    # Champ pour l'URL à scraper
    url = st.text_input("URL du site web à analyser", 
                       placeholder="https://exemple.com")
    
    # Option pour le nombre de pages
    scrape_option = st.radio(
        "Nombre de pages à analyser",
        ["Définir un nombre limité", "Analyser toutes les pages"],
        index=0
    )
    
    # Si l'utilisateur choisit un nombre limité, afficher le sélecteur
    if scrape_option == "Définir un nombre limité":
        max_pages = st.number_input("Nombre maximum de pages", 
                          min_value=1, max_value=200, value=10)
    else:
        max_pages = 200  # Une valeur élevée qui sera considérée comme "toutes les pages"
        st.info("⚠️ L'analyse de toutes les pages peut prendre beaucoup de temps.")
    
    # Bouton pour lancer le scraping
    if st.button("🔍 Lancer le scraping", use_container_width=True):
        if not url:
            st.error("Veuillez entrer une URL valide")
        elif 'openai_api_key' not in st.session_state and not os.getenv("OPENAI_API_KEY"):
            st.error("Veuillez entrer une clé API OpenAI valide")
        else:
            action_text = "complet du site" if scrape_option == "Analyser toutes les pages" else f"de {max_pages} pages"
            with st.spinner(f"Scraping {action_text} en cours..."):
                result = scrape_and_load(url, max_pages)
                if result:
                    st.success(f"Scraping et indexation terminés avec succès! {result['total_pages']} pages analysées.")
    
    # Afficher la progression du scraping
    if st.session_state.scrape_progress > 0:
        st.progress(st.session_state.scrape_progress)
        st.text(st.session_state.scrape_status)
    
    st.markdown("---")
    
    # Section avancée (cachée par défaut)
    with st.expander("⚙️ Options avancées"):
        if st.session_state.vector_store is not None:
            if st.button("Supprimer la collection actuelle"):
                if st.session_state.vector_store:
                    st.session_state.vector_store.delete_collection()
                    st.session_state.vector_store = None
                    st.session_state.collection_name = None
                    st.success("Collection supprimée avec succès!")
        
        # Option pour effacer l'historique de recherche
        if st.session_state.search_history and st.button("Effacer l'historique de recherche"):
            st.session_state.search_history = []
            st.success("Historique effacé!")

# Contenu principal
st.markdown("<h1 class='main-title'>🔍 Assistant de Recherche Web</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Posez des questions sur le contenu de n'importe quel site web</p>", 
            unsafe_allow_html=True)

# Affichage principal
if st.session_state.vector_store is not None:
    st.success("✅ Site web indexé ! Vous pouvez maintenant poser des questions.")
    
    # Afficher les informations sur les données chargées
    with st.expander("📊 Informations sur le site indexé"):
        info = st.session_state.vector_store.get_collection_info()
        st.json({
            "Nom de la collection": info.get("name", "Inconnu"),
            "Nombre de documents": info.get("count", 0),
            "Statut": "Actif"
        })
    
    # Zone de question
    st.markdown("### ❓ Posez votre question")
    question = st.text_area("", placeholder="Posez votre question ici...", height=100)
    
    # Options de recherche
    col1, col2 = st.columns(2)
    with col1:
        n_results = st.slider("Nombre de résultats à afficher", 1, 10, 3)
    with col2:
        threshold = st.slider("Seuil de pertinence", 0.0, 1.0, 0.4, 0.05)
    
    # Bouton de recherche
    if st.button("🔍 Rechercher", type="primary", use_container_width=True):
        if question.strip():
            with st.spinner("Recherche en cours..."):
                try:
                    # Effectuer la recherche
                    response = st.session_state.vector_store.rag_query(
                        question, 
                        n_results=n_results,
                        threshold=threshold
                    )
                    
                    # Ajouter à l'historique
                    st.session_state.search_history.append({
                        "question": question,
                        "answer": response["answer"],
                        "sources": response["sources"]
                    })
                    
                    # Afficher la réponse
                    st.markdown("### 📝 Réponse")
                    st.markdown(response["answer"])
                    
                    # Afficher les sources
                    if response.get("sources"):
                        st.markdown("### 📚 Sources")
                        for i, source in enumerate(response["sources"][:3], 1):  # Limiter à 3 sources
                            with st.expander(f"Source {i}: {source.get('title', 'Sans titre')}"):
                                st.write(f"**URL:** {source.get('url', 'N/A')}")
                                st.write(f"**Pertinence:** {source.get('similarity', 0)*100:.1f}%")
                                
                                # Afficher un extrait du contenu
                                if source.get('content'):
                                    content = source['content']
                                    if len(content) > 300:
                                        content = content[:300] + "..."
                                    st.write("**Extrait:**", content)
                    
                    # Ajouter système de feedback
                    st.markdown("### 📝 Cette réponse vous a-t-elle été utile ?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("👍 Oui", type="primary"):
                            st.success("Merci pour votre retour positif !")
                    with col2:
                        if st.button("👎 Non"):
                            feedback = st.text_area("Qu'est-ce qui pourrait être amélioré ?")
                            if st.button("Envoyer"):
                                st.success("Merci pour votre retour !")
                    
                except Exception as e:
                    st.error(f"Une erreur est survenue : {str(e)}")
        else:
            st.warning("Veuillez entrer une question")
    
    # Afficher l'historique de recherche
    if st.session_state.search_history:
        with st.expander("📜 Historique de recherche"):
            for i, item in enumerate(reversed(st.session_state.search_history), 1):
                st.markdown(f"**Question {i}:** {item['question']}")
                st.markdown(f"**Réponse:** {item['answer'][:150]}...")
                st.markdown("---")

else:
    # Afficher les instructions
    st.info("""
    ### Comment utiliser cet outil :
    1. Entrez votre clé API OpenAI dans la barre latérale
    2. Entrez l'URL du site web que vous souhaitez analyser
    3. Choisissez le nombre de pages à analyser
    4. Cliquez sur "Lancer le scraping"
    5. Une fois le scraping terminé, posez vos questions dans la zone prévue
    
    💡 Conseil : Commencez par un petit site web pour tester l'outil.
    """)

# Pied de page
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; margin-top: 2em;'>
        <p>Assistant de Recherche Web - Utilise l'IA pour analyser le contenu des sites web</p>
        <p>Développé avec ❤️ et Streamlit</p>
    </div>
""", unsafe_allow_html=True)
import asyncio
from playwright.async_api import async_playwright
import requests
import xmltodict
import re
from datetime import datetime
import logging
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class WebScraper:
    def __init__(self, max_concurrent=5, chunk_size=500):
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        
    def scrape_website(self, url: str, max_pages: int = 50) -> Dict[str, Any]:
        """Point d'entrée principal pour scraper un site web"""
        try:
            logging.info(f"Début du scraping de {url} (max {max_pages} pages)")
            
            # Normaliser l'URL
            if not url.startswith('http'):
                url = 'https://' + url
                
            # Extraire le nom de domaine
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            domain_name = parsed_url.netloc.replace('www.', '')
            
            logging.info(f"Initialisation du scraper pour {base_url}")
            
            # Créer et exécuter le scraper
            scraper = SiteContentScraper(
                base_url=base_url, 
                max_concurrent=self.max_concurrent, 
                chunk_size=self.chunk_size
            )
            
            # Exécuter le scraping de manière synchrone en appelant la fonction asynchrone
            logging.info("Création de la boucle d'événements")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logging.info("Démarrage du scraping asynchrone")
                result = loop.run_until_complete(scraper.scrape_all_pages(max_pages))
            except Exception as e:
                logging.error(f"Erreur lors du scraping: {str(e)}", exc_info=True)
                raise
            finally:
                logging.info("Nettoyage de la boucle d'événements")
                loop.close()
            
            if result is None:
                logging.warning("Aucun résultat n'a été retourné par le scraper")
                return {
                    "domain": base_url,
                    "domain_name": domain_name,
                    "total_pages": 0,
                    "timestamp": datetime.now().isoformat(),
                    "total_chunks": 0,
                    "pages": []
                }
            
            logging.info(f"Scraping terminé avec succès: {len(result.get('pages', []))} pages trouvées")
            return result
            
        except Exception as e:
            logging.error(f"Erreur critique dans scrape_website: {str(e)}", exc_info=True)
            raise

class SiteContentScraper:
    def __init__(self, base_url=None, max_concurrent=5, chunk_size=500):
        self.base_url = base_url
        self.pages = []
        self.sitemap_url = f"{self.base_url}/sitemap.xml"
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        parsed_url = urlparse(self.base_url)
        self.domain_name = parsed_url.netloc.replace('www.', '')
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Définir une fonction de callback pour reporter la progression"""
        self.progress_callback = callback

    def report_progress(self, status: str, progress: float):
        """Reporter la progression si un callback est défini"""
        if self.progress_callback:
            self.progress_callback(status, progress)
        logging.info(f"Progression: {progress:.1f}% - {status}")

    async def fetch_sitemap(self, max_pages=50):
        """Récupère le sitemap et extrait les URLs des pages"""
        try:
            self.report_progress("Recherche du sitemap...", 5)
            logging.info(f"Récupération du sitemap depuis {self.sitemap_url}")
            response = requests.get(self.sitemap_url, timeout=10)
            if response.status_code == 200:
                # Nettoyer le contenu XML
                content = response.content.decode('utf-8')
                if '?>' in content:
                    content = content.split('?>', 1)[1]
                
                try:
                    sitemap = xmltodict.parse(content)
                    
                    # Si c'est un sitemap index, récupérer tous les sous-sitemaps
                    if 'sitemapindex' in sitemap:
                        self.report_progress("Traitement des sous-sitemaps...", 10)
                        for sitemap_entry in sitemap['sitemapindex']['sitemap']:
                            loc = sitemap_entry['loc']
                            try:
                                sub_response = requests.get(loc, timeout=10)
                                if sub_response.status_code == 200:
                                    sub_content = sub_response.content.decode('utf-8')
                                    if '?>' in sub_content:
                                        sub_content = sub_content.split('?>', 1)[1]
                                    
                                    sub_sitemap = xmltodict.parse(sub_content)
                                    
                                    # S'assurer que la structure attendue existe
                                    if 'urlset' in sub_sitemap and 'url' in sub_sitemap['urlset']:
                                        urls = sub_sitemap['urlset']['url']
                                        # Gérer le cas où il n'y a qu'une seule URL
                                        if not isinstance(urls, list):
                                            urls = [urls]
                                            
                                        for url in urls:
                                            loc = url['loc']
                                            if loc.startswith(self.base_url) and loc not in self.pages:
                                                self.pages.append(loc)
                                                if len(self.pages) >= max_pages:
                                                    break
                            except Exception as e:
                                logging.error(f"Erreur lors du traitement du sous-sitemap {loc}: {str(e)}")
                        
                        logging.info(f"Trouvé {len(self.pages)} pages dans tous les sitemaps")
                        self.report_progress(f"Trouvé {len(self.pages)} pages", 15)
                        return len(self.pages) > 0
                    else:
                        # Si c'est un sitemap normal, traiter directement
                        self.report_progress("Traitement du sitemap principal...", 10)
                        if 'urlset' in sitemap and 'url' in sitemap['urlset']:
                            urls = sitemap['urlset']['url']
                            # Gérer le cas où il n'y a qu'une seule URL
                            if not isinstance(urls, list):
                                urls = [urls]
                                
                            for url in urls:
                                loc = url['loc']
                                if loc.startswith(self.base_url) and loc not in self.pages:
                                    self.pages.append(loc)
                                    if len(self.pages) >= max_pages:
                                        break
                            
                            logging.info(f"Trouvé {len(self.pages)} pages dans le sitemap")
                            self.report_progress(f"Trouvé {len(self.pages)} pages", 15)
                            return len(self.pages) > 0
                except Exception as e:
                    logging.error(f"Erreur lors du parsing du sitemap: {str(e)}")
                    self.report_progress("Erreur avec le sitemap, tentative de crawling...", 5)
                    return await self.discover_pages_via_crawling(self.base_url, max_pages)
                    
            else:
                logging.warning(f"Pas de sitemap trouvé ({response.status_code}). Tentative de découverte par crawling...")
                self.report_progress("Pas de sitemap, tentative de crawling...", 5)
                return await self.discover_pages_via_crawling(self.base_url, max_pages)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du sitemap: {str(e)}")
            logging.info("Tentative de découverte par crawling...")
            self.report_progress("Erreur, tentative de crawling...", 5)
            return await self.discover_pages_via_crawling(self.base_url, max_pages)
            
    async def discover_pages_via_crawling(self, start_url, max_pages=50):
        """Découvre les pages en suivant les liens quand il n'y a pas de sitemap"""
        logging.info(f"Démarrage de la découverte via crawling depuis {start_url}")
        self.report_progress("Découverte de pages par crawling...", 10)
        self.pages = [start_url]
        visited = set([start_url])
        to_visit = [start_url]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            page_count = 0
            while to_visit and len(visited) < max_pages:
                current_url = to_visit.pop(0)
                page_count += 1
                
                # Mise à jour de la progression
                progress_percent = min(10 + (page_count / max_pages) * 30, 40)
                self.report_progress(f"Exploration de la page {page_count}/{max_pages}...", progress_percent)
                
                try:
                    logging.info(f"Visite de la page pour découverte: {current_url}")
                    await page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Extraire tous les liens de la page
                    links = await page.evaluate("""
                        () => {
                            return Array.from(document.querySelectorAll('a[href]'))
                                .map(a => a.href)
                                .filter(href => 
                                    href.startsWith(window.location.origin) && 
                                    !href.includes('#') && 
                                    !href.match(/\.(jpg|jpeg|png|gif|css|js|pdf|zip|tar)$/i)
                                );
                        }
                    """)
                    
                    # Ajouter les nouveaux liens à la liste à visiter
                    for link in links:
                        if link not in visited and link.startswith(self.base_url):
                            visited.add(link)
                            to_visit.append(link)
                            self.pages.append(link)
                            if len(self.pages) >= max_pages:
                                break
                except Exception as e:
                    logging.error(f"Erreur lors de la découverte sur {current_url}: {str(e)}")
            
            await browser.close()
            
        logging.info(f"Découverte terminée: {len(self.pages)} pages trouvées")
        self.report_progress(f"Découverte terminée: {len(self.pages)} pages trouvées", 40)
        return len(self.pages) > 0

    def chunk_text(self, text):
        """Découpe le texte en chunks de taille appropriée pour le RAG"""
        if not text:
            return []
        
        # Nettoyer le texte (retirer espaces multiples)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Diviser par paragraphes
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si le paragraphe est très long, le diviser en phrases
            if len(paragraph) > self.chunk_size * 2:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= self.chunk_size:
                        current_chunk += " " + sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
            # Sinon traiter le paragraphe entier
            elif len(current_chunk) + len(paragraph) <= self.chunk_size:
                current_chunk += " " + paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
        
        # Ajouter le dernier chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    async def scrape_page(self, url, index, total):
        """Scrape une page spécifique avec extraction optimisée pour RAG"""
        progress = 40 + (index / total) * 20
        self.report_progress(f"Scraping de la page {index+1}/{total}: {url}", progress)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                logging.info(f"Scraping de la page: {url}")
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=30000)
                
                # Récupérer le titre
                title = await page.title()
                
                # Récupérer le contenu principal en évitant les menus, footers, etc.
                content = await page.evaluate("""
                    () => {
                        // Fonction pour détecter le contenu principal
                        function getMainContent() {
                            // Essayer de trouver le contenu principal par les balises sémantiques
                            const main = document.querySelector('main, article, [role="main"], .content, #content');
                            if (main) return main.innerText;
                            
                            // Sinon, exclure les parties communes de navigation
                            const body = document.body;
                            const elements = Array.from(body.querySelectorAll('nav, header, footer, aside, .menu, .sidebar, .navigation, #header, #footer, #menu, #nav'));
                            
                            // Supprimer temporairement ces éléments pour extraire le contenu
                            elements.forEach(el => {
                                if (el) el.style.display = 'none';
                            });
                            const content = body.innerText;
                            elements.forEach(el => {
                                if (el) el.style.display = '';
                            });
                            
                            return content;
                        }
                        
                        return getMainContent();
                    }
                """)
                
                # Si le contenu est vide, essayer une méthode alternative
                if not content or len(content.strip()) < 50:
                    content = await page.evaluate("""
                        () => {
                            // Récupérer tous les paragraphes
                            const paragraphs = Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li'));
                            return paragraphs.map(p => p.innerText).join('\\n\\n');
                        }
                    """)
                
                # Extraire les métadonnées
                metadata = await page.evaluate("""
                    () => {
                        const metadata = {};
                        // Récupérer les métadonnées des balises meta
                        const metaTags = document.querySelectorAll('meta');
                        metaTags.forEach(meta => {
                            const name = meta.getAttribute('name') || meta.getAttribute('property');
                            const content = meta.getAttribute('content');
                            if (name && content) {
                                if (['description', 'keywords', 'author'].includes(name) ||
                                    name.startsWith('og:') || name.startsWith('twitter:')) {
                                    metadata[name] = content;
                                }
                            }
                        });
                        return metadata;
                    }
                """)
                
                # Fermer le navigateur
                await browser.close()
                
                # Découper le contenu en chunks pour le RAG
                chunks = self.chunk_text(content)
                
                # Préparer les données structurées pour le RAG
                result = {
                    'url': url,
                    'title': title,
                    'content': content,
                    'chunks': chunks,
                    'chunk_count': len(chunks),
                    'metadata': {
                        'source': self.domain_name,
                        'last_modified': datetime.now().isoformat(),
                        'language': 'fr',  # Par défaut en français, à adapter si besoin
                        **metadata
                    }
                }
                
                logging.info(f"Scraping réussi pour {url}: {len(chunks)} chunks extraits")
                return result
                
            except Exception as e:
                logging.error(f"Erreur lors du scraping de {url}: {str(e)}")
                await browser.close()
                return None

    async def scrape_all_pages(self, max_pages=50):
        """Scrape toutes les pages et retourne les données structurées"""
        self.report_progress("Démarrage du processus de scraping...", 0)
        
        if not await self.fetch_sitemap(max_pages):
            logging.error(f"Impossible de trouver des pages à scraper pour {self.base_url}")
            self.report_progress("Échec: aucune page trouvée", 0)
            return None
        
        # Limiter le nombre de pages à scraper
        if len(self.pages) > max_pages:
            self.pages = self.pages[:max_pages]
            logging.info(f"Limitation à {max_pages} pages")
        
        self.report_progress(f"Préparation du scraping de {len(self.pages)} pages...", 40)

        # Semaphore pour limiter le nombre de requêtes concurrentes
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_scrape(url, index, total):
            async with semaphore:
                return await self.scrape_page(url, index, total)
        
        # Lancer toutes les tâches en parallèle
        tasks = [bounded_scrape(url, i, len(self.pages)) for i, url in enumerate(self.pages)]
        all_results = await asyncio.gather(*tasks)
        
        # Filtrer les résultats réussis
        successful_results = [result for result in all_results if result]
        
        self.report_progress("Assemblage des données...", 90)
        
        # Créer un JSON unique avec tous les résultats
        master_json = {
            'domain': self.base_url,
            'domain_name': self.domain_name,
            'total_pages': len(successful_results),
            'timestamp': datetime.now().isoformat(),
            'total_chunks': sum(page['chunk_count'] for page in successful_results),
            'pages': successful_results
        }
        
        logging.info(f"Scraping terminé: {len(successful_results)} pages traitées avec succès")
        self.report_progress(f"Scraping terminé: {len(successful_results)} pages traitées", 100)
        
        return master_json

# Pour tester le scraper individuellement
if __name__ == "__main__":
    scraper = WebScraper(max_concurrent=5)
    import sys
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Entrez l'URL du site à scraper: ")
        
    max_pages = 10
    print(f"Scraping de {url} (max {max_pages} pages)...")
    result = scraper.scrape_website(url, max_pages=max_pages)
    print(f"Scraping terminé: {result['total_pages']} pages, {result['total_chunks']} chunks")
    
    # Afficher les titres des pages scrapées
    for i, page in enumerate(result['pages']):
        print(f"{i+1}. {page['title']} ({page['chunk_count']} chunks)")
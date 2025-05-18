import os
import json
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from typing import List, Dict, Any, Optional
import tiktoken
import logging
import httpx

# Ajout de l'adaptateur pour ChromaDB ≥ 0.4.16
class EmbeddingFunctionAdapter:
    def __init__(self, embedding_function):
        self.embedding_function = embedding_function
    
    def __call__(self, input):
        # Convertit 'input' en 'texts' pour l'ancienne interface
        return self.embedding_function(texts=input)

class VectorStore:
    def __init__(self, collection_name: str = "web_docs", api_key: str = None):
        # Initialiser le client OpenAI
        openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("La clé API OpenAI n'est pas définie")
        
        # Configuration du logger
        self.logger = logging.getLogger(__name__)
        
        # Initialisation du client OpenAI avec gestion des proxies
        print("Initialisation du client OpenAI...")
        try:
            # Créer un client HTTP personnalisé avec proxies=None explicitement
            transport = httpx.HTTPTransport(proxy=None)
            http_client = httpx.Client(transport=transport)
            
            # Utiliser ce client HTTP personnalisé avec OpenAI
            self.openai_client = OpenAI(
                api_key=openai_api_key,
                http_client=http_client
            )
            print("Client OpenAI initialisé avec succès")
            
            # Initialiser ChromaDB
            print("Initialisation de ChromaDB...")
            self.chroma_client = chromadb.PersistentClient(path="/app/chroma_db")
            print("Client ChromaDB initialisé avec succès")
            
            # Créer un client HTTP personnalisé pour les embeddings
            transport_embed = httpx.HTTPTransport(proxy=None)
            http_client_embed = httpx.Client(transport=transport_embed)
            
            # Définir une fonction d'embedding personnalisée pour contourner le problème de proxy
            class CustomOpenAIEmbedding:
                def __init__(self, api_key, model_name):
                    self.client = OpenAI(
                        api_key=api_key,
                        http_client=http_client_embed
                    )
                    self.model_name = model_name
                
                def __call__(self, texts):
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=texts
                    )
                    return [item.embedding for item in response.data]
            
            # Utiliser notre fonction d'embedding personnalisée avec le modèle amélioré
            self.openai_ef = CustomOpenAIEmbedding(
                api_key=openai_api_key,
                model_name="text-embedding-3-large"
            )
            
            # Créer l'adaptateur pour rendre compatible avec ChromaDB ≥ 0.4.16
            self.embedding_adapter = EmbeddingFunctionAdapter(self.openai_ef)
            
            # Créer ou récupérer la collection avec l'adaptateur
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_adapter
            )
            
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
        except Exception as e:
            error_msg = f"Erreur lors de l'initialisation: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
            raise Exception(error_msg) from e

    def load_from_dict(self, data: Dict[str, Any]):
        """Charge les données depuis un dictionnaire dans le vector store."""
        print(f"Chargement de {len(data.get('pages', []))} pages dans le vector store...")
        
        try:
            documents = []
            metadatas = []
            ids = []
            doc_id_counter = 0
            
            for i, page in enumerate(data.get('pages', [])):
                content = page.get('content', '')
                
                # Si le contenu est trop grand, utiliser les chunks préexistants
                if len(content) > 5000:  # Seuil arbitraire, à ajuster
                    chunks = page.get('chunks', [])
                    for j, chunk in enumerate(chunks):
                        doc_id = f"doc_{doc_id_counter}"
                        doc_id_counter += 1
                        documents.append(chunk)
                        metadatas.append({
                            'url': page.get('url', ''),
                            'title': page.get('title', ''),
                            'chunk_id': j,
                            'is_chunk': True
                        })
                        ids.append(doc_id)
                else:
                    # Sinon, utiliser le contenu entier
                    doc_id = f"doc_{doc_id_counter}"
                    doc_id_counter += 1
                    documents.append(content)
                    metadatas.append({
                        'url': page.get('url', ''),
                        'title': page.get('title', ''),
                        'is_chunk': False
                    })
                    ids.append(doc_id)
            
            # Traiter les documents par lots pour éviter les dépassements de limite
            batch_size = 20  # Ajustez selon vos besoins
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_meta = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                # Ajouter le lot à la collection
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_meta,
                    ids=batch_ids
                )
                print(f"Lot {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size} chargé")
            
            print(f"{len(documents)} documents chargés avec succès")
            
        except Exception as e:
            error_msg = f"Erreur lors du chargement des données: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e

    def rag_query(self, query: str, n_results: int = 5, threshold: float = 0.0) -> Dict[str, Any]:
        """Effectue une recherche RAG (Retrieval-Augmented Generation)."""
        print(f"Recherche RAG pour: {query}")
        
        try:
            # Recherche des documents pertinents
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Préparer les résultats
            sources = []
            for i, doc in enumerate(results['documents'][0]):
                sources.append({
                    'content': doc,
                    'url': results['metadatas'][0][i].get('url', ''),
                    'title': results['metadatas'][0][i].get('title', 'Sans titre'),
                    'similarity': results['distances'][0][i] if 'distances' in results else 0.0
                })
            
            # Générer une réponse avec OpenAI
            context = "\n\n".join([f"Source {i+1}: {src['content']}" for i, src in enumerate(sources)])
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Vous êtes un assistant précis et concis. Répondez directement à la question en vous basant uniquement sur les informations fournies. Allez droit au but sans détails superflus. Si l'information n'est pas disponible dans le contexte, dites-le simplement."},
                    {"role": "user", "content": f"Contexte:\n{context}\n\nQuestion: {query}"}
                ],
                temperature=0.0
            )
            
            return {
                'answer': response.choices[0].message.content,
                'sources': sources
            }
            
        except Exception as e:
            error_msg = f"Erreur lors de la recherche RAG: {str(e)}"
            print(error_msg)
            return {
                'answer': f"Désolé, une erreur s'est produite lors du traitement de votre requête: {str(e)}",
                'sources': []
            }

    def get_collection_info(self) -> Dict[str, Any]:
        """Retourne des informations sur la collection actuelle."""
        try:
            return {
                'name': self.collection.name,
                'count': self.collection.count()
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des informations de la collection: {str(e)}")
            return {'name': 'inconnu', 'count': 0}

    def delete_collection(self):
        """Supprime la collection actuelle."""
        try:
            self.chroma_client.delete_collection(self.collection.name)
            print(f"Collection {self.collection.name} supprimée avec succès")
        except Exception as e:
            print(f"Erreur lors de la suppression de la collection: {str(e)}")
            raise
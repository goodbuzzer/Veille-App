import streamlit as st
from apify_client import ApifyClient
import time
from datetime import datetime
import re


def scrape_facebook_simplified(api_token: str, facebook_urls: list, days: int = 7):
    """
    Scrape uniquement les informations essentielles de Facebook.
    
    Args:
        api_token (str): Token API Apify
        facebook_urls (list): Liste des URLs Facebook
        days (int): Nombre de jours à scraper
    
    Returns:
        list: Liste de dictionnaires avec les données simplifiées
    """
    client = ApifyClient(api_token)
    simplified_data = []
    
    try:
        # 1. Récupérer les infos des pages
        st.info("🔍 Récupération des informations des pages...")
        page_info_actor_id = "Catqz8yCm9MEuNd8x"
        facebook_urls = list(facebook_urls)
        page_info_input = {"urls": facebook_urls}
        
        run_page_info = client.actor(page_info_actor_id).call(run_input=page_info_input)
        page_info_results = list(client.dataset(run_page_info["defaultDatasetId"]).iterate_items())
        
        # 2. Récupérer les posts pour chaque page
        st.info("📝 Récupération des posts...")
        posts_actor_id = "oj3ILOAxhstwhCRYo"
        
        # Calculer les timestamps
        start_time_ts = int(time.time())
        end_time_ts = start_time_ts - (days * 24 * 60 * 60)
        
        posts_input_list = []
        for page_info in page_info_results:
            posts_input_list.append({
                "pageId": page_info.get("page_id"),
                "maxPosts": 100,
                "startTime": start_time_ts,
                "endTime": end_time_ts
            })
        

        if posts_input_list:
            run_posts = client.actor(posts_actor_id).call(run_input={"input": posts_input_list})
            posts_results = list(client.dataset(run_posts["defaultDatasetId"]).iterate_items())
            
            # Créer un mapping des page_id vers nom de page
            page_id_to_name = {page['page_id']: page.get('name', 'N/A') for page in page_info_results}
            
            # Extraire uniquement les données demandées
            for post in posts_results:
                page_id = post.get("pageId")
                page_name = page_id_to_name.get(page_id, "N/A")
                
                # Construire l'URL du post
                post_id = post.get("postId", "")
                post_url = f"https://www.facebook.com/{post_id}" if post_id else "N/A"
                
                # Convertir la date de création
                creation_date = post.get("creationDate")
                
                if creation_date:
                    try:
                        # 1. Si creation_date est un timestamp (ex: "1699632397")
                        if str(creation_date).isdigit():
                            creation_date = datetime.fromtimestamp(int(creation_date)).strftime("%Y-%m-%d")
                        else:
                            # 2. Sinon, parser la date textuelle "Monday, November 10, 2025 at 01:56 PM" et enlever l'heure
                            creation_date = datetime.strptime(
                                creation_date,
                                "%A, %B %d, %Y at %I:%M %p"
                            ).strftime("%Y-%m-%d")

                    except Exception as e:
                        # Si tout échoue, conserver en texte brut
                        creation_date = str(creation_date)
                
                simplified_data.append({
                    "Nom de la page": page_name,
                    "Texte du post": post.get("text", ""),
                    "URL du post": post_url,
                    "Date de création": creation_date
                })
        
        st.success(f"✅ {len(simplified_data)} posts récupérés avec succès!")
        return simplified_data
        
    except Exception as e:
        st.error(f"❌ Erreur lors du scraping: {str(e)}")
        return []




# Fonction pour nettoyer les caractères illégaux pour Excel
def clean_excel_text(text):
    if isinstance(text, str):
        # Supprime tous les caractères ASCII de contrôle sauf tabulation (9), newline (10), carriage return (13)
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text


# Liste des mots vides français (stopwords)
FRENCH_STOPWORDS = [
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "en", "au",
    "aux", "pour", "dans", "sur", "avec", "par", "ce", "cet", "cette", "ces",
    "il", "elle", "ils", "elles", "nous", "vous", "ne", "pas", "que", "qui", "à", "notre", "vos",
    "mais", "ou", "donc", "or", "ni", "car", "si", "tous", "tout", "toute", "toutes",
    "son", "sa", "ses", "leur", "leurs", "mon", "ma", "mes", "ton", "ta", "tes",
    "y", "en", "ceci", "cela", "ça", "ici", "votre", "est", "été", "être", "sont", "été", "faire"
]


def clean_text(text):
    """
    Nettoie le texte pour l'analyse :
    - Supprime les hashtags
    - Supprime la ponctuation
    - Supprime les mots vides français

    Args:
        text (str): Texte à nettoyer

    Returns:
        str: Texte nettoyé
    """
    if isinstance(text, str):
        text = re.sub(r'#\w+', '', text)      # enlever hashtags
        text = re.sub(r'[^\w\s]', '', text)   # enlever ponctuation
        words = text.lower().split()
        words = [w for w in words if w not in FRENCH_STOPWORDS]
        return " ".join(words)
    return ""
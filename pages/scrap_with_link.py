import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import io

def scrape_facebook_simplified(api_token: str, facebook_urls: list, days: int = 35):
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


def main():
    st.set_page_config(
        page_title="Facebook Scraper",
        page_icon="📘",
        layout="wide"
    )
    
    st.title("📘 Facebook Page Scraper")
    st.markdown("Récupérez facilement les posts de vos pages Facebook et exportez-les en Excel")
    
    # Sidebar pour la configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        api_token = "apify_api_k2Pi9y14AA0kj6pZj1szSbAI7CViOM4gKiXd"
        
        days = st.slider(
            "Nombre de jours à scraper",
            min_value=1,
            max_value=90,
            value=7,
            help="Nombre de jours en arrière pour récupérer les posts"
        )
        
        st.markdown("---")
        st.markdown("### 📌 Instructions")
        st.markdown("""
        1. Ajoutez les URLs des pages Facebook
        2. Cliquez sur 'Lancer le scraping'
        3. Téléchargez le fichier Excel
        """)
    
    # Zone principale
    st.header("🔗 URLs des pages Facebook")
    
    # Option pour ajouter plusieurs URLs
    url_input_method = st.radio(
        "Méthode d'ajout des URLs",
        ["Une par ligne", "Liste séparée par des virgules"]
    )
    
    if url_input_method == "Une par ligne":
        urls_text = st.text_area(
            "Entrez les URLs (une par ligne)",
            placeholder="https://www.facebook.com/page1\nhttps://www.facebook.com/page2",
            height=150
        )
        facebook_urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
    else:
        urls_text = st.text_input(
            "Entrez les URLs (séparées par des virgules)",
            placeholder="https://www.facebook.com/page1, https://www.facebook.com/page2"
        )
        facebook_urls = [url.strip() for url in urls_text.split(',') if url.strip()]
    
    # Afficher les URLs détectées
    if facebook_urls:
        st.success(f"✅ {len(facebook_urls)} URL(s) détectée(s)")
        with st.expander("Voir les URLs"):
            for i, url in enumerate(facebook_urls, 1):
                st.write(f"{i}. {url}")
    
    # Bouton de lancement
    if st.button("🚀 Lancer le scraping", type="primary", disabled=not api_token or not facebook_urls):
        if not api_token:
            st.warning("⚠️ Veuillez entrer votre token API Apify")
        elif not facebook_urls:
            st.warning("⚠️ Veuillez ajouter au moins une URL Facebook")
        else:
            with st.spinner("Scraping en cours... Cela peut prendre quelques minutes ⏳"):
                data = scrape_facebook_simplified(api_token, facebook_urls, days)
                
                if data:
                    # Stocker les données dans la session
                    st.session_state['scraped_data'] = data
                    st.session_state['scraping_done'] = True
    
    # Affichage des résultats
    if st.session_state.get('scraping_done', False) and 'scraped_data' in st.session_state:
        st.markdown("---")
        st.header("📊 Résultats")
        
        data = st.session_state['scraped_data']
        df = pd.DataFrame(data)
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de posts", len(df))
        with col2:
            st.metric("Nombre de pages", df["Nom de la page"].nunique())
        with col3:
            avg_text_length = df["Texte du post"].str.len().mean()
            st.metric("Longueur moyenne du texte", f"{avg_text_length:.0f} car.")
        
        # Afficher le tableau
        st.subheader("📋 Aperçu des données")
        st.dataframe(df, use_container_width=True, height=400)
        
        # Boutons d'export
        st.subheader("💾 Exporter les données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Posts Facebook')
                
                # Ajuster la largeur des colonnes
                worksheet = writer.sheets['Posts Facebook']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Télécharger Excel",
                data=excel_data,
                file_name=f"facebook_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Export CSV
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Télécharger CSV",
                data=csv,
                file_name=f"facebook_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Option pour réinitialiser
        if st.button("🔄 Nouveau scraping"):
            st.session_state['scraping_done'] = False
            st.session_state.pop('scraped_data', None)
            st.rerun()


if __name__ == "__main__":
    main()
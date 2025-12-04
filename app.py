import streamlit as st
import pandas as pd
import json
from datetime import datetime
import io
from utils import scrape_facebook_simplified, clean_excel_text, clean_text
import matplotlib.pyplot as plt
from wordcloud import WordCloud


def main():
    st.set_page_config(
        page_title="Facebook Scraper",
        page_icon="🏦",
        layout="wide"
    )
    
    st.title("🏦 Extraction Veille Finance CEMAC Facebook")
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
        1. Sélectionnez le pays correspondant
        2. Cliquez sur 'Lancer le scraping'
        3. Téléchargez le fichier Excel
        """)
        
        # Charger les données des pays
        with open('data.json', 'r', encoding='utf-8') as f:
            countries_data = json.load(f)
        
        # Zone principale
        st.header("🔗 Pays disponibles")
        
        # Sélecteur de pays
        selected_country = st.radio(
        "Sélectionnez le pays",
        options=list(countries_data.keys()),
        horizontal=False
        )
        
        # Récupérer les données du pays sélectionné
        country_data = countries_data.get(selected_country, {})
        facebook_urls = list(country_data.values())
        facebook_names = list(country_data.keys())

        
    
    # Afficher les pages détectées
    if facebook_urls:
        st.success(f"✅ {len(facebook_urls)} page(s) détectée(s)")
        with st.expander("Voir les pages"):
            for i, (name, url) in enumerate(zip(facebook_names, facebook_urls), 1):
                st.write(f"{i}. **{name}** - {url}")
    
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
        df['Date de création'] = pd.to_datetime(df['Date de création'], errors='coerce')
        df.rename(columns={"Nom de la page": "Acteur"}, inplace=True)
        df["Jour"] = df['Date de création'].dt.day
        df["Mois"] = df['Date de création'].dt.month
        df["Année"] = df['Date de création'].dt.year

        # Colonnes à ajouter (vides)
        df.insert(df.columns.get_loc("Texte du post"), "Type", "")
        df.insert(df.columns.get_loc("Texte du post"), "Titre", "")
        df.insert(df.columns.get_loc("URL du post"), "Plateforme", "web")
        df.insert(df.columns.get_loc("URL du post"), "Nom plateforme", "facebook")
        df["Date de création"] = df.pop("Date de création")
        df['URL du post'] = df['URL du post'].apply(lambda x: f'=HYPERLINK("{x}", "{x}")')
        df.rename(columns={"URL du post": "Lien"}, inplace=True)
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre de posts", len(df))
        with col2:
            st.metric("Nombre d'Acteurs", df["Acteur"].nunique())
        with col3:
            avg_text_length = df["Texte du post"].str.len().mean()
            st.metric("Longueur moyenne du texte", f"{avg_text_length:.0f} car.")
        



        # -------------------------------
        # Analyse des posts et nuage de mots
        # -------------------------------

        # Nettoyage complet du texte
        all_text = " ".join(df['Texte du post'].apply(clean_text))

        # Génération du nuage de mots
        wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis').generate(all_text)

        # Comptage des posts par acteur
        posts_per_actor = df.groupby('Acteur')['Lien'].count().sort_values(ascending=False)

        # Extraction des hashtags
        hashtags = df['Texte du post'].str.findall(r'#\w+').explode()
        hashtags_count = hashtags.value_counts()

        # -------------------------------
        # Affichage Streamlit dans deux colonnes
        # -------------------------------
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏷 Top 10 hashtags")
            st.bar_chart(hashtags_count.head(10))

        with col2:
            st.subheader("📝 Nuage de mots des publications")
            fig, ax = plt.subplots(figsize=(8,4))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)





        # Afficher le tableau
        st.subheader("📋 Aperçu des données")
        st.dataframe(df, use_container_width=True, height=400)
        
        # Boutons d'export
        st.subheader("💾 Exporter les données")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export Excel
            output = io.BytesIO()
            # Nettoyage des caractères illégaux
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(clean_excel_text)

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
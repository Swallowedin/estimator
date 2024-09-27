import streamlit as st
from openai import OpenAI
import os
from prestations_heures import get_prestations
from tarifs_prestations import get_tarifs
from chatbot_instructions import get_chatbot_instructions

# Initialisation de l'API OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Chargement des données
prestations = get_prestations()
tarifs = get_tarifs()
instructions = get_chatbot_instructions()

def analyze_question(question, client_type, urgency):
    global prestations
    options = []
    for domaine, prestations_domaine in prestations.items():
        prestations_str = ', '.join(prestations_domaine.keys())
        options.append(f"{domaine}: {prestations_str}")
    options_str = '\n'.join(options)

    prompt = f"""En tant qu'assistant juridique de View Avocats, analysez la question suivante et identifiez le domaine juridique et la prestation la plus pertinente parmi les options données.

Question : {question}
Type de client : {client_type}
Degré d'urgence : {urgency}

Options de domaines et prestations :
{options_str}

Répondez avec le domaine, la prestation la plus pertinente, et un score de confiance entre 0 et 100, séparés par des virgules."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content.strip()
    parts = answer.split(',')
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip(), int(parts[2].strip())
    else:
        return answer, "prestation générale", 50  # Score de confiance par défaut

def calculate_estimate(domaine, prestation, urgency):
    print(f"Debug - Inputs: domaine={domaine}, prestation={prestation}, urgency={urgency}")
    
    heures = prestations.get(domaine, {}).get(prestation, 10)
    print(f"Debug - Heures: {heures}")
    
    tarif_horaire = tarifs["tarif_horaire_standard"]
    print(f"Debug - Tarif horaire: {tarif_horaire}")
    
    estimation = heures * tarif_horaire
    print(f"Debug - Estimation initiale: {estimation}")

    if urgency == "Urgent":
        estimation *= tarifs["facteur_urgence"]
        print(f"Debug - Estimation après urgence: {estimation}")

    forfait = tarifs["forfaits"].get(prestation)
    if forfait:
        estimation = min(estimation, forfait)
        print(f"Debug - Estimation après forfait: {estimation}")
        if urgency == "Urgent":
            estimation *= tarifs["facteur_urgence"]
            print(f"Debug - Estimation finale: {estimation}")

    return round(estimation * 0.8), round(estimation * 1.2)

def main():
    st.set_page_config(page_title="View Avocats - Devis en ligne", page_icon="⚖️", layout="wide")
    
    # CSS personnalisé pour cacher les éléments Streamlit
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.title("🏛️ View Avocats - Estimateur de devis")
    st.write("Obtenez une estimation rapide pour vos besoins juridiques.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Décrivez votre situation juridique")
        client_type = st.selectbox(
            "Vous êtes :",
            ("Particulier", "Professionnel", "Société")
        )
        urgency = st.selectbox(
            "Degré d'urgence :",
            ("Normal", "Urgent")
        )
        question = st.text_area("Expliquez brièvement votre cas :", height=150)

        if st.button("Obtenir une estimation", key="estimate_button"):
            if question:
                with st.spinner("Analyse en cours..."):
                    domaine, prestation, confidence_score = analyze_question(question, client_type, urgency)
                    estimation_basse, estimation_haute = calculate_estimate(domaine, prestation, urgency)

                st.success("J'ai analysé votre demande ! Voici un devis indicatif de ce que coûte la prestation que vous avez demandée. Merci pour votre confiance !")
                
                # Affichage de la jauge de confiance
                st.subheader("Niveau de confiance dans l'analyse")
                st.progress(confidence_score / 100)
                if confidence_score >= 80:
                    st.success(f"Confiance élevée : {confidence_score}%")
                elif confidence_score >= 50:
                    st.warning(f"Confiance moyenne : {confidence_score}%")
                else:
                    st.error(f"Confiance faible : {confidence_score}%")
                
                st.write(f"**Type de client :** {client_type}")
                st.write(f"**Degré d'urgence :** {urgency}")
                st.write(f"**Domaine juridique identifié :** {domaine}")
                st.write(f"**Prestation recommandée :** {prestation}")
                st.write(f"**Estimation du coût hors taxes :** Entre {estimation_basse} €HT et {estimation_haute} €HT")

                # Mettre en valeur l'option alternative
                st.markdown("---")
                st.markdown("### 💡 Alternative Recommandée")
                st.markdown(
                    """
                    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 2px solid #4CAF50;">
                        <h3 style="color: #4CAF50;">Consultation initiale d'une heure</h3>
                        <ul style="list-style-type: none; padding-left: 0;">
                            <li>✅ Tarif fixe : <strong>100 € HT</strong></li>
                            <li>✅ Idéal pour un premier avis juridique</li>
                            <li>✅ Évaluation approfondie de votre situation</li>
                            <li>✅ Recommandations personnalisées</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Boutons d'action
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Demander un devis détaillé", key="detailed_quote"):
                        st.success("Nous vous contacterons bientôt pour un devis détaillé.")
                with col2:
                    if st.button("Réserver une consultation initiale", key="book_consult"):
                        st.success("Excellent choix ! Nous vous contacterons sous peu pour planifier votre consultation.")

                st.markdown("---")
                st.info("Note : Ces estimations sont fournies à titre indicatif et hors taxes. Pour un devis précis et personnalisé, ou pour réserver une consultation, veuillez nous contacter directement.")
            else:
                st.warning("Veuillez décrire votre situation juridique avant de demander une estimation.")

        st.markdown("---")
        st.subheader("Prêt à franchir le pas ?")
        st.write("Nous sommes là pour vous accompagner dans votre démarche juridique. N'hésitez pas à nous contacter pour obtenir un devis personnalisé et des conseils adaptés à votre situation spécifique.")
        st.write("📞 **Téléphone :** 01 23 45 67 89")
        st.write("✉️ **Email :** contact@viewavocats.fr")

        if st.button("Demander un rendez-vous"):
            st.success("Merci de votre intérêt ! Un de nos avocats vous contactera dans les plus brefs délais pour fixer un rendez-vous et discuter de votre situation en détail.")

    with col2:
        st.subheader("Nos domaines d'expertise")
        for domaine in prestations.keys():
            st.write(f"- {domaine.replace('_', ' ').title()}")

        st.subheader("Pourquoi choisir View Avocats ?")
        st.write("✔️ Expertise reconnue dans de nombreux domaines du droit")
        st.write("✔️ Approche personnalisée pour chaque client")
        st.write("✔️ Transparence des tarifs")
        st.write("✔️ Engagement pour votre succès")

        st.markdown("---")
        st.write("© 2024 View Avocats. Tous droits réservés.")

if __name__ == "__main__":
    main()

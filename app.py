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
    options = []
    for domaine, prestations_domaine in prestations.items():
        prestations_str = ', '.join(prestations_domaine.keys())
        options.append(f"{domaine}: {prestations_str}")
    options_str = '\n'.join(options)

    prompt = f"""En tant qu'assistant juridique de View Avocats, identifiez le domaine juridique et la prestation la plus pertinente parmi les options données pour la question suivante.

Question : {question}
Type de client : {client_type}
Degré d'urgence : {urgency}

Options de domaines et prestations :
{options_str}

Répondez avec le domaine et la prestation la plus pertinente, séparés par une virgule."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt}
        ]
    )
    answer = response.choices[0].message.content.strip()
    parts = answer.split(',')
    return parts[0].strip(), parts[1].strip() if len(parts) >= 2 else "prestation générale"

def calculate_estimate(domaine, prestation):
    # La logique de calcul reste inchangée
    heures = prestations.get(domaine, {}).get(prestation, {"min": 5, "max": 15})
    tarif_horaire = tarifs["tarif_horaire_standard"]
    
    estimation_basse = heures["min"] * tarif_horaire["min"]
    estimation_haute = heures["max"] * tarif_horaire["max"]
    
    forfait = tarifs["forfaits"].get(prestation, None)
    if forfait:
        estimation_basse = min(estimation_basse, forfait["min"])
        estimation_haute = min(estimation_haute, forfait["max"])
    
    return estimation_basse, estimation_haute

def main():
    st.set_page_config(page_title="View Avocats - Devis en ligne", page_icon="⚖️", layout="wide")
    st.title("🏛️ View Avocats - Estimateur de devis")
    st.write("Obtenez une estimation indicative pour vos besoins juridiques.")

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
                    domaine, prestation = analyze_question(question, client_type, urgency)
                    estimation_basse, estimation_haute = calculate_estimate(domaine, prestation)
                st.success("J'ai analysé votre demande ! Voici un devis indicatif de ce que coûte la prestation que vous avez demandé. Merci pour votre confiance !")
                st.write(f"**Type de client :** {client_type}")
                st.write(f"**Degré d'urgence :** {urgency}")
                st.write(f"**Domaine juridique identifié :** {domaine}")
                st.write(f"**Prestation recommandée :** {prestation}")
                st.write(f"**Estimation indicative :** Entre {estimation_basse} € et {estimation_haute} €")
                st.info("Note : Cette estimation est fournie à titre purement indicatif. Pour un devis précis et personnalisé, adapté à votre situation spécifique, nous vous invitons à contacter directement notre cabinet.")
                st.warning("Des frais additionnels peuvent s'appliquer. Des réductions sont possibles pour les clients fidèles ou pour des volumes importants.")
            else:
                st.warning("Veuillez décrire votre situation juridique avant de demander une estimation.")

    with col2:
        st.subheader("Nos domaines d'expertise")
        for domaine in prestations.keys():
            st.write(f"- {domaine.replace('_', ' ').title()}")

        st.subheader("Pourquoi choisir View Avocats ?")
        st.write("✔️ Expertise reconnue dans de nombreux domaines du droit")
        st.write("✔️ Approche personnalisée pour chaque client")
        st.write("✔️ Transparence des tarifs")
        st.write("✔️ Engagement pour la réussite de votre dossier")

    st.markdown("---")
    st.write("© 2024 View Avocats. Tous droits réservés.")
    st.write("Contactez-nous pour un devis personnalisé et des conseils adaptés à votre situation.")

if __name__ == "__main__":
    main()

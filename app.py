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
    prestations = get_prestations()
    tarifs = get_tarifs()
    
    # Obtenir le nombre d'heures estimé pour la prestation
    heures = prestations.get(domaine, {}).get(prestation)
    if heures is None:
        raise ValueError(f"Prestation '{prestation}' non trouvée dans le domaine '{domaine}'")
    
    tarif_horaire = tarifs["tarif_horaire_standard"]
    
    # Calculer l'estimation basée sur le nombre d'heures et le tarif horaire
    estimation = heures * tarif_horaire
    
    # Vérifier s'il existe un forfait pour cette prestation
    forfait = tarifs["forfaits"].get(prestation)
    if forfait:
        # Utiliser le minimum entre l'estimation horaire et le forfait
        estimation = min(estimation, forfait)
    
    # Ajouter les frais de dossier
    frais_additionnels = tarifs["frais_additionnels"]
    estimation += frais_additionnels["frais_de_dossier"]
    
    # Calculer une fourchette de prix (+/- 20%)
    estimation_basse = estimation * 0.8
    estimation_haute = estimation * 1.2
    
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
                    try:
                        domaine, prestation = analyze_question(question, client_type, urgency)
                        estimation_basse, estimation_haute = calculate_estimate(domaine, prestation)
                        
                        # Ajuster l'estimation en fonction de l'urgence
                        if urgency == "Urgent":
                            tarifs = get_tarifs()
                            facteur_urgence = tarifs["facteur_urgence"]
                            estimation_basse *= facteur_urgence
                            estimation_haute *= facteur_urgence
                        
                        st.success("J'ai analysé votre demande ! Voici un devis indicatif de ce que coûte la prestation que vous avez demandée. Merci pour votre confiance !")
                        st.write(f"**Type de client :** {client_type}")
                        st.write(f"**Degré d'urgence :** {urgency}")
                        st.write(f"**Domaine juridique identifié :** {domaine}")
                        st.write(f"**Prestation recommandée :** {prestation}")
                        st.write(f"**Estimation indicative :** Entre {estimation_basse:.2f} € et {estimation_haute:.2f} €")
                        st.info("Note : Cette estimation est fournie à titre purement indicatif. Pour un devis précis et personnalisé, adapté à votre situation spécifique, nous vous invitons à contacter directement notre cabinet.")
                        st.warning("Des frais additionnels peuvent s'appliquer. Des réductions sont possibles pour les clients fidèles ou pour des volumes importants.")
                    except Exception as e:
                        st.error(f"Une erreur s'est produite lors du calcul de l'estimation : {str(e)}")
                        st.error(f"Domaine : {domaine}, Prestation : {prestation}")
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

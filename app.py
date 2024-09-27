import streamlit as st
from openai import OpenAI
import os
import sys
import importlib.util
import json

# Configuration du client OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_py_module(file_path, module_name):
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Erreur lors du chargement du module {module_name}: {e}")
        return None

# Chemins des modules à charger
prestations_path = './prestations-heures.py'
tarifs_path = './tarifs-prestations.py'
instructions_path = './chatbot-instructions.py'

prestations_module = load_py_module(prestations_path, 'prestations_heures')
tarifs_module = load_py_module(tarifs_path, 'tarifs_prestations')
instructions_module = load_py_module(instructions_path, 'consignes_chatbot')

# Définition des variables globales
global prestations, tarifs, instructions
prestations = prestations_module.get_prestations() if prestations_module else {}
tarifs = tarifs_module.get_tarifs() if tarifs_module else {}
instructions = instructions_module.get_chatbot_instructions() if instructions_module else ""

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
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    else:
        return answer, "prestation générale"


def calculate_estimate(domaine, prestation, urgency):
    try:
        heures = prestations.get(domaine, {}).get(prestation, 10)
        tarif_horaire = tarifs.get("tarif_horaire_standard")
        if tarif_horaire is None:
            raise KeyError("tarif_horaire_standard non trouvé dans tarifs")
       
        estimation = heures * tarif_horaire


        calcul_details = [f"Heures estimées: {heures}"]
        calcul_details.append(f"Tarif horaire standard: {tarif_horaire} €")
        calcul_details.append(f"Estimation initiale: {heures} x {tarif_horaire} = {estimation} €")


        if urgency == "Urgent":
            facteur_urgence = tarifs.get("facteur_urgence", 1.5)
            estimation *= facteur_urgence
            calcul_details.append(f"Facteur d'urgence appliqué: x{facteur_urgence}")
            calcul_details.append(f"Estimation après urgence: {estimation} €")


        forfait = tarifs.get("forfaits", {}).get(prestation)
        if forfait:
            calcul_details.append(f"Forfait disponible pour cette prestation: {forfait} €")
            if forfait < estimation:
                estimation = forfait
                calcul_details.append(f"Forfait appliqué car plus avantageux: {forfait} €")
            else:
                calcul_details.append("Forfait non appliqué car moins avantageux que l'estimation horaire")


        estimation_basse = round(estimation * 0.8)
        estimation_haute = round(estimation * 1.2)
        calcul_details.append(f"Fourchette d'estimation: {estimation_basse} € - {estimation_haute} €")


        tarifs_utilises = {
            "tarif_horaire_standard": tarif_horaire,
            "facteur_urgence": tarifs.get("facteur_urgence") if urgency == "Urgent" else "Non appliqué",
            "forfait_prestation": forfait if forfait else "Pas de forfait pour cette prestation"
        }


        return estimation_basse, estimation_haute, calcul_details, tarifs_utilises
    except Exception as e:
        print(f"Erreur dans calculate_estimate: {str(e)}")
        print(f"tarifs: {tarifs}")
        print(f"prestations: {prestations}")
        raise



import json
import re
from typing import Tuple, Dict, Any

def get_detailed_analysis(question: str, client_type: str, urgency: str, domaine: str, prestation: str) -> Tuple[str, Dict[str, Any], str]:
    prompt = f"""
    En tant qu'assistant juridique expert, analysez la question suivante et expliquez votre raisonnement pour le choix du domaine juridique et de la prestation.
    
    Question : {question}
    Type de client : {client_type}
    Degré d'urgence : {urgency}
    Domaine recommandé : {domaine}
    Prestation recommandée : {prestation}

    Structurez votre réponse en trois parties distinctes :
    1. Analyse détaillée : Expliquez votre raisonnement de manière claire et concise.
    2. Éléments spécifiques utilisés : Fournissez un objet JSON valide et strict, avec des guillemets doubles pour toutes les clés et les valeurs string. 
       Exemple : {{"domaine": {{"nom": "Droit_immobilier", "description": "Concerne les relations et transactions liées aux biens immobiliers"}}, "prestation": {{"nom": "Rédaction_bail_locatif", "description": "Service de rédaction d'un contrat de location"}}}}
    3. Sources d'information : Listez les sources spécifiques utilisées (fichiers de tarifs, de prestations, ou autres sources internes).

    Assurez-vous que chaque partie est clairement séparée et que le JSON est correctement formaté.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant juridique expert qui explique son raisonnement de manière détaillée et transparente."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1000
        )

        full_response = response.choices[0].message.content.strip()
        
        # Séparation des parties de la réponse
        parts = re.split(r'\d+\.|\*\*', full_response)
        parts = [part.strip() for part in parts if part.strip()]

        analysis = parts[0] if parts else "Analyse non disponible."
        elements_used = {}
        sources = "Aucune source spécifique mentionnée."

        if len(parts) > 1:
            elements_str = parts[1]
            # Extraction du JSON à partir du texte Markdown
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', elements_str, re.DOTALL)
            if json_match:
                elements_str = json_match.group(1)
            
            # Nettoyage et correction du JSON
            elements_str = re.sub(r'(\w+):', r'"\1":', elements_str)
            elements_str = elements_str.replace("'", '"').replace('d"un', "d'un")
            
            try:
                elements_used = json.loads(elements_str)
            except json.JSONDecodeError as e:
                print(f"Erreur de parsing JSON : {e}")
                print(f"Contenu brut des éléments après correction : {elements_str}")
                elements_used = {"error": "Impossible de parser les éléments spécifiques", "raw_content": elements_str}

        if len(parts) > 2:
            sources = parts[2]

    except Exception as e:
        print(f"Erreur lors de l'appel à l'API ou du traitement de la réponse : {e}")
        analysis = "Une erreur s'est produite lors de l'analyse."
        elements_used = {"error": "Erreur lors de l'analyse", "details": str(e)}
        sources = "Non disponible en raison d'une erreur."

    return analysis, elements_used, sources


def main():
    st.set_page_config(page_title="View Avocats - Devis en ligne", page_icon="⚖️", layout="wide")
    st.title("🏛️ View Avocats - Estimateur de devis")
    st.write("Obtenez une estimation rapide pour vos besoins juridiques.")

    # Vérification initiale des données chargées
    if not prestations or not tarifs:
        st.error("Erreur : Données non chargées correctement")
        st.json({
            "prestations": {k: list(v.keys()) for k, v in prestations.items()} if prestations else {},
            "tarifs": {k: v for k, v in tarifs.items() if k != 'forfaits'} if tarifs else {},
            "instructions": instructions[:100] + "..." if instructions else "Vide"
        })
        if not prestations:
            st.error("Les prestations n'ont pas été chargées. Veuillez vérifier le fichier prestations-heures.py")
        if not tarifs:
            st.error("Les tarifs n'ont pas été chargés. Veuillez vérifier le fichier tarifs-prestations.py")
        return


    # Interface utilisateur de base
    client_type = st.selectbox("Vous êtes :", ("Particulier", "Professionnel", "Société"))
    urgency = st.selectbox("Degré d'urgence :", ("Normal", "Urgent"))
    question = st.text_area("Expliquez brièvement votre cas :", height=150)


    if st.button("Obtenir une estimation", key="estimate_button"):
        if question:
            try:
                with st.spinner("Analyse en cours..."):
                    # Étape 1 : Analyse de la question
                    domaine, prestation = analyze_question(question, client_type, urgency)
                    st.write(f"Domaine identifié : {domaine}")
                    st.write(f"Prestation recommandée : {prestation}")


                    # Étape 2 : Calcul de l'estimation
                    estimation_basse, estimation_haute, calcul_details, tarifs_utilises = calculate_estimate(domaine, prestation, urgency)


                    # Étape 3 : Obtention de l'analyse détaillée
                    detailed_analysis, elements_used, sources = get_detailed_analysis(question, client_type, urgency, domaine, prestation)


                # Affichage des résultats
                st.success("Analyse terminée. Voici les résultats :")


                col1, col2 = st.columns(2)


                with col1:
                    st.subheader("Résumé de l'estimation")
                    st.write(f"**Type de client :** {client_type}")
                    st.write(f"**Degré d'urgence :** {urgency}")
                    st.write(f"**Domaine juridique :** {domaine}")
                    st.write(f"**Prestation :** {prestation}")
                    st.write(f"**Estimation :** Entre {estimation_basse} €HT et {estimation_haute} €HT")


                    st.subheader("Détails du calcul")
                    for detail in calcul_details:
                        st.write(detail)


                with col2:
                    st.subheader("Éléments tarifaires utilisés")
                    st.json(tarifs_utilises)


                    if elements_used:
                        st.subheader("Éléments spécifiques pris en compte")
                        st.json(elements_used)


                st.subheader("Analyse détaillée")
                st.write(detailed_analysis)


                if sources:
                    st.subheader("Sources d'information")
                    st.write(sources)


                # Option alternative
                st.markdown("---")
                st.markdown("### 💡 Alternative Recommandée")
                st.info("""
                    **Consultation initiale d'une heure**
                    - Tarif fixe : 100 € HT
                    - Idéal pour un premier avis juridique
                    - Évaluation approfondie de votre situation
                    - Recommandations personnalisées
                """)


                # Boutons d'action
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Demander un devis détaillé"):
                        st.success("Nous vous contacterons pour un devis détaillé.")
                with col2:
                    if st.button("Réserver une consultation initiale"):
                        st.success("Nous vous contacterons pour planifier la consultation.")


            except Exception as e:
                st.error(f"Une erreur s'est produite : {str(e)}")
                st.write("Détails de l'erreur pour le débogage :")
                st.write(e)
                st.write("État des variables globales :")
                st.json({
                    "prestations": {k: list(v.keys()) for k, v in prestations.items()},
                    "tarifs": {k: v for k, v in tarifs.items() if k != 'forfaits'},
                    "instructions": instructions[:100] + "..." if instructions else "Vide"
                })
        else:
            st.warning("Veuillez décrire votre cas avant de demander une estimation.")


    # Informations supplémentaires
    st.markdown("---")
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

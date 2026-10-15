import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from database import get_client, créer_tables

créer_tables()

st.set_page_config(page_title="Paramètres", page_icon=":material/settings:", layout="wide")

# Vérification sécurité
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

# ── SKILL FRONTEND-DESIGN : Typographie, Palette & Composants sur-mesure ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stApp {
    background-color: #F8FAFC;
}

h1, h2, h3 {
    color: #0F172A !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

div[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #0F172A;
    border-radius: 10px;
    padding: 18px 22px;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}
div[data-testid="stMetricLabel"] > div {
    color: #64748B !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
div[data-testid="stMetricValue"] > div {
    font-family: 'JetBrains Mono', monospace !important;
    color: #0F172A !important;
    font-size: 1.55rem !important;
    font-weight: 600 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}
</style>
""", unsafe_allow_html=True)

st.title("Paramètres de l'établissement")
st.caption("Configuration des taux financiers, de la rémunération horaire et des coordonnées sur les documents PDF.")

supabase = get_client()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
def get_parametres():
    res = supabase.table("parametres").select("*").eq("id", 1).execute()
    if not res.data:
        supabase.table("parametres").insert({
            "id"           : 1,
            "taux_horaire" : 12.0,
            "taux_benefice": 0.70,
            "taux_charges" : 0.30,
            "nom_traiteur" : "Mon Traiteur",
            "adresse"      : "",
            "telephone"    : ""
        }).execute()
        res = supabase.table("parametres").select("*").eq("id", 1).execute()
    return res.data[0]


def sauvegarder_parametres(taux_horaire, taux_benefice,
                            nom_traiteur, adresse, telephone):
    taux_charges = 1 - taux_benefice
    supabase.table("parametres").update({
        "taux_horaire"  : taux_horaire,
        "taux_benefice" : taux_benefice,
        "taux_charges"  : taux_charges,
        "nom_traiteur"  : nom_traiteur,
        "adresse"       : adresse,
        "telephone"     : telephone
    }).eq("id", 1).execute()


# ─────────────────────────────────────────────
# AFFICHAGE
# ─────────────────────────────────────────────

params = get_parametres()

with st.container(border=True):
    st.subheader("Paramètres financiers & coordonnées")

    with st.form("form_params"):
        col1, col2 = st.columns(2)

        with col1:
            taux_horaire = st.number_input(
                "Taux horaire du personnel (€/h)",
                min_value=1.0,
                value=float(params['taux_horaire']),
                step=0.5
            )
            taux_benefice = st.slider(
                "Objectif de marge brute (%)",
                min_value=50,
                max_value=90,
                value=int(params['taux_benefice'] * 100),
                step=5
            )

        with col2:
            st.info(f"""
            **Synthèse de répartition :**
            - Taux de marge brute : **{taux_benefice} %**
            - Part des coûts de revient : **{100 - taux_benefice} %**
            - Taux horaire appliqué : **{taux_horaire:.2f} €/h**
            """)

        st.divider()
        st.subheader("Informations de l'entreprise (En-tête PDF)")

        col1, col2 = st.columns(2)
        with col1:
            nom_traiteur = st.text_input(
                "Nom ou raison sociale",
                value=params['nom_traiteur'] or ""
            )
            telephone = st.text_input(
                "Téléphone",
                value=params['telephone'] or ""
            )
        with col2:
            adresse = st.text_area(
                "Adresse postale",
                value=params['adresse'] or ""
            )

        submitted = st.form_submit_button(
            "Enregistrer les paramètres",
            icon=":material/save:",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            sauvegarder_parametres(
                taux_horaire,
                taux_benefice / 100,
                nom_traiteur,
                adresse,
                telephone
            )
            st.success("Les paramètres ont été mis à jour.")
            st.rerun()

st.write("")

# ─────────────────────────────────────────────
# SIMULATEUR
# ─────────────────────────────────────────────

with st.container(border=True):
    st.subheader("Simulateur de tarification")
    st.caption("Vérifiez l'impact de vos paramètres sur un coût de revient donné.")

    cout_exemple = st.number_input(
        "Coût de revient simulé (€)",
        min_value=100.0,
        value=1000.0,
        step=100.0
    )

    taux_ch  = (100 - taux_benefice) / 100
    prix_ex  = cout_exemple / taux_ch
    benef_ex = prix_ex * (taux_benefice / 100)

    col1, col2, col3 = st.columns(3)
    col1.metric("Coût de revient",   f"{cout_exemple:.2f} €")
    col2.metric("Prix final client", f"{prix_ex:.2f} €")
    col3.metric("Marge brute",       f"{benef_ex:.2f} €")
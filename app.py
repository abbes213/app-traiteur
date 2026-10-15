import sys
import os
sys.path.append(os.path.abspath(__file__))

import streamlit as st
from database import get_client, créer_tables

créer_tables()

st.set_page_config(
    page_title="Gestion Traiteur",
    page_icon=":material/restaurant:",
    layout="wide"
)

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
    font-size: 1.45rem !important;
    font-weight: 600 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.stButton > button[kind="primary"] {
    background-color: #0F172A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #1E293B !important;
}
</style>
""", unsafe_allow_html=True)

supabase = get_client()

# ─────────────────────────────────────────────
# MOT DE PASSE
# ─────────────────────────────────────────────

MOT_DE_PASSE = "traiteur_mamieflore2026"

def check_password():
    if "authentifie" not in st.session_state:
        st.session_state.authentifie = False

    if st.session_state.authentifie:
        return True

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
                <div style='text-align: center; padding: 20px 10px 10px 10px;'>
                    <div style='display: inline-block; background-color: #0F172A; color: white; padding: 10px 16px; border-radius: 8px; font-weight: 700; font-size: 14px; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px;'>
                        Espace Gestion
                    </div>
                    <h2 style='color: #0F172A; margin: 5px 0;'>Portail Traiteur</h2>
                    <p style='color: #64748B; font-size: 14px; margin-bottom: 20px;'>Gestion des stocks, fiches techniques et devis commerciaux</p>
                </div>
            """, unsafe_allow_html=True)

            mot_de_passe = st.text_input(
                "Mot de passe d'accès",
                type="password",
                placeholder="Saisissez votre mot de passe"
            )

            if st.button("Se connecter", icon=":material/login:", use_container_width=True, type="primary"):
                if mot_de_passe == MOT_DE_PASSE:
                    st.session_state.authentifie = True
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")

            st.caption("Contactez l'administrateur en cas d'oubli de vos identifiants.")

        st.markdown("""
            <div style='text-align: center; margin-top: 24px;'>
                <p style='color: #94A3B8; font-size: 12px;'>
                    © 2026 Application Traiteur — Tous droits réservés — Youcef ABBES
                </p>
            </div>
        """, unsafe_allow_html=True)

    return False


if not check_password():
    st.stop()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_stats():
    res   = supabase.table("devis").select("*").execute()
    devis = res.data

    total_devis    = len(devis)
    total_valides  = len([d for d in devis if d['statut'] == 'validé'])
    ca_total       = sum(d['prix_final'] for d in devis if d['statut'] == 'validé')
    benefice_total = sum(d['benefice']   for d in devis if d['statut'] == 'validé')

    return {
        "total_devis"   : total_devis,
        "total_valides" : total_valides,
        "ca_total"      : ca_total,
        "benefice_total": benefice_total
    }

@st.cache_data(ttl=30)
def get_alertes():
    produits = supabase.table("produits").select("*").execute()
    return [p for p in produits.data if p['quantite_stock'] <= p['seuil_alerte']]

@st.cache_data(ttl=30)
def get_derniers_devis():
    res = supabase.table("devis")\
        .select("*, recettes(nom)")\
        .order("date_creation", desc=True)\
        .limit(5).execute()
    return res.data

@st.cache_data(ttl=30)
def get_nb_produits():
    res = supabase.table("produits").select("id").execute()
    return len(res.data)

@st.cache_data(ttl=30)
def get_nb_recettes():
    res = supabase.table("recettes").select("id").execute()
    return len(res.data)


# ─────────────────────────────────────────────
# TABLEAU DE BORD
# ─────────────────────────────────────────────

col_titre, col_logout = st.columns([5, 1])
with col_titre:
    st.title("Tableau de bord")
    st.caption("Vue d'ensemble de l'activité commerciale et de l'état des stocks.")
with col_logout:
    st.write("")
    if st.button("Déconnexion", icon=":material/logout:", use_container_width=True):
        st.session_state.authentifie = False
        st.rerun()

# Alertes stock
alertes = get_alertes()
if alertes:
    with st.container(border=True):
        st.error(f"Alerte stock : {len(alertes)} produit(s) sous le seuil de réapprovisionnement")
        for a in alertes:
            st.warning(
                f"**{a['nom']}** — "
                f"Stock actuel : {a['quantite_stock']} {a['unite']} "
                f"(Seuil minimum : {a['seuil_alerte']} {a['unite']})"
            )

# Chiffres clés
st.subheader("Indicateurs clés")

stats       = get_stats()
nb_produits = get_nb_produits()
nb_recettes = get_nb_recettes()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Produits",             nb_produits)
col2.metric("Recettes",             nb_recettes)
col3.metric("Total devis",          stats['total_devis'])
col4.metric("Prestations validées", stats['total_valides'])
col5.metric("Chiffre d'affaires",   f"{stats['ca_total']:.2f} €")
col6.metric("Marge brute totale",   f"{stats['benefice_total']:.2f} €")

st.write("")

# Derniers devis
with st.container(border=True):
    st.subheader("Derniers devis édités")

    derniers_devis = get_derniers_devis()

    if not derniers_devis:
        st.info("Aucun devis enregistré. Rendez-vous dans le module Devis pour créer une simulation.")
    else:
        for d in derniers_devis:
            statut_label = "VALIDÉ" if d['statut'] == 'validé' else "SIMULATION"
            recette_nom  = d['recettes']['nom'] if d['recettes'] else "Formule sur-mesure"
            col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 1.5, 1.5])
            col1.write(f"**{d['nom_client']}**")
            col2.write(recette_nom)
            col3.write(f"{d['nb_personnes']} pers.")
            col4.write(f"**{d['prix_final']:.2f} €**")
            col5.write(f"`{statut_label}`")

st.write("")

# Navigation rapide
st.subheader("Accès rapide aux modules")

with st.container(border=True):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.page_link("pages/1_Stock.py",      label="Gestion du stock", icon=":material/inventory_2:")
    col2.page_link("pages/2_Recettes.py",   label="Fiches recettes",  icon=":material/menu_book:")
    col3.page_link("pages/3_Devis.py",      label="Nouveau devis",    icon=":material/calculate:")
    col4.page_link("pages/4_Historique.py", label="Historique",       icon=":material/folder_open:")
    col5.page_link("pages/5_Parametres.py", label="Paramètres",       icon=":material/settings:")
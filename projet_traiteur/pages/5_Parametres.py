import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from database import get_connection, créer_tables

créer_tables()

st.set_page_config(page_title="Paramètres", page_icon="⚙️")
# Vérification de la sécurité (À PLACER EXACTEMENT ICI)
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")
st.title("⚙️ Paramètres")

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_parametres():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parametres WHERE id = 1")
    params = cursor.fetchone()
    conn.close()
    return params


def sauvegarder_parametres(taux_horaire, taux_benefice,
                            nom_traiteur, adresse, telephone):
    taux_charges = 1 - taux_benefice
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE parametres
        SET taux_horaire  = ?,
            taux_benefice = ?,
            taux_charges  = ?,
            nom_traiteur  = ?,
            adresse       = ?,
            telephone     = ?
        WHERE id = 1
    """, (taux_horaire, taux_benefice, taux_charges,
          nom_traiteur, adresse, telephone))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# AFFICHAGE
# ─────────────────────────────────────────────

params = get_parametres()

st.subheader("💰 Paramètres financiers")

with st.form("form_params"):
    col1, col2 = st.columns(2)

    with col1:
        taux_horaire = st.number_input(
            "💶 Taux horaire employés (€/h)",
            min_value=1.0,
            value=float(params['taux_horaire']),
            step=0.5,
            help="Actuellement 12€/h"
        )
        taux_benefice = st.slider(
            "🤑 Taux de bénéfice (%)",
            min_value=50,
            max_value=90,
            value=int(params['taux_benefice'] * 100),
            step=5,
            help="Le reste sera les charges"
        )

    with col2:
        st.info(f"""
        **Récapitulatif :**
        - Taux bénéfice : **{taux_benefice}%**
        - Taux charges  : **{100 - taux_benefice}%**
        - Taux horaire  : **{taux_horaire} €/h**
        """)

    st.divider()
    st.subheader("🏢 Informations du traiteur")

    col1, col2 = st.columns(2)
    with col1:
        nom_traiteur = st.text_input(
            "Nom / Raison sociale",
            value=params['nom_traiteur'] or ""
        )
        telephone = st.text_input(
            "Téléphone",
            value=params['telephone'] or ""
        )
    with col2:
        adresse = st.text_area(
            "Adresse",
            value=params['adresse'] or ""
        )

    submitted = st.form_submit_button(
        "💾 Sauvegarder les paramètres",
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
        st.success("✅ Paramètres sauvegardés avec succès !")
        st.rerun()

st.divider()

# ─────────────────────────────────────────────
# EXEMPLE DE CALCUL EN TEMPS RÉEL
# ─────────────────────────────────────────────

st.subheader("🧮 Simulateur rapide")
st.write("Vérifiez l'impact de vos paramètres sur un exemple :")

cout_exemple = st.number_input(
    "Coût total exemple (€)",
    min_value=100.0,
    value=1000.0,
    step=100.0
)

taux_ch = (100 - taux_benefice) / 100
prix_ex  = cout_exemple / taux_ch
benef_ex = prix_ex * (taux_benefice / 100)

col1, col2, col3 = st.columns(3)
col1.metric("💰 Coût total",    f"{cout_exemple:.2f} €")
col2.metric("💵 Prix client",   f"{prix_ex:.2f} €")
col3.metric("🤑 Votre bénéfice", f"{benef_ex:.2f} €")
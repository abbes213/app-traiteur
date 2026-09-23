import sys
import os
sys.path.append(os.path.abspath(__file__))

import streamlit as st
from database import get_connection, créer_tables

créer_tables()
st.image("https://images.unsplash.com/photo-1555244162-803834f70033?w=1200", use_container_width=True)
st.set_page_config(
    page_title="Gestion Traiteur",
    page_icon="🍽️",
    layout="wide"
)

# ─────────────────────────────────────────────
# MOT DE PASSE
# ─────────────────────────────────────────────

MOT_DE_PASSE = "traiteur2024"  # ← change ça par le mot de passe que tu veux

def check_password():
    """Vérifie le mot de passe"""

    if "authentifie" not in st.session_state:
        st.session_state.authentifie = False

    if st.session_state.authentifie:
        return True

    # Page de connexion
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🍽️ Application Traiteur")
        st.markdown("---")
        st.subheader("🔒 Connexion")

        mot_de_passe = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="Entrez votre mot de passe"
        )

        if st.button("✅ Se connecter", use_container_width=True, type="primary"):
            if mot_de_passe == MOT_DE_PASSE:
                st.session_state.authentifie = True
                st.success("✅ Connexion réussie !")
                st.rerun()
            else:
                st.error("❌ Mot de passe incorrect !")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Contactez votre administrateur si vous avez oublié le mot de passe.")

    return False


# ─────────────────────────────────────────────
# VÉRIFICATION AVANT TOUT
# ─────────────────────────────────────────────

if not check_password():
    st.stop()  # ← bloque tout si pas connecté

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total_devis,
            SUM(CASE WHEN statut = 'validé' THEN 1 ELSE 0 END) as mariages,
            SUM(CASE WHEN statut = 'validé' THEN prix_final ELSE 0 END) as ca,
            SUM(CASE WHEN statut = 'validé' THEN benefice ELSE 0 END) as benefice
        FROM devis
    """)
    stats = cursor.fetchone()
    conn.close()
    return stats


def get_alertes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM produits
        WHERE quantite_stock <= seuil_alerte
        ORDER BY quantite_stock ASC
    """)
    alertes = cursor.fetchall()
    conn.close()
    return alertes


def get_derniers_devis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, r.nom as recette_nom
        FROM devis d
        JOIN recettes r ON d.recette_id = r.id
        ORDER BY d.date_creation DESC
        LIMIT 5
    """)
    devis = cursor.fetchall()
    conn.close()
    return devis


def get_nb_produits():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as nb FROM produits")
    nb = cursor.fetchone()['nb']
    conn.close()
    return nb


def get_nb_recettes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as nb FROM recettes")
    nb = cursor.fetchone()['nb']
    conn.close()
    return nb


# ─────────────────────────────────────────────
# TABLEAU DE BORD
# ─────────────────────────────────────────────

# Bouton déconnexion en haut à droite
col_titre, col_logout = st.columns([5, 1])
with col_titre:
    st.title("🍽️ Gestion Traiteur — Tableau de Bord")
with col_logout:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔓 Déconnexion"):
        st.session_state.authentifie = False
        st.rerun()

# Alertes stock
alertes = get_alertes()
if alertes:
    st.error(f"⚠️ {len(alertes)} produit(s) à réapprovisionner !")
    for a in alertes:
        st.warning(
            f"🔴 **{a['nom']}** — "
            f"Stock : {a['quantite_stock']} {a['unite']} "
            f"(minimum : {a['seuil_alerte']} {a['unite']})"
        )
    st.divider()

# Chiffres clés
st.subheader("📊 Chiffres clés")

stats       = get_stats()
nb_produits = get_nb_produits()
nb_recettes = get_nb_recettes()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("📦 Produits",          nb_produits)
col2.metric("📋 Recettes",          nb_recettes)
col3.metric("📄 Total devis",       stats['total_devis'] or 0)
col4.metric("✅ Mariages validés",  stats['mariages'] or 0)
col5.metric("💵 Chiffre d'affaires", f"{stats['ca'] or 0:.2f} €")
col6.metric("🤑 Bénéfice total",    f"{stats['benefice'] or 0:.2f} €")

st.divider()

# Derniers devis
st.subheader("📄 5 derniers devis")

derniers_devis = get_derniers_devis()

if not derniers_devis:
    st.info("Aucun devis encore. Allez dans 🧮 Devis pour en créer un !")
else:
    for d in derniers_devis:
        statut_icon = "✅" if d['statut'] == 'validé' else "💾"
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 1])
        col1.write(f"**{d['nom_client']}**")
        col2.write(d['recette_nom'])
        col3.write(f"{d['nb_personnes']} pers.")
        col4.write(f"{d['prix_final']:.2f} €")
        col5.write(f"{statut_icon} {d['statut']}")

st.divider()

# Navigation rapide
st.subheader("🚀 Navigation rapide")

col1, col2, col3, col4, col5 = st.columns(5)
col1.page_link("pages/1_Stock.py",      label="📦 Stock",      icon="📦")
col2.page_link("pages/2_Recettes.py",   label="📋 Recettes",   icon="📋")
col3.page_link("pages/3_Devis.py",      label="🧮 Devis",      icon="🧮")
col4.page_link("pages/4_Historique.py", label="📁 Historique", icon="📁")
col5.page_link("pages/5_Parametres.py", label="⚙️ Paramètres", icon="⚙️")
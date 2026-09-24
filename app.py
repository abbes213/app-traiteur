import sys
import os
sys.path.append(os.path.abspath(__file__))

import streamlit as st
from database import get_client, créer_tables

créer_tables()

st.set_page_config(
    page_title="Gestion Traiteur",
    page_icon="🍽️",
    layout="wide"
)

supabase = get_client()

# ─────────────────────────────────────────────
# MOT DE PASSE
# ─────────────────────────────────────────────

MOT_DE_PASSE = "traiteur2024"

def check_password():
    if "authentifie" not in st.session_state:
        st.session_state.authentifie = False

    if st.session_state.authentifie:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Image en fond avec titre par dessus
        st.markdown("""
            <div style='
                background-image: url("https://images.unsplash.com/photo-1555244162-803834f70033?w=1200");
                background-size: cover;
                background-position: center;
                padding: 60px 30px;
                border-radius: 15px;
                margin-bottom: 20px;
            '>
                <div style='
                    background: rgba(44, 62, 80, 0.82);
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                '>
                    <h1 style='color: white; font-size: 52px; margin: 0;'>🍽️</h1>
                    <h2 style='color: white; margin: 10px 0 5px 0; font-size: 26px;'>
                        Application Traiteur
                    </h2>
                    <p style='color: #BDC3C7; margin: 0; font-size: 14px;'>
                        Gestion professionnelle de vos mariages
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

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
        st.caption("🔑 Contactez votre administrateur si vous avez oublié le mot de passe.")

        st.markdown("""
            <div style='text-align: center; margin-top: 30px;'>
                <p style='color: #BDC3C7; font-size: 12px;'>
                    © 2024 Application Traiteur — Tous droits réservés
                </p>
            </div>
        """, unsafe_allow_html=True)

    return False


if not check_password():
    st.stop()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

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


def get_alertes():
    produits = supabase.table("produits").select("*").execute()
    return [p for p in produits.data if p['quantite_stock'] <= p['seuil_alerte']]


def get_derniers_devis():
    res = supabase.table("devis")\
        .select("*, recettes(nom)")\
        .order("date_creation", desc=True)\
        .limit(5).execute()
    return res.data


def get_nb_produits():
    res = supabase.table("produits").select("id").execute()
    return len(res.data)


def get_nb_recettes():
    res = supabase.table("recettes").select("id").execute()
    return len(res.data)


# ─────────────────────────────────────────────
# TABLEAU DE BORD
# ─────────────────────────────────────────────

col_titre, col_logout = st.columns([5, 1])
with col_titre:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #2C3E50, #3498DB);
                    padding: 15px 25px; border-radius: 10px; margin-bottom: 10px;'>
            <h1 style='color: white; margin: 0; font-size: 28px;'>
                🍽️ Gestion Traiteur — Tableau de Bord
            </h1>
        </div>
    """, unsafe_allow_html=True)
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
col1.metric("📦 Produits",           nb_produits)
col2.metric("📋 Recettes",           nb_recettes)
col3.metric("📄 Total devis",        stats['total_devis'])
col4.metric("✅ Mariages validés",   stats['total_valides'])
col5.metric("💵 Chiffre d'affaires", f"{stats['ca_total']:.2f} €")
col6.metric("🤑 Bénéfice total",     f"{stats['benefice_total']:.2f} €")

st.divider()

# Derniers devis
st.subheader("📄 5 derniers devis")

derniers_devis = get_derniers_devis()

if not derniers_devis:
    st.info("Aucun devis encore. Allez dans 🧮 Devis pour en créer un !")
else:
    for d in derniers_devis:
        statut_icon = "✅" if d['statut'] == 'validé' else "💾"
        recette_nom = d['recettes']['nom'] if d['recettes'] else "Inconnue"
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 2, 1])
        col1.write(f"**{d['nom_client']}**")
        col2.write(recette_nom)
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
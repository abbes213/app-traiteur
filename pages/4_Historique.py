import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables
from modules.pdf_generator import generer_pdf_devis

créer_tables()

st.set_page_config(page_title="Historique des Devis", page_icon="📁")

# Vérification sécurité
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

st.title("📁 Historique des Devis")

supabase = get_client()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_tous_devis(statut_filtre=None, client_filtre=None):
    res = supabase.table("devis")\
        .select("*, recettes(nom)")\
        .order("date_creation", desc=True).execute()
    devis = res.data

    if statut_filtre and statut_filtre != "Tous":
        devis = [d for d in devis if d['statut'] == statut_filtre.lower()]

    if client_filtre:
        devis = [d for d in devis
                 if client_filtre.lower() in d['nom_client'].lower()]

    return devis

@st.cache_data(ttl=30)
def get_employes_devis(devis_id):
    res = supabase.table("employes_devis")\
        .select("*").eq("devis_id", devis_id).execute()
    return res.data


def get_ingredients_devis(recette_id):
    res = supabase.table("recette_ingredients")\
        .select("*, produits(nom, unite, prix_achat)")\
        .eq("recette_id", recette_id).execute()
    return res.data


def supprimer_devis(devis_id):
    supabase.table("employes_devis").delete().eq("devis_id", devis_id).execute()
    supabase.table("devis").delete().eq("id", devis_id).execute()

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


def get_parametres():
    res = supabase.table("parametres").select("*").eq("id", 1).execute()
    return res.data[0]


# ─────────────────────────────────────────────
# STATISTIQUES
# ─────────────────────────────────────────────

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total devis",        stats['total_devis'])
col2.metric("✅ Mariages validés",   stats['total_valides'])
col3.metric("💵 Chiffre d'affaires", f"{stats['ca_total']:.2f} €")
col4.metric("🤑 Bénéfice total",     f"{stats['benefice_total']:.2f} €")

st.divider()

# ─────────────────────────────────────────────
# FILTRES
# ─────────────────────────────────────────────

st.subheader("🔍 Filtres")

col1, col2 = st.columns(2)
with col1:
    statut_filtre = st.selectbox("Statut", ["Tous", "Simulation", "Validé"])
with col2:
    client_filtre = st.text_input("Rechercher un client", placeholder="ex: Ahmed")

# ─────────────────────────────────────────────
# LISTE DES DEVIS
# ─────────────────────────────────────────────

devis_liste = get_tous_devis(statut_filtre, client_filtre)

if not devis_liste:
    st.info("Aucun devis trouvé.")
else:
    st.subheader(f"📋 {len(devis_liste)} devis trouvé(s)")

    for d in devis_liste:
        statut_icon = "✅" if d['statut'] == 'validé' else "💾"
        recette_nom = d['recettes']['nom'] if d['recettes'] else "Inconnue"

        with st.expander(
            f"{statut_icon} #{d['id']} — {d['nom_client']} — "
            f"{recette_nom} — {d['nb_personnes']} pers. — "
            f"{d['prix_final']:.2f} € — {d['date_creation']}"
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("🛒 Ingrédients", f"{d['cout_ingredients']:.2f} €")
            col2.metric("👨‍🍳 Employés",    f"{d['cout_employes']:.2f} €")
            col3.metric("📌 Frais fixes",  f"{d['frais_fixes']:.2f} €")

            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Coût total",  f"{d['cout_total']:.2f} €")
            col2.metric("💵 Prix client", f"{d['prix_final']:.2f} €")
            col3.metric("🤑 Bénéfice",    f"{d['benefice']:.2f} €")

            st.write(f"**Recette :** {recette_nom}")
            st.write(f"**Date mariage :** {d['date_mariage']}")
            st.write(f"**Statut :** {d['statut'].upper()}")

            # Détail employés
            employes = get_employes_devis(d['id'])
            if employes:
                with st.expander("👨‍🍳 Détail employés"):
                    data_emp = []
                    for e in employes:
                        data_emp.append({
                            "Type"        : e['type_employe'],
                            "Nb employés" : e['nombre'],
                            "Nb heures"   : e['heures'],
                            "Coût total"  : f"{e['cout_total']:.2f} €"
                        })
                    st.dataframe(
                        pd.DataFrame(data_emp),
                        use_container_width=True,
                        hide_index=True
                    )

            st.divider()

            # ── ACTIONS ──
            col1, col2 = st.columns(2)

            with col1:
                # Bouton PDF ✅
                if st.button(
                    "🖨️ Télécharger PDF",
                    key=f"pdf_{d['id']}",
                    use_container_width=True
                ):
                    params      = get_parametres()
                    ingredients = get_ingredients_devis(d['recette_id'])
                    employes_d  = get_employes_devis(d['id'])

                    # Reconstruire le détail ingrédients
                    detail_ingredients = []
                    for ing in ingredients:
                        produit    = ing['produits']
                        qte_totale = ing['quantite_par_personne'] * d['nb_personnes']
                        cout       = qte_totale * produit['prix_achat']
                        detail_ingredients.append({
                            "Ingrédient"     : produit['nom'],
                            "Qté / personne" : f"{ing['quantite_par_personne']} {produit['unite']}",
                            "Qté totale"     : f"{qte_totale:.2f} {produit['unite']}",
                            "Prix achat"     : f"{produit['prix_achat']} €",
                            "Coût total"     : f"{cout:.2f} €"
                        })

                    # Reconstruire le détail employés
                    detail_employes = []
                    for e in employes_d:
                        detail_employes.append({
                            "Type"         : e['type_employe'],
                            "Nb employés"  : e['nombre'],
                            "Nb heures"    : e['heures'],
                            "Taux horaire" : f"{params['taux_horaire']} €/h",
                            "Coût total"   : f"{e['cout_total']:.2f} €"
                        })

                    resultat = {
                        "cout_ingredients"           : d['cout_ingredients'],
                        "cout_employes"              : d['cout_employes'],
                        "frais_fixes_recette"        : d['frais_fixes'],
                        "frais_fixes_supplementaires": 0,
                        "frais_fixes_total"          : d['frais_fixes'],
                        "cout_total"                 : d['cout_total'],
                        "prix_final"                 : d['prix_final'],
                        "benefice"                   : d['benefice'],
                        "detail_ingredients"         : detail_ingredients,
                        "detail_employes"            : detail_employes,
                        "taux_horaire"               : params['taux_horaire']
                    }

                    nom_fichier = generer_pdf_devis(
                        nom_client         = d['nom_client'],
                        date_mariage       = d['date_mariage'],
                        recette_nom        = recette_nom,
                        nb_personnes       = d['nb_personnes'],
                        detail_ingredients = detail_ingredients,
                        detail_employes    = detail_employes,
                        resultat           = resultat,
                        params             = dict(params),
                        devis_id           = d['id']
                    )

                    with open(nom_fichier, "rb") as f:
                        st.download_button(
                            label     = "📥 Télécharger",
                            data      = f,
                            file_name = os.path.basename(nom_fichier),
                            mime      = "application/pdf",
                            key       = f"dl_{d['id']}"
                        )
                    st.success("✅ PDF généré !")

            with col2:
                if st.button(
                    "🗑️ Supprimer ce devis",
                    key=f"sup_devis_{d['id']}",
                    use_container_width=True
                ):
                    supprimer_devis(d['id'])
                    st.success("✅ Devis supprimé !")
                    st.rerun()
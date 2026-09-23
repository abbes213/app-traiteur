import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.pdf_generator import generer_pdf_devis
import streamlit as st
import pandas as pd
from database import get_connection, créer_tables

créer_tables()

st.set_page_config(page_title="Historique des Devis", page_icon="📁")
# Vérification de la sécurité (À PLACER EXACTEMENT ICI)
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")
st.title("📁 Historique des Devis")

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_tous_devis(statut_filtre=None, client_filtre=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT d.*, r.nom as recette_nom
        FROM devis d
        JOIN recettes r ON d.recette_id = r.id
        WHERE 1=1
    """
    params = []

    if statut_filtre and statut_filtre != "Tous":
        query += " AND d.statut = ?"
        params.append(statut_filtre.lower())

    if client_filtre:
        query += " AND d.nom_client LIKE ?"
        params.append(f"%{client_filtre}%")

    query += " ORDER BY d.date_creation DESC"

    cursor.execute(query, params)
    devis = cursor.fetchall()
    conn.close()
    return devis


def get_employes_devis(devis_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM employes_devis WHERE devis_id = ?
    """, (devis_id,))
    employes = cursor.fetchall()
    conn.close()
    return employes


def supprimer_devis(devis_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employes_devis WHERE devis_id = ?", (devis_id,))
    cursor.execute("DELETE FROM devis WHERE id = ?", (devis_id,))
    conn.commit()
    conn.close()


def get_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_devis,
            SUM(CASE WHEN statut = 'validé' THEN 1 ELSE 0 END) as total_valides,
            SUM(CASE WHEN statut = 'validé' THEN prix_final ELSE 0 END) as ca_total,
            SUM(CASE WHEN statut = 'validé' THEN benefice ELSE 0 END) as benefice_total
        FROM devis
    """)
    stats = cursor.fetchone()
    conn.close()
    return stats


# ─────────────────────────────────────────────
# STATISTIQUES EN HAUT
# ─────────────────────────────────────────────

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📄 Total devis",       stats['total_devis'] or 0)
col2.metric("✅ Mariages validés",  stats['total_valides'] or 0)
col3.metric("💵 Chiffre d'affaires", f"{stats['ca_total'] or 0:.2f} €")
col4.metric("🤑 Bénéfice total",    f"{stats['benefice_total'] or 0:.2f} €")

st.divider()

# ─────────────────────────────────────────────
# FILTRES
# ─────────────────────────────────────────────

st.subheader("🔍 Filtres")

col1, col2 = st.columns(2)
with col1:
    statut_filtre = st.selectbox(
        "Statut",
        ["Tous", "Simulation", "Validé"]
    )
with col2:
    client_filtre = st.text_input(
        "Rechercher un client",
        placeholder="ex: Ahmed"
    )

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
        with st.expander(
            f"{statut_icon} #{d['id']} — {d['nom_client']} — "
            f"{d['recette_nom']} — {d['nb_personnes']} pers. — "
            f"{d['prix_final']:.2f} € — {d['date_creation']}"
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("🛒 Ingrédients",     f"{d['cout_ingredients']:.2f} €")
            col2.metric("👨‍🍳 Employés",        f"{d['cout_employes']:.2f} €")
            col3.metric("📌 Frais fixes",      f"{d['frais_fixes']:.2f} €")

            col1, col2, col3 = st.columns(3)
            col1.metric("💰 Coût total",       f"{d['cout_total']:.2f} €")
            col2.metric("💵 Prix client",       f"{d['prix_final']:.2f} €")
            col3.metric("🤑 Bénéfice",         f"{d['benefice']:.2f} €")

            st.write(f"**Recette :** {d['recette_nom']}")
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

           # ─────────────────────────────────────────────
            # BOUTONS D'ACTION (PDF ET SUPPRESSION)
            # ─────────────────────────────────────────────
            st.divider()
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                # Étape 1 : Le bouton "Préparer le PDF" reconstruit les données de la base
                if st.button(f"🖨️ Préparer le PDF", key=f"prep_{d['id']}"):
                    
                    # Récupérer les paramètres et les ingrédients pour ce devis
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM parametres WHERE id = 1")
                    params = cursor.fetchone()
                    
                    cursor.execute("""
                        SELECT ri.quantite_par_personne, p.nom, p.unite, p.prix_achat
                        FROM recette_ingredients ri
                        JOIN produits p ON ri.produit_id = p.id
                        WHERE ri.recette_id = ?
                    """, (d['recette_id'],))
                    ingredients_db = cursor.fetchall()
                    conn.close()

                    # Recréer la liste des ingrédients formatée pour le PDF
                    detail_ingredients = []
                    for ing in ingredients_db:
                        qte_totale = ing['quantite_par_personne'] * d['nb_personnes']
                        detail_ingredients.append({
                            "Ingrédient": ing['nom'],
                            "Qté / personne": f"{ing['quantite_par_personne']} {ing['unite']}",
                            "Qté totale": f"{qte_totale:.2f} {ing['unite']}",
                            "Prix achat": f"{ing['prix_achat']} €",
                            "Coût total": f"{qte_totale * ing['prix_achat']:.2f} €"
                        })

                    # Recréer la liste des employés formatée pour le PDF
                    detail_employes = []
                    for e in (employes or []):
                        taux = e['cout_total'] / (e['nombre'] * e['heures']) if (e['nombre'] * e['heures']) > 0 else 0
                        detail_employes.append({
                            "Type": e['type_employe'],
                            "Nb employés": e['nombre'],
                            "Nb heures": e['heures'],
                            "Taux horaire": f"{taux:.2f} €/h",
                            "Coût total": f"{e['cout_total']:.2f} €"
                        })

                    # Recréer le dictionnaire des résultats financiers
                    resultat = {
                        "cout_ingredients": d['cout_ingredients'],
                        "cout_employes": d['cout_employes'],
                        "frais_fixes_total": d['frais_fixes'],
                        "cout_total": d['cout_total'],
                        "prix_final": d['prix_final'],
                        "benefice": d['benefice']
                    }

                    # Étape 2 : Générer le fichier
                    nom_fichier = generer_pdf_devis(
                        nom_client=d['nom_client'],
                        date_mariage=d['date_mariage'],
                        recette_nom=d['recette_nom'],
                        nb_personnes=d['nb_personnes'],
                        detail_ingredients=detail_ingredients,
                        detail_employes=detail_employes,
                        resultat=resultat,
                        params=dict(params),
                        devis_id=d['id']
                    )
                    
                    # Étape 3 : Afficher le bouton de téléchargement final en bleu
                    with open(nom_fichier, "rb") as f:
                        st.download_button(
                            label="📥 Cliquer ici pour télécharger le PDF",
                            data=f,
                            file_name=os.path.basename(nom_fichier),
                            mime="application/pdf",
                            key=f"dl_{d['id']}",
                            type="primary"
                        )

            with col_btn2:
                # Le bouton de suppression reste identique
                if st.button(f"🗑️ Supprimer ce devis", key=f"sup_devis_{d['id']}"):
                    supprimer_devis(d['id'])
                    st.success("✅ Devis supprimé !")
                    st.rerun()
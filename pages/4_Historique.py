import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables
import importlib
import modules.pdf_generator
importlib.reload(modules.pdf_generator)
from modules.pdf_generator import generer_pdf_devis

créer_tables()

st.set_page_config(page_title="Historique des Devis", page_icon=":material/folder_open:", layout="wide")

if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stApp { background-color: #F8FAFC; }
h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #0F172A; border-radius: 10px; padding: 18px 22px; box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04); }
div[data-testid="stMetricLabel"] > div { color: #64748B !important; font-size: 0.78rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.06em; }
div[data-testid="stMetricValue"] > div { font-family: 'JetBrains Mono', monospace !important; color: #0F172A !important; font-size: 1.55rem !important; font-weight: 600 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; padding: 8px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03); }
div[data-testid="stExpander"] { background-color: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; margin-bottom: 10px; }
.stButton > button[kind="primary"] { background-color: #0F172A !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Historique des devis")
st.caption("Suivi financier, validation des simulations et réédition des documents PDF.")

supabase = get_client()

def get_tous_devis(statut_filtre="Tous", auteur_filtre="Tous", client_filtre=""):
    res = supabase.table("devis").select("*, recettes(nom)").order("date_creation", desc=True).execute()
    devis = res.data
    if statut_filtre != "Tous": devis = [d for d in devis if d['statut'] == statut_filtre.lower()]
    if auteur_filtre != "Tous": devis = [d for d in devis if d.get('auteur') == auteur_filtre]
    if client_filtre: devis = [d for d in devis if client_filtre.lower() in d['nom_client'].lower()]
    return devis

def get_recettes_du_devis(devis_id):
    try: return supabase.table("devis_recettes").select("*, recettes(nom)").eq("devis_id", devis_id).execute().data
    except: return []

def get_employes_devis(devis_id):
    return supabase.table("employes_devis").select("*").eq("devis_id", devis_id).execute().data

def get_ingredients_devis(recette_id):
    if not recette_id: return []
    return supabase.table("recette_ingredients").select("*, produits(nom, unite, prix_achat, id)").eq("recette_id", recette_id).execute().data

def supprimer_devis(devis_id):
    try: supabase.table("devis_recettes").delete().eq("devis_id", devis_id).execute()
    except: pass
    supabase.table("employes_devis").delete().eq("devis_id", devis_id).execute()
    supabase.table("devis").delete().eq("id", devis_id).execute()

def get_parametres(): return supabase.table("parametres").select("*").eq("id", 1).execute().data[0]

def valider_mariage(devis_id, lignes_rec, devis_info):
    # 1. Mettre à jour le statut
    supabase.table("devis").update({"statut": "validé"}).eq("id", devis_id).execute()
    
    # 2. Déduire les ingrédients du stock
    if lignes_rec:
        for lr in lignes_rec:
            ings = get_ingredients_devis(lr['recette_id'])
            for ing in ings:
                produit = supabase.table("produits").select("quantite_stock").eq("id", ing['produits']['id']).execute().data[0]
                qte_utilisee = ing['quantite_par_personne'] * lr['nb_personnes']
                supabase.table("produits").update({"quantite_stock": produit['quantite_stock'] - qte_utilisee}).eq("id", ing['produits']['id']).execute()
    else:
        ings = get_ingredients_devis(devis_info['recette_id'])
        for ing in ings:
            produit = supabase.table("produits").select("quantite_stock").eq("id", ing['produits']['id']).execute().data[0]
            qte_utilisee = ing['quantite_par_personne'] * devis_info['nb_personnes']
            supabase.table("produits").update({"quantite_stock": produit['quantite_stock'] - qte_utilisee}).eq("id", ing['produits']['id']).execute()

with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1: statut_filtre = st.selectbox("Filtrer par statut", ["Tous", "Simulation", "Validé"])
    with col2: auteur_filtre = st.selectbox("Filtrer par auteur", ["Tous", "Youcef", "Mami flore"])
    with col3: client_filtre = st.text_input("Rechercher un client", placeholder="Ex. : Mairie, Ahmed...")

devis_liste = get_tous_devis(statut_filtre, auteur_filtre, client_filtre)

total_devis = len(devis_liste)
valides = [d for d in devis_liste if d['statut'] == 'validé']
total_valides = len(valides)
ca_total = sum(d['prix_final'] for d in valides)
benefice_total = sum(d['benefice'] for d in valides)

st.write("")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Dossiers affichés", total_devis)
col2.metric("Prestations validées", total_valides)
col3.metric("Chiffre d'affaires généré", f"{ca_total:.2f} €")
col4.metric("Bénéfice net généré", f"{benefice_total:.2f} €")
st.write("")

if not devis_liste:
    st.info("Aucun devis ne correspond aux critères sélectionnés.")
else:
    for d in devis_liste:
        statut_label = "VALIDÉ" if d['statut'] == 'validé' else "SIMULATION"
        lignes_rec = get_recettes_du_devis(d['id'])
        recette_nom = " + ".join([f"{lr['recettes']['nom'] if lr.get('recettes') else 'Inconnue'} ({lr['nb_personnes']} pers.)" for lr in lignes_rec]) if lignes_rec else (d['recettes']['nom'] if d.get('recettes') else "Inconnue")

        with st.expander(f"Devis #{d['id']:04d}  —  {d['nom_client']}  |  {d['prix_final']:.2f} €  [{statut_label}]"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Coût matières", f"{d['cout_ingredients']:.2f} €")
            col2.metric("Coût personnel", f"{d['cout_employes']:.2f} €")
            col3.metric("Frais fixes", f"{d['frais_fixes']:.2f} €")

            col1, col2, col3 = st.columns(3)
            col1.metric("Coût de revient", f"{d['cout_total']:.2f} €")
            col2.metric("Prix client", f"{d['prix_final']:.2f} €")
            col3.metric("Bénéfice Net", f"{d['benefice']:.2f} €")

            st.write(f"**Formule(s) :** {recette_nom}")
            st.write(f"**Date de prestation :** {d['date_mariage']}  |  **Créé par :** {d.get('auteur', 'Non spécifié')} le {d['date_creation']}")

            employes = get_employes_devis(d['id'])
            if employes:
                with st.expander("Détail des postes employés"):
                    st.dataframe(pd.DataFrame([{"Poste": e['type_employe'], "Effectif": e['nombre'], "Heures": e['heures'], "Coût total": f"{e['cout_total']:.2f} €"} for e in employes]), use_container_width=True, hide_index=True)

            st.divider()
            
            # --- GESTION DES BOUTONS SELON LE STATUT ---
            if d['statut'] == 'simulation':
                col_val, col_pdf, col_sup = st.columns(3)
                
                with col_val:
                    if st.button("Valider la prestation", key=f"val_{d['id']}", type="primary", icon=":material/check_circle:", use_container_width=True):
                        valider_mariage(d['id'], lignes_rec, d)
                        st.rerun()

                with col_pdf:
                    if st.button("Générer le PDF", key=f"pdf_{d['id']}", icon=":material/print:", use_container_width=True):
                        params, employes_d = get_parametres(), get_employes_devis(d['id'])
                        detail_recettes, detail_ingredients = [], []

                        if lignes_rec:
                            for lr in lignes_rec:
                                nom_r = lr['recettes']['nom'] if lr.get('recettes') else "Archivée"
                                ings = get_ingredients_devis(lr['recette_id'])
                                cout_unit = 0
                                for ing in ings:
                                    qte_totale = ing['quantite_par_personne'] * lr['nb_personnes']
                                    cout = qte_totale * ing['produits']['prix_achat']
                                    cout_unit += ing['quantite_par_personne'] * ing['produits']['prix_achat']
                                    detail_ingredients.append({"Ingrédient": f"{ing['produits']['nom']} ({nom_r} - {lr['nb_personnes']}p)", "Qté / personne": f"{ing['quantite_par_personne']} {ing['produits']['unite']}", "Qté totale": f"{qte_totale:.2f} {ing['produits']['unite']}", "Prix achat": f"{ing['produits']['prix_achat']} €", "Coût total": f"{cout:.2f} €"})
                                detail_recettes.append({"Recette": nom_r, "Nb personnes": f"{lr['nb_personnes']} pers.", "Coût / pers.": f"{cout_unit:.2f} €", "Coût total": f"{cout_unit * lr['nb_personnes']:.2f} €"})
                        else:
                            ings = get_ingredients_devis(d['recette_id'])
                            for ing in ings:
                                qte_totale = ing['quantite_par_personne'] * d['nb_personnes']
                                cout = qte_totale * ing['produits']['prix_achat']
                                detail_ingredients.append({"Ingrédient": ing['produits']['nom'], "Qté / personne": f"{ing['quantite_par_personne']} {ing['produits']['unite']}", "Qté totale": f"{qte_totale:.2f} {ing['produits']['unite']}", "Prix achat": f"{ing['produits']['prix_achat']} €", "Coût total": f"{cout:.2f} €"})
                            cout_unit = d['cout_ingredients'] / d['nb_personnes'] if d['nb_personnes'] else 0
                            detail_recettes.append({"Recette": recette_nom, "Nb personnes": f"{d['nb_personnes']} pers.", "Coût / pers.": f"{cout_unit:.2f} €", "Coût total": f"{d['cout_ingredients']:.2f} €"})

                        detail_employes = [{"Type": e['type_employe'], "Nb employés": e['nombre'], "Nb heures": e['heures'], "Taux horaire": f"{params['taux_horaire']} €/h", "Coût total": f"{e['cout_total']:.2f} €"} for e in employes_d]
                        marge_brute_pdf = d['prix_final'] - d['cout_ingredients']
                        resultat = {"cout_ingredients": d['cout_ingredients'], "cout_employes": d['cout_employes'], "frais_fixes_total": d['frais_fixes'], "cout_total": d['cout_total'], "prix_final": d['prix_final'], "marge_brute": marge_brute_pdf, "benefice": d['benefice'], "detail_recettes": detail_recettes, "detail_ingredients": detail_ingredients, "detail_employes": detail_employes, "taux_horaire": params['taux_horaire']}

                        nom_fichier = generer_pdf_devis(d['nom_client'], d['date_mariage'], recette_nom, d['nb_personnes'], detail_ingredients, detail_employes, resultat, dict(params), d['id'])
                        with open(nom_fichier, "rb") as f:
                            st.download_button("Télécharger le document PDF", data=f, file_name=os.path.basename(nom_fichier), mime="application/pdf", icon=":material/download:", key=f"dl_{d['id']}", use_container_width=True)

                with col_sup:
                    if st.button("Supprimer ce devis", key=f"sup_{d['id']}", icon=":material/delete:", use_container_width=True):
                        supprimer_devis(d['id'])
                        st.rerun()

            else:
                col_pdf, col_sup = st.columns(2)
                
                with col_pdf:
                    if st.button("Générer le PDF", key=f"pdf_{d['id']}", icon=":material/print:", use_container_width=True):
                        params, employes_d = get_parametres(), get_employes_devis(d['id'])
                        detail_recettes, detail_ingredients = [], []

                        if lignes_rec:
                            for lr in lignes_rec:
                                nom_r = lr['recettes']['nom'] if lr.get('recettes') else "Archivée"
                                ings = get_ingredients_devis(lr['recette_id'])
                                cout_unit = 0
                                for ing in ings:
                                    qte_totale = ing['quantite_par_personne'] * lr['nb_personnes']
                                    cout = qte_totale * ing['produits']['prix_achat']
                                    cout_unit += ing['quantite_par_personne'] * ing['produits']['prix_achat']
                                    detail_ingredients.append({"Ingrédient": f"{ing['produits']['nom']} ({nom_r} - {lr['nb_personnes']}p)", "Qté / personne": f"{ing['quantite_par_personne']} {ing['produits']['unite']}", "Qté totale": f"{qte_totale:.2f} {ing['produits']['unite']}", "Prix achat": f"{ing['produits']['prix_achat']} €", "Coût total": f"{cout:.2f} €"})
                                detail_recettes.append({"Recette": nom_r, "Nb personnes": f"{lr['nb_personnes']} pers.", "Coût / pers.": f"{cout_unit:.2f} €", "Coût total": f"{cout_unit * lr['nb_personnes']:.2f} €"})
                        else:
                            ings = get_ingredients_devis(d['recette_id'])
                            for ing in ings:
                                qte_totale = ing['quantite_par_personne'] * d['nb_personnes']
                                cout = qte_totale * ing['produits']['prix_achat']
                                detail_ingredients.append({"Ingrédient": ing['produits']['nom'], "Qté / personne": f"{ing['quantite_par_personne']} {ing['produits']['unite']}", "Qté totale": f"{qte_totale:.2f} {ing['produits']['unite']}", "Prix achat": f"{ing['produits']['prix_achat']} €", "Coût total": f"{cout:.2f} €"})
                            cout_unit = d['cout_ingredients'] / d['nb_personnes'] if d['nb_personnes'] else 0
                            detail_recettes.append({"Recette": recette_nom, "Nb personnes": f"{d['nb_personnes']} pers.", "Coût / pers.": f"{cout_unit:.2f} €", "Coût total": f"{d['cout_ingredients']:.2f} €"})

                        detail_employes = [{"Type": e['type_employe'], "Nb employés": e['nombre'], "Nb heures": e['heures'], "Taux horaire": f"{params['taux_horaire']} €/h", "Coût total": f"{e['cout_total']:.2f} €"} for e in employes_d]
                        marge_brute_pdf = d['prix_final'] - d['cout_ingredients']
                        resultat = {"cout_ingredients": d['cout_ingredients'], "cout_employes": d['cout_employes'], "frais_fixes_total": d['frais_fixes'], "cout_total": d['cout_total'], "prix_final": d['prix_final'], "marge_brute": marge_brute_pdf, "benefice": d['benefice'], "detail_recettes": detail_recettes, "detail_ingredients": detail_ingredients, "detail_employes": detail_employes, "taux_horaire": params['taux_horaire']}

                        nom_fichier = generer_pdf_devis(d['nom_client'], d['date_mariage'], recette_nom, d['nb_personnes'], detail_ingredients, detail_employes, resultat, dict(params), d['id'])
                        with open(nom_fichier, "rb") as f:
                            st.download_button("Télécharger le document PDF", data=f, file_name=os.path.basename(nom_fichier), mime="application/pdf", icon=":material/download:", key=f"dl_{d['id']}", use_container_width=True)

                with col_sup:
                    if st.button("Supprimer ce devis", key=f"sup_{d['id']}", icon=":material/delete:", use_container_width=True):
                        supprimer_devis(d['id'])
                        st.rerun()
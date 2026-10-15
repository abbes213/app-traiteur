import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables
from datetime import date
import importlib
import modules.pdf_generator
importlib.reload(modules.pdf_generator)
from modules.pdf_generator import generer_pdf_devis

créer_tables()

st.set_page_config(page_title="Générateur de Devis", page_icon=":material/calculate:", layout="wide")

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
div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; padding: 10px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03); }
.stButton > button[kind="primary"] { background-color: #0F172A !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Générateur de devis")
st.caption("Chiffrage financier professionnel basé sur la Marge Brute matière.")

supabase = get_client()

def get_toutes_recettes():
    return supabase.table("recettes").select("*").order("nom").execute().data

def get_ingredients_recette(recette_id):
    return supabase.table("recette_ingredients").select("*, produits(nom, unite, prix_achat, id)").eq("recette_id", recette_id).execute().data

def get_parametres():
    return supabase.table("parametres").select("*").eq("id", 1).execute().data[0]

def get_recette(recette_id):
    return supabase.table("recettes").select("*").eq("id", recette_id).execute().data[0]

def calculer_devis(recettes_selectionnees, employes, frais_fixes_supplementaires):
    params = get_parametres()
    detail_recettes, detail_ingredients, detail_employes = [], [], []
    cout_ingredients = frais_fixes_recette = cout_employes = 0

    for item in recettes_selectionnees:
        recette = get_recette(item['id'])
        ingredients = get_ingredients_recette(item['id'])
        frais_fixes_recette += recette['frais_fixes']
        cout_unitaire_recette = 0

        for ing in ingredients:
            qte_totale = ing['quantite_par_personne'] * item['nb_personnes']
            cout = qte_totale * ing['produits']['prix_achat']
            cout_ingredients += cout
            cout_unitaire_recette += ing['quantite_par_personne'] * ing['produits']['prix_achat']
            detail_ingredients.append({"Ingrédient": f"{ing['produits']['nom']} ({recette['nom']} - {item['nb_personnes']}p)", "Qté / personne": f"{ing['quantite_par_personne']} {ing['produits']['unite']}", "Qté totale": f"{qte_totale:.2f} {ing['produits']['unite']}", "Prix achat": f"{ing['produits']['prix_achat']} €", "Coût total": f"{cout:.2f} €"})
        detail_recettes.append({"Recette": recette['nom'], "Nb personnes": f"{item['nb_personnes']} pers.", "Coût / pers.": f"{cout_unitaire_recette:.2f} €", "Coût total": f"{cout_unitaire_recette * item['nb_personnes']:.2f} €"})

    for emp in employes:
        cout = emp['nombre'] * emp['heures'] * params['taux_horaire']
        cout_employes += cout
        detail_employes.append({"Type": emp['type'], "Nb employés": emp['nombre'], "Nb heures": emp['heures'], "Coût total": f"{cout:.2f} €"})

    frais_fixes_total = frais_fixes_recette + frais_fixes_supplementaires
    cout_total = cout_ingredients + cout_employes + frais_fixes_total

    # LOGIQUE FINANCIÈRE RESTAURATEUR
    prix_final = cout_ingredients / params['taux_charges']
    marge_brute = prix_final - cout_ingredients
    benefice_net = marge_brute - cout_employes - frais_fixes_total

    return {
        "cout_ingredients": cout_ingredients, "cout_employes": cout_employes, "frais_fixes_total": frais_fixes_total,
        "cout_total": cout_total, "prix_final": prix_final, "marge_brute": marge_brute, "benefice": benefice_net,
        "detail_recettes": detail_recettes, "detail_ingredients": detail_ingredients, "detail_employes": detail_employes, "taux_horaire": params['taux_horaire']
    }

def sauvegarder_devis(nom_client, date_mariage, auteur_devis, recettes_selectionnees, employes, resultat, statut):
    total_personnes = recettes_selectionnees[0]['nb_personnes'] if len(set(r['nb_personnes'] for r in recettes_selectionnees)) == 1 else sum(r['nb_personnes'] for r in recettes_selectionnees)
    
    if statut == "validé":
        simus = supabase.table("devis").select("id").eq("nom_client", nom_client).eq("statut", "simulation").execute()
        for sim in simus.data:
            try: supabase.table("devis_recettes").delete().eq("devis_id", sim['id']).execute()
            except: pass
            supabase.table("employes_devis").delete().eq("devis_id", sim['id']).execute()
            supabase.table("devis").delete().eq("id", sim['id']).execute()

    res = supabase.table("devis").insert({
        "nom_client": nom_client, "date_mariage": str(date_mariage), "auteur": auteur_devis,
        "recette_id": recettes_selectionnees[0]['id'], "nb_personnes": total_personnes,
        "cout_ingredients": resultat['cout_ingredients'], "cout_employes": resultat['cout_employes'],
        "frais_fixes": resultat['frais_fixes_total'], "cout_total": resultat['cout_total'],
        "prix_final": resultat['prix_final'], "benefice": resultat['benefice'], "statut": statut
    }).execute()

    devis_id = res.data[0]['id']
    try:
        for r_sel in recettes_selectionnees:
            supabase.table("devis_recettes").insert({"devis_id": devis_id, "recette_id": r_sel['id'], "nb_personnes": r_sel['nb_personnes']}).execute()
    except: pass

    for emp in employes:
        supabase.table("employes_devis").insert({"devis_id": devis_id, "type_employe": emp['type'], "nombre": emp['nombre'], "heures": emp['heures'], "cout_total": emp['nombre'] * emp['heures'] * get_parametres()['taux_horaire']}).execute()
    return devis_id

def valider_mariage(devis_id, recettes_selectionnees):
    supabase.table("devis").update({"statut": "validé"}).eq("id", devis_id).execute()
    for r_sel in recettes_selectionnees:
        ingredients = get_ingredients_recette(r_sel['id'])
        for ing in ingredients:
            produit = supabase.table("produits").select("quantite_stock").eq("id", ing['produits']['id']).execute().data[0]
            supabase.table("produits").update({"quantite_stock": produit['quantite_stock'] - (ing['quantite_par_personne'] * r_sel['nb_personnes'])}).eq("id", ing['produits']['id']).execute()

recettes = get_toutes_recettes()
if not recettes:
    st.warning("Aucune recette n'est disponible. Veuillez d'abord créer vos fiches recettes.")
    st.stop()
noms_recettes = [r['nom'] for r in recettes]
options_recettes = {r['nom']: r for r in recettes}

with st.container(border=True):
    st.subheader("01. Informations client & composition du menu")
    col1, col2, col3 = st.columns([2, 1.5, 1.5])
    with col1: nom_client = st.text_input("Nom du client", placeholder="Ex. : Mairie")
    with col2: date_mariage = st.date_input("Date de la prestation", value=date.today())
    with col3: auteur_devis = st.selectbox("Édité par", ["Youcef", "Mami flore"])

    st.markdown("**Sélection des formules et nombre de convives**")
    if 'lignes_recettes' not in st.session_state: st.session_state.lignes_recettes = [{"nom": noms_recettes[0], "nb_personnes": 100}]
    recettes_valides, frais_fixes_cumules = [], 0

    for i, ligne in enumerate(st.session_state.lignes_recettes):
        col_r, col_p = st.columns([3, 2])
        with col_r: recette_nom_choisie = st.selectbox(f"Recette n° {i+1:02d}", noms_recettes, index=noms_recettes.index(ligne['nom']) if ligne['nom'] in noms_recettes else 0, key=f"rec_{i}")
        with col_p: nb_pers = st.number_input(f"Convives (Recette n° {i+1:02d})", min_value=1, step=1, value=int(ligne['nb_personnes']), key=f"pers_{i}")
        rec_obj = options_recettes[recette_nom_choisie]
        frais_fixes_cumules += rec_obj['frais_fixes']
        recettes_valides.append({"id": rec_obj['id'], "nom": rec_obj['nom'], "nb_personnes": nb_pers, "frais_fixes": rec_obj['frais_fixes']})

    col_add_r, col_reset_r = st.columns(2)
    with col_add_r:
        if st.button("Ajouter une recette", icon=":material/add:"):
            st.session_state.lignes_recettes.append({"nom": noms_recettes[0], "nb_personnes": 100}); st.rerun()
    with col_reset_r:
        if len(st.session_state.lignes_recettes) > 1 and st.button("Conserver une seule recette", icon=":material/restart_alt:"):
            st.session_state.lignes_recettes = [{"nom": noms_recettes[0], "nb_personnes": 100}]; st.rerun()

with st.container(border=True):
    st.subheader("02. Personnel et main-d'œuvre")
    if 'employes' not in st.session_state: st.session_state.employes = [{"type": "Serveurs", "nombre": 1, "heures": 8}, {"type": "Cuisiniers", "nombre": 1, "heures": 8}]
    params = get_parametres()
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1])
    col1.markdown("**Poste**"); col2.markdown("**Effectif**"); col3.markdown("**Heures**"); col4.markdown("**Coût**"); col5.markdown("**Action**")

    employes_valides = []
    for i, emp in enumerate(st.session_state.employes):
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1])
        with col1: type_emp = st.text_input("Type", value=emp['type'], key=f"type_{i}", label_visibility="collapsed")
        with col2: nb_emp = st.number_input("Nb", value=emp['nombre'], min_value=1, key=f"nb_{i}", label_visibility="collapsed")
        with col3: nb_h = st.number_input("Heures", value=float(emp['heures']), min_value=1.0, step=0.5, key=f"h_{i}", label_visibility="collapsed")
        with col4: st.markdown(f"**{nb_emp * nb_h * params['taux_horaire']:.0f} €**")
        with col5:
            if st.button("", icon=":material/close:", key=f"del_emp_{i}"): st.session_state.employes.pop(i); st.rerun()
        employes_valides.append({"type": type_emp, "nombre": nb_emp, "heures": nb_h})

    if st.button("Ajouter une ligne employé", icon=":material/person_add:"):
        st.session_state.employes.append({"type": "Autre", "nombre": 1, "heures": 8}); st.rerun()

with st.container(border=True):
    st.subheader("03. Frais fixes et logistique")
    col1, col2 = st.columns(2)
    with col1: st.info(f"Frais fixes associés aux recettes sélectionnées : **{frais_fixes_cumules:.2f} €**")
    with col2: frais_supp = st.number_input("Frais supplémentaires (€)", min_value=0.0, step=50.0)

st.write("")
if st.button("Calculer le devis", type="primary", icon=":material/calculate:", use_container_width=True):
    if not nom_client: st.error("Veuillez renseigner le nom du client.")
    else:
        st.session_state.resultat = calculer_devis(recettes_valides, employes_valides, frais_supp)
        st.session_state.devis_calcule = True
        st.session_state.nom_client = nom_client
        st.session_state.date_mariage = date_mariage
        st.session_state.auteur_devis = auteur_devis
        st.session_state.recettes_selectionnees = recettes_valides
        st.session_state.employes_snap = employes_valides

if st.session_state.get('devis_calcule'):
    r, r_list = st.session_state.resultat, st.session_state.recettes_selectionnees
    resume_recettes = " + ".join([f"{x['nom']} ({x['nb_personnes']} pers.)" for x in r_list])
    
    st.divider()
    st.subheader(f"Synthèse financière — {st.session_state.nom_client}")
    st.caption(f"Prestation : {resume_recettes} | Édité par : {st.session_state.auteur_devis}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Coût matières premières", f"{r['cout_ingredients']:.2f} €")
    col2.metric("Marge Brute", f"{r['marge_brute']:.2f} €")
    col3.metric("Charges (Personnel + Frais)", f"{r['cout_employes'] + r['frais_fixes_total']:.2f} €")
    col4.metric("Coût de revient global", f"{r['cout_total']:.2f} €")

    st.write("")
    col1, col2 = st.columns(2)
    col1.metric("Prix final client", f"{r['prix_final']:.2f} €")
    col2.metric("Bénéfice Net (Résultat)", f"{r['benefice']:.2f} €")

    st.write("")
    with st.expander("Détail des recettes", expanded=True): st.dataframe(pd.DataFrame(r['detail_recettes']), use_container_width=True, hide_index=True)
    with st.expander("Détail des ingrédients (Cuisine)"): st.dataframe(pd.DataFrame(r['detail_ingredients']), use_container_width=True, hide_index=True)
    with st.expander("Détail du personnel"): st.dataframe(pd.DataFrame(r['detail_employes']), use_container_width=True, hide_index=True)

    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Sauvegarder simulation", icon=":material/bookmark_add:", use_container_width=True):
            devis_id = sauvegarder_devis(st.session_state.nom_client, st.session_state.date_mariage, st.session_state.auteur_devis, r_list, st.session_state.employes_snap, r, "simulation")
            st.success(f"Devis #{devis_id:04d} enregistré.")
    with col2:
        if st.button("Générer le PDF", icon=":material/print:", use_container_width=True):
            devis_id = sauvegarder_devis(st.session_state.nom_client, st.session_state.date_mariage, st.session_state.auteur_devis, r_list, st.session_state.employes_snap, r, "simulation")
            nom_fichier = generer_pdf_devis(st.session_state.nom_client, st.session_state.date_mariage, resume_recettes, sum(x['nb_personnes'] for x in r_list), r['detail_ingredients'], r['detail_employes'], r, dict(get_parametres()), devis_id)
            with open(nom_fichier, "rb") as f:
                st.download_button("Télécharger le document PDF", data=f, file_name=os.path.basename(nom_fichier), mime="application/pdf", icon=":material/download:", use_container_width=True)
    with col3:
        if st.button("Valider la prestation", type="primary", icon=":material/check_circle:", use_container_width=True):
            devis_id = sauvegarder_devis(st.session_state.nom_client, st.session_state.date_mariage, st.session_state.auteur_devis, r_list, st.session_state.employes_snap, r, "validé")
            valider_mariage(devis_id, r_list)
            st.success(f"Prestation validée. Le devis #{devis_id:04d} a été enregistré.")
            st.session_state.devis_calcule = False
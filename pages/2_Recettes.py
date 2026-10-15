import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables

créer_tables()

st.set_page_config(page_title="Gestion des Recettes", page_icon=":material/menu_book:", layout="wide")

if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

# ── STYLE CSS PROFESSIONNEL ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stApp { background-color: #F8FAFC; }
h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { background-color: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; padding: 10px; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03); }
div[data-testid="stExpander"] { background-color: #FFFFFF; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; margin-bottom: 10px; }
.stButton > button[kind="primary"] { background-color: #0F172A !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

st.title("Fiches techniques & recettes")
st.caption("Création des menus, rendement (pour X convives) et calcul automatique des coûts matières.")

supabase = get_client()

def get_toutes_recettes():
    res = supabase.table("recettes").select("*").order("nom").execute()
    return res.data

def get_tous_produits():
    res = supabase.table("produits").select("*").order("nom").execute()
    return res.data

def get_ingredients_recette(recette_id):
    res = supabase.table("recette_ingredients").select("*, produits(nom, unite, prix_achat)").eq("recette_id", recette_id).execute()
    return res.data

def ajouter_recette(nom, description, frais_fixes, nb_personnes_base):
    supabase.table("recettes").insert({"nom": nom, "description": description, "frais_fixes": frais_fixes, "nb_personnes_base": nb_personnes_base}).execute()

def modifier_recette(id, nom, description, frais_fixes, nb_personnes_base):
    supabase.table("recettes").update({"nom": nom, "description": description, "frais_fixes": frais_fixes, "nb_personnes_base": nb_personnes_base}).eq("id", id).execute()

def supprimer_recette(recette_id):
    supabase.table("devis").update({"recette_id": None}).eq("recette_id", recette_id).execute()
    try:
        supabase.table("devis_recettes").update({"recette_id": None}).eq("recette_id", recette_id).execute()
    except: pass
    supabase.table("recette_ingredients").delete().eq("recette_id", recette_id).execute()
    supabase.table("recettes").delete().eq("id", recette_id).execute()

def ajouter_ingredient(recette_id, produit_id, quantite_par_personne):
    supabase.table("recette_ingredients").insert({"recette_id": recette_id, "produit_id": produit_id, "quantite_par_personne": quantite_par_personne}).execute()

def modifier_quantite_ingredient(ingredient_id, nouvelle_qte_par_personne):
    supabase.table("recette_ingredients").update({"quantite_par_personne": nouvelle_qte_par_personne}).eq("id", ingredient_id).execute()

def supprimer_ingredient(ingredient_id):
    supabase.table("recette_ingredients").delete().eq("id", ingredient_id).execute()

def calculer_cout_par_personne(ingredients):
    return sum(ing['quantite_par_personne'] * ing['produits']['prix_achat'] for ing in ingredients)

recettes = get_toutes_recettes()

if not recettes:
    st.info("Aucune recette enregistrée. Créez votre première fiche technique ci-dessous.")
else:
    for recette in recettes:
        ingredients = get_ingredients_recette(recette['id'])
        cout_par_personne = calculer_cout_par_personne(ingredients)
        
        # Sécurité si la recette a été créée avant la mise à jour SQL
        nb_base = recette.get('nb_personnes_base')
        if nb_base is None:
            nb_base = 1

        with st.expander(f"{recette['nom']}  —  Conçue pour {nb_base} pers.  |  {cout_par_personne:.2f} € / convive"):
            col1, col2 = st.columns(2)
            col1.write(f"**Rendement de base de la fiche :** {nb_base} personne(s)")
            col2.write(f"**Frais fixes associés :** {recette['frais_fixes']:.2f} €")

            if ingredients:
                # Affichage des quantités TOTALES basées sur le rendement de la fiche
                data = []
                for i in ingredients:
                    qte_totale = i['quantite_par_personne'] * nb_base
                    data.append({
                        "Ingrédient": i['produits']['nom'], 
                        f"Qté totale (pour {nb_base} pers)": f"{qte_totale:.3f} {i['produits']['unite']}", 
                        "Qté unitaire / pers": f"{i['quantite_par_personne']:.3f} {i['produits']['unite']}", 
                        "Coût / pers": f"{i['quantite_par_personne'] * i['produits']['prix_achat']:.3f} €"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                
                st.markdown(f"**Gérer les quantités (Total pour {nb_base} convives)**")
                options_ing = {ing['produits']['nom']: ing for ing in ingredients}
                
                col_sel, col_qte, col_maj, col_sup = st.columns([2, 1.5, 1, 1])
                with col_sel:
                    ing_nom = st.selectbox("Sélectionner un ingrédient", list(options_ing.keys()), key=f"sel_{recette['id']}", label_visibility="collapsed")
                    ing_selectionne = options_ing[ing_nom]
                with col_qte:
                    # On affiche et modifie la quantité TOTALE
                    qte_totale_actuelle = float(ing_selectionne['quantite_par_personne']) * nb_base
                    nouvelle_qte_totale = st.number_input(f"Nouvelle Qté (pour {nb_base})", value=qte_totale_actuelle, step=0.01, format="%.3f", key=f"qte_{ing_selectionne['id']}")
                with col_maj:
                    if st.button("Mettre à jour", key=f"maj_{ing_selectionne['id']}", icon=":material/edit:", use_container_width=True):
                        # Le système redivise par le nombre de base pour l'enregistrement
                        nouvelle_qte_pers = nouvelle_qte_totale / nb_base
                        modifier_quantite_ingredient(ing_selectionne['id'], nouvelle_qte_pers)
                        st.rerun()
                with col_sup:
                    if st.button("Supprimer", key=f"sup_{ing_selectionne['id']}", icon=":material/delete:", use_container_width=True):
                        supprimer_ingredient(ing_selectionne['id'])
                        st.rerun()
            else:
                st.info("Aucun ingrédient associé à cette recette.")

            st.divider()

            st.markdown(f"**Ajouter un ingrédient (Saisissez la quantité totale pour {nb_base} personnes)**")
            produits = get_tous_produits()
            if produits:
                options_prod = {p['nom']: p for p in produits}
                produit_choisi = st.selectbox("Sélectionner un produit", list(options_prod.keys()), key=f"prod_{recette['id']}")
                unite = options_prod[produit_choisi]['unite']

                with st.form(f"form_add_{recette['id']}"):
                    qte_totale = st.number_input(f"Quantité totale de l'ingrédient pour la fiche ({unite})", min_value=0.001, step=0.001, format="%.3f")
                    
                    if st.form_submit_button("Ajouter l'ingrédient", icon=":material/add:"):
                        # Divise automatiquement la quantité totale saisie par la taille de la recette
                        qte_unitaire = qte_totale / nb_base
                        ajouter_ingredient(recette['id'], options_prod[produit_choisi]['id'], qte_unitaire)
                        st.rerun()

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("Modifier les informations de la recette"):
                    with st.form(f"form_modif_{recette['id']}"):
                        nouveau_nom = st.text_input("Nom", value=recette['nom'])
                        nouveau_nb_base = st.number_input("Rendement (Pour combien de personnes ?)", min_value=1, value=int(nb_base), step=1)
                        nouvelle_desc = st.text_area("Description", value=recette['description'] or "")
                        nouveaux_frais = st.number_input("Frais fixes (€)", value=float(recette['frais_fixes']), step=10.0)
                        if st.form_submit_button("Enregistrer", icon=":material/save:"):
                            modifier_recette(recette['id'], nouveau_nom, nouvelle_desc, nouveaux_frais, nouveau_nb_base)
                            st.rerun()
            with col2:
                if st.button("Supprimer cette recette", icon=":material/delete:", key=f"del_rec_{recette['id']}", use_container_width=True):
                    supprimer_recette(recette['id'])
                    st.rerun()

st.write("")
with st.container(border=True):
    st.subheader("Créer une nouvelle fiche recette")
    with st.form("form_nouvelle_recette"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Intitulé de la recette", placeholder="Ex. : Couscous Royal")
            nb_personnes_base = st.number_input("Rendement (Pour combien de personnes ?)", min_value=1, value=1, step=1, help="Précisez la quantité de base de votre recette (ex: marmite pour 10 personnes).")
        with col2:
            frais_fixes = st.number_input("Frais fixes spécifiques (€)", min_value=0.0, step=10.0)
            description = st.text_area("Notes ou description")
        if st.form_submit_button("Créer la fiche", icon=":material/add:", use_container_width=True):
            if nom:
                ajouter_recette(nom, description, frais_fixes, nb_personnes_base)
                st.rerun()
            else:
                st.error("L'intitulé est obligatoire.")
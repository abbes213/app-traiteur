import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables

créer_tables()

st.set_page_config(page_title="Gestion des Recettes", page_icon="📋")
st.title("📋 Gestion des Recettes")

supabase = get_client()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
def get_toutes_recettes():
    res = supabase.table("recettes").select("*").order("nom").execute()
    return res.data


def get_tous_produits():
    res = supabase.table("produits").select("*").order("nom").execute()
    return res.data

def get_ingredients_recette(recette_id):
    res = supabase.table("recette_ingredients")\
        .select("*, produits(nom, unite, prix_achat)")\
        .eq("recette_id", recette_id).execute()
    return res.data

def ajouter_recette(nom, description, frais_fixes):
    res = supabase.table("recettes").insert({
        "nom": nom,
        "description": description,
        "frais_fixes": frais_fixes
    }).execute()
    return res.data[0]['id']

def modifier_recette(id, nom, description, frais_fixes):
    supabase.table("recettes").update({
        "nom": nom,
        "description": description,
        "frais_fixes": frais_fixes
    }).eq("id", id).execute()

def supprimer_recette(recette_id):
    supabase.table("recette_ingredients").delete().eq("recette_id", recette_id).execute()
    supabase.table("recettes").delete().eq("id", recette_id).execute()

def ajouter_ingredient(recette_id, produit_id, quantite_par_personne):
    supabase.table("recette_ingredients").insert({
        "recette_id": recette_id,
        "produit_id": produit_id,
        "quantite_par_personne": quantite_par_personne
    }).execute()

def supprimer_ingredient(ingredient_id):
    supabase.table("recette_ingredients").delete().eq("id", ingredient_id).execute()

def calculer_cout_par_personne(ingredients):
    cout = 0
    for ing in ingredients:
        cout += ing['quantite_par_personne'] * ing['produits']['prix_achat']
    return cout


# ─────────────────────────────────────────────
# LISTE DES RECETTES
# ─────────────────────────────────────────────

recettes = get_toutes_recettes()

if not recettes:
    st.info("Aucune recette enregistrée. Créez votre première recette !")
else:
    st.subheader(f"📋 {len(recettes)} Recette(s) enregistrée(s)")

    for recette in recettes:
        ingredients       = get_ingredients_recette(recette['id'])
        cout_par_personne = calculer_cout_par_personne(ingredients)

        with st.expander(
            f"📋 {recette['nom']} — "
            f"{len(ingredients)} ingrédient(s) — "
            f"~{cout_par_personne:.2f} € / personne"
        ):
            st.write(f"**Description :** {recette['description'] or 'Aucune'}")
            st.write(f"**Frais fixes :** {recette['frais_fixes']} €")
            st.write(f"**Coût ingrédients / personne :** {cout_par_personne:.2f} €")

            if ingredients:
                st.write("**Ingrédients :**")
                data = []
                for ing in ingredients:
                    data.append({
                        "Ingrédient"          : ing['produits']['nom'],
                        "Quantité / personne" : f"{ing['quantite_par_personne']} {ing['produits']['unite']}",
                        "Prix achat"          : f"{ing['produits']['prix_achat']} €",
                        "Coût / personne"     : f"{ing['quantite_par_personne'] * ing['produits']['prix_achat']:.3f} €"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                st.write("**Supprimer un ingrédient :**")
                options_ing = {
                    ing['produits']['nom']: ing['id']
                    for ing in ingredients
                }
                ing_a_supprimer = st.selectbox(
                    "Choisir l'ingrédient à supprimer",
                    list(options_ing.keys()),
                    key=f"sup_ing_{recette['id']}"
                )
                if st.button(
                    f"🗑️ Supprimer {ing_a_supprimer}",
                    key=f"btn_sup_ing_{recette['id']}"
                ):
                    supprimer_ingredient(options_ing[ing_a_supprimer])
                    st.success("✅ Ingrédient supprimé !")
                    st.rerun()
            else:
                st.info("Aucun ingrédient encore. Ajoutez-en ci-dessous.")

            # Ajouter un ingrédient
            st.write("**➕ Ajouter un ingrédient :**")
            produits = get_tous_produits()

            if not produits:
                st.warning("⚠️ Ajoutez d'abord des produits dans le stock !")
            else:
                options_prod = {p['nom']: p for p in produits}

                                # Sélection produit EN DEHORS du form
                produit_choisi = st.selectbox(
                    "Produit",
                    list(options_prod.keys()),
                    key=f"select_{recette['id']}"
                )
                unite = options_prod[produit_choisi]['unite']

                with st.form(f"form_add_ing_{recette['id']}"):
                    qte = st.number_input(
                        f"Quantité / personne ({unite})",  # ← unité correcte ✅
                        min_value=0.001,
                        step=0.001,
                        format="%.3f"
                    )
                    if st.form_submit_button("➕ Ajouter", use_container_width=True):
                        ajouter_ingredient(
                            recette['id'],
                            options_prod[produit_choisi]['id'],
                            qte
                        )
                        st.success(f"✅ **{produit_choisi}** ajouté !")
                        st.rerun()

            st.divider()

            # Modifier / Supprimer recette
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("✏️ Modifier cette recette"):
                    with st.form(f"form_modif_{recette['id']}"):
                        nouveau_nom    = st.text_input("Nom", value=recette['nom'])
                        nouvelle_desc  = st.text_area("Description", value=recette['description'] or "")
                        nouveaux_frais = st.number_input(
                            "Frais fixes (€)",
                            value=float(recette['frais_fixes']),
                            step=10.0
                        )
                        if st.form_submit_button("💾 Sauvegarder"):
                            modifier_recette(recette['id'], nouveau_nom, nouvelle_desc, nouveaux_frais)
                            st.success("✅ Recette modifiée !")
                            st.rerun()

            with col2:
                if st.button(
                    "🗑️ Supprimer cette recette",
                    key=f"sup_rec_{recette['id']}"
                ):
                    supprimer_recette(recette['id'])
                    st.success("✅ Recette supprimée !")
                    st.rerun()

st.divider()

# ─────────────────────────────────────────────
# CRÉER UNE NOUVELLE RECETTE
# ─────────────────────────────────────────────

st.subheader("➕ Créer une nouvelle recette")

with st.form("form_nouvelle_recette"):
    col1, col2 = st.columns(2)

    with col1:
        nom         = st.text_input("Nom de la recette", placeholder="ex: Menu Mariage Oriental")
        description = st.text_area("Description")

    with col2:
        frais_fixes = st.number_input("Frais fixes (€)", min_value=0.0, step=10.0)

    if st.form_submit_button("✅ Créer la recette", use_container_width=True):
        if not nom:
            st.error("❌ Le nom est obligatoire !")
        else:
            ajouter_recette(nom, description, frais_fixes)
            st.success(f"✅ Recette **{nom}** créée !")
            st.rerun()
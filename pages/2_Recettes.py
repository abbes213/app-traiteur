import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_connection, créer_tables

créer_tables()

st.set_page_config(page_title="Gestion des Recettes", page_icon="📋")
# Vérification de la sécurité (À PLACER EXACTEMENT ICI)
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")
st.title("📋 Gestion des Recettes")

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_toutes_recettes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recettes ORDER BY nom")
    recettes = cursor.fetchall()
    conn.close()
    return recettes


def get_tous_produits():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits ORDER BY nom")
    produits = cursor.fetchall()
    conn.close()
    return produits


def get_ingredients_recette(recette_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ri.id, p.nom, p.unite, p.prix_achat,
               ri.quantite_par_personne, ri.produit_id
        FROM recette_ingredients ri
        JOIN produits p ON ri.produit_id = p.id
        WHERE ri.recette_id = ?
        ORDER BY p.nom
    """, (recette_id,))
    ingredients = cursor.fetchall()
    conn.close()
    return ingredients


def ajouter_recette(nom, description, frais_fixes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recettes (nom, description, frais_fixes)
        VALUES (?, ?, ?)
    """, (nom, description, frais_fixes))
    recette_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return recette_id


def ajouter_ingredient(recette_id, produit_id, quantite_par_personne):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recette_ingredients (recette_id, produit_id, quantite_par_personne)
        VALUES (?, ?, ?)
    """, (recette_id, produit_id, quantite_par_personne))
    conn.commit()
    conn.close()


def supprimer_ingredient(ingredient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recette_ingredients WHERE id = ?", (ingredient_id,))
    conn.commit()
    conn.close()


def modifier_recette(id, nom, description, frais_fixes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE recettes
        SET nom = ?, description = ?, frais_fixes = ?
        WHERE id = ?
    """, (nom, description, frais_fixes, id))
    conn.commit()
    conn.close()


def supprimer_recette(recette_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recette_ingredients WHERE recette_id = ?", (recette_id,))
    cursor.execute("DELETE FROM recettes WHERE id = ?", (recette_id,))
    conn.commit()
    conn.close()


def calculer_cout_par_personne(recette_id):
    """Calcule le coût des ingrédients pour 1 personne"""
    ingredients = get_ingredients_recette(recette_id)
    cout = 0
    for ing in ingredients:
        cout += ing['quantite_par_personne'] * ing['prix_achat']
    return cout


# ─────────────────────────────────────────────
# AFFICHAGE LISTE DES RECETTES
# ─────────────────────────────────────────────

recettes = get_toutes_recettes()

if not recettes:
    st.info("Aucune recette enregistrée. Créez votre première recette !")
else:
    st.subheader(f"📋 {len(recettes)} Recette(s) enregistrée(s)")

    for recette in recettes:
        cout_personne = calculer_cout_par_personne(recette['id'])
        ingredients = get_ingredients_recette(recette['id'])

        with st.expander(
            f"📋 {recette['nom']} — "
            f"{len(ingredients)} ingrédient(s) — "
            f"~{cout_personne:.2f} € / personne"
        ):
            st.write(f"**Description :** {recette['description'] or 'Aucune'}")
            st.write(f"**Frais fixes :** {recette['frais_fixes']} €")
            st.write(f"**Coût ingrédients / personne :** {cout_personne:.2f} €")

            # Tableau des ingrédients
            if ingredients:
                st.write("**Ingrédients :**")
                data = []
                for ing in ingredients:
                    data.append({
                        "Ingrédient"          : ing['nom'],
                        "Quantité / personne" : f"{ing['quantite_par_personne']} {ing['unite']}",
                        "Prix achat"          : f"{ing['prix_achat']} €",
                        "Coût / personne"     : f"{ing['quantite_par_personne'] * ing['prix_achat']:.3f} €"
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Supprimer un ingrédient
                st.write("**Supprimer un ingrédient :**")
                options_ing = {
                    f"{ing['nom']}" : ing['id']
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
                    st.success(f"✅ Ingrédient supprimé !")
                    st.rerun()
            else:
                st.info("Aucun ingrédient encore. Ajoutez-en ci-dessous.")

            # Ajouter un ingrédient à cette recette
            st.write("**➕ Ajouter un ingrédient :**")
            produits = get_tous_produits()

            if not produits:
                st.warning("⚠️ Ajoutez d'abord des produits dans le stock !")
            else:
                options_prod = {p['nom']: p for p in produits}
                unites = {p['nom']: p['unite'] for p in produits}

                with st.form(f"form_add_ing_{recette['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        produit_choisi = st.selectbox(
                            "Produit",
                            list(options_prod.keys())
                        )
                    with col2:
                        qte = st.number_input(
                            f"Quantité / personne ({unites[produit_choisi]})",
                            min_value=0.001,
                            step=0.001,
                            format="%.3f"
                        )
                    if st.form_submit_button("➕ Ajouter", use_container_width=True):
                        produit_id = options_prod[produit_choisi]['id']
                        ajouter_ingredient(recette['id'], produit_id, qte)
                        st.success(
                            f"✅ **{produit_choisi}** ajouté "
                            f"({qte} {unites[produit_choisi]} / personne)"
                        )
                        st.rerun()

            st.divider()

            # Modifier / Supprimer la recette
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("✏️ Modifier cette recette"):
                    with st.form(f"form_modif_{recette['id']}"):
                        nouveau_nom = st.text_input("Nom", value=recette['nom'])
                        nouvelle_desc = st.text_area("Description", value=recette['description'] or "")
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
                    f"🗑️ Supprimer cette recette",
                    key=f"sup_rec_{recette['id']}",
                    type="secondary"
                ):
                    supprimer_recette(recette['id'])
                    st.success("✅ Recette supprimée !")
                    st.rerun()

st.divider()

# ─────────────────────────────────────────────
# AJOUTER UNE NOUVELLE RECETTE
# ─────────────────────────────────────────────

st.subheader("➕ Créer une nouvelle recette")

with st.form("form_nouvelle_recette"):
    col1, col2 = st.columns(2)

    with col1:
        nom         = st.text_input("Nom de la recette", placeholder="ex: Menu Mariage Oriental")
        description = st.text_area("Description", placeholder="ex: Menu complet avec entrée, plat et dessert")

    with col2:
        frais_fixes = st.number_input(
            "Frais fixes (€)",
            min_value=0.0,
            step=10.0,
            help="Location salle, décoration, transport..."
        )

    submitted = st.form_submit_button("✅ Créer la recette", use_container_width=True)

    if submitted:
        if not nom:
            st.error("❌ Le nom de la recette est obligatoire !")
        else:
            ajouter_recette(nom, description, frais_fixes)
            st.success(
                f"✅ Recette **{nom}** créée ! "
                f"Maintenant ajoutez ses ingrédients ci-dessus."
            )
            st.rerun()
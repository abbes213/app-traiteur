import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables

créer_tables()

st.set_page_config(page_title="Gestion du Stock", page_icon="📦")
st.title("📦 Gestion du Stock")

supabase = get_client()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_tous_produits():
    res = supabase.table("produits").select("*").order("nom").execute()
    return res.data

def ajouter_produit(nom, unite, prix_achat, quantite, seuil):
    supabase.table("produits").insert({
        "nom": nom,
        "unite": unite,
        "prix_achat": prix_achat,
        "quantite_stock": quantite,
        "seuil_alerte": seuil
    }).execute()

def modifier_produit(id, nom, unite, prix_achat, quantite, seuil):
    supabase.table("produits").update({
        "nom": nom,
        "unite": unite,
        "prix_achat": prix_achat,
        "quantite_stock": quantite,
        "seuil_alerte": seuil
    }).eq("id", id).execute()

def supprimer_produit(id):
    # 1. On supprime d'abord les liaisons de ce produit dans les recettes
    supabase.table("recette_ingredients").delete().eq("produit_id", id).execute()
    
    # 2. On peut ensuite supprimer le produit du stock en toute sécurité
    supabase.table("produits").delete().eq("id", id).execute()

def reception_stock(produit_id, quantite_achetee, nouveau_prix):
    produit = supabase.table("produits").select("quantite_stock").eq("id", produit_id).execute()
    ancienne_qte = produit.data[0]['quantite_stock']
    nouvelle_qte = ancienne_qte + quantite_achetee

    supabase.table("produits").update({
        "quantite_stock": nouvelle_qte,
        "prix_achat": nouveau_prix
    }).eq("id", produit_id).execute()

    supabase.table("achats_stock").insert({
        "produit_id": produit_id,
        "quantite_achetee": quantite_achetee,
        "prix_achat": nouveau_prix
    }).execute()

def get_alertes():
    produits = supabase.table("produits").select("*").execute()
    return [p for p in produits.data if p['quantite_stock'] <= p['seuil_alerte']]


# ─────────────────────────────────────────────
# ALERTES
# ─────────────────────────────────────────────

alertes = get_alertes()
if alertes:
    st.error("⚠️ PRODUITS À RÉAPPROVISIONNER :")
    for a in alertes:
        st.warning(
            f"🔴 **{a['nom']}** — "
            f"Stock actuel : {a['quantite_stock']} {a['unite']} "
            f"(seuil minimum : {a['seuil_alerte']} {a['unite']})"
        )
    st.divider()

# ─────────────────────────────────────────────
# TABLEAU DU STOCK
# ─────────────────────────────────────────────

st.subheader("📋 État du Stock")

produits = get_tous_produits()

if not produits:
    st.info("Aucun produit dans le stock. Ajoutez votre premier produit !")
else:
    data = []
    for p in produits:
        if p['quantite_stock'] == 0:
            statut = "🔴 Rupture"
        elif p['quantite_stock'] <= p['seuil_alerte']:
            statut = "🟠 Faible"
        else:
            statut = "🟢 OK"

        data.append({
            "Produit"      : p['nom'],
            "Unité"        : p['unite'],
            "Prix Achat"   : f"{p['prix_achat']} €",
            "Quantité"     : p['quantite_stock'],
            "Seuil Alerte" : p['seuil_alerte'],
            "Statut"       : statut,
            "Dernière MAJ" : p['date_maj']
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    excel_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exporter en Excel",
        data=excel_data,
        file_name="stock_traiteur.csv",
        mime="text/csv"
    )

st.divider()

# ─────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "➕ Ajouter un produit",
    "📦 Réception stock",
    "✏️ Modifier / Supprimer"
])

# ── ONGLET 1 ──
with tab1:
    st.subheader("➕ Ajouter un nouveau produit")

    with st.form("form_ajouter"):
        col1, col2 = st.columns(2)

        with col1:
            nom        = st.text_input("Nom du produit", placeholder="ex: Poulet")
            unite      = st.selectbox("Unité", ["kg", "litre", "pièce", "gramme", "cl", "autre"])
            prix_achat = st.number_input("Prix d'achat (€)", min_value=0.0, step=0.01)

        with col2:
            quantite = st.number_input("Quantité initiale", min_value=0.0, step=0.1)
            seuil    = st.number_input("Seuil d'alerte minimum", min_value=0.0, step=0.1)

        submitted = st.form_submit_button("✅ Ajouter le produit", use_container_width=True)

        if submitted:
            if not nom:
                st.error("❌ Le nom du produit est obligatoire !")
            elif prix_achat <= 0:
                st.error("❌ Le prix d'achat doit être supérieur à 0 !")
            else:
                ajouter_produit(nom, unite, prix_achat, quantite, seuil)
                st.success(f"✅ Produit **{nom}** ajouté avec succès !")
                st.rerun()

# ── ONGLET 2 ──
with tab2:
    st.subheader("📦 Réception de nouveaux achats")

    produits = get_tous_produits()

    if not produits:
        st.info("Ajoutez d'abord des produits dans le stock.")
    else:
        options       = {p['nom']: p for p in produits}
        produit_choisi = st.selectbox("Produit reçu", list(options.keys()))

        produit_selectionne = options[produit_choisi]
        unite_actuelle      = produit_selectionne['unite']
        prix_actuel         = produit_selectionne['prix_achat']

        with st.form("form_reception"):
            col1, col2 = st.columns(2)
            with col1:
                qte_recue = st.number_input(
                    f"Quantité reçue ({unite_actuelle})",
                    min_value=0.1, step=0.1
                )
            with col2:
                nouveau_prix = st.number_input(
                    "Nouveau prix d'achat (€)",
                    min_value=0.0, step=0.01,
                    value=float(prix_actuel)
                )

            submitted2 = st.form_submit_button(
                "✅ Confirmer la réception",
                use_container_width=True
            )

            if submitted2:
                reception_stock(
                    produit_selectionne['id'],
                    qte_recue,
                    nouveau_prix
                )
                st.success(
                    f"✅ **{qte_recue} {unite_actuelle}** de "
                    f"**{produit_choisi}** ajoutés au stock !"
                )
                st.rerun()

# ── ONGLET 3 ──
with tab3:
    st.subheader("✏️ Modifier ou Supprimer un produit")

    produits = get_tous_produits()

    if not produits:
        st.info("Aucun produit à modifier.")
    else:
        options        = {p['nom']: p for p in produits}
        produit_choisi = st.selectbox("Choisir un produit", list(options.keys()))
        p              = options[produit_choisi]

        with st.form("form_modifier"):
            col1, col2 = st.columns(2)

            with col1:
                nouveau_nom    = st.text_input("Nom", value=p['nom'])
                nouvelle_unite = st.selectbox(
                    "Unité",
                    ["kg", "litre", "pièce", "gramme", "cl", "autre"],
                    index=["kg", "litre", "pièce", "gramme", "cl", "autre"].index(p['unite'])
                    if p['unite'] in ["kg", "litre", "pièce", "gramme", "cl", "autre"] else 0
                )
                nouveau_prix = st.number_input(
                    "Prix d'achat (€)",
                    value=float(p['prix_achat']),
                    step=0.01
                )

            with col2:
                nouvelle_qte   = st.number_input(
                    "Quantité",
                    value=float(p['quantite_stock']),
                    step=0.1
                )
                nouveau_seuil  = st.number_input(
                    "Seuil alerte",
                    value=float(p['seuil_alerte']),
                    step=0.1
                )

            col_mod, col_sup = st.columns(2)

            with col_mod:
                if st.form_submit_button("💾 Sauvegarder", use_container_width=True):
                    modifier_produit(
                        p['id'], nouveau_nom, nouvelle_unite,
                        nouveau_prix, nouvelle_qte, nouveau_seuil
                    )
                    st.success(f"✅ Produit **{nouveau_nom}** modifié !")
                    st.rerun()

            with col_sup:
                if st.form_submit_button("🗑️ Supprimer", use_container_width=True):
                    supprimer_produit(p['id'])
                    st.success(f"✅ Produit **{p['nom']}** supprimé !")
                    st.rerun()
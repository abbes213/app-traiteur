import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables

créer_tables()

st.set_page_config(page_title="Gestion du Stock", page_icon=":material/inventory_2:", layout="wide")

# Vérification sécurité
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

# ── SKILL FRONTEND-DESIGN : Typographie, Palette & Composants sur-mesure ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stApp {
    background-color: #F8FAFC;
}

h1, h2, h3 {
    color: #0F172A !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    padding: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.stButton > button[kind="primary"] {
    background-color: #0F172A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Gestion du stock")
st.caption("Inventaire des matières premières, suivi des seuils d'alerte et réceptions fournisseurs.")

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
    supabase.table("recette_ingredients").delete().eq("produit_id", id).execute()
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
    with st.container(border=True):
        st.error("Produits nécessitant un réapprovisionnement :")
        for a in alertes:
            st.warning(
                f"**{a['nom']}** — "
                f"Stock actuel : {a['quantite_stock']} {a['unite']} "
                f"(Seuil minimum : {a['seuil_alerte']} {a['unite']})"
            )

# ─────────────────────────────────────────────
# TABLEAU DU STOCK
# ─────────────────────────────────────────────

with st.container(border=True):
    st.subheader("État de l'inventaire")

    produits = get_tous_produits()

    if not produits:
        st.info("Aucun produit enregistré dans le stock.")
    else:
        data = []
        for p in produits:
            if p['quantite_stock'] == 0:
                statut = "Rupture"
            elif p['quantite_stock'] <= p['seuil_alerte']:
                statut = "Stock faible"
            else:
                statut = "Disponible"

            data.append({
                "Produit"      : p['nom'],
                "Unité"        : p['unite'],
                "Prix d'achat" : f"{p['prix_achat']:.2f} €",
                "Quantité"     : p['quantite_stock'],
                "Seuil alerte" : p['seuil_alerte'],
                "Statut"       : statut,
                "Dernière MAJ" : p['date_maj']
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        excel_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Exporter l'inventaire (CSV)",
            data=excel_data,
            file_name="stock_traiteur.csv",
            mime="text/csv",
            icon=":material/download:"
        )

st.write("")

# ─────────────────────────────────────────────
# ONGLETS
# ─────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "Ajouter un produit",
    "Réception de stock",
    "Modifier ou supprimer"
])

# ── ONGLET 1 ──
with tab1:
    with st.container(border=True):
        st.subheader("Référencer un nouveau produit")

        with st.form("form_ajouter"):
            col1, col2 = st.columns(2)

            with col1:
                nom        = st.text_input("Désignation du produit", placeholder="Ex. : Poulet, Crème liquide...")
                unite      = st.selectbox("Unité de mesure", ["kg", "litre", "pièce", "gramme", "cl", "portion", "dose", "autre"])
                prix_achat = st.number_input("Prix d'achat unitaire (€)", min_value=0.0, step=0.01)

            with col2:
                quantite = st.number_input("Quantité initiale en stock", min_value=0.0, step=0.1)
                seuil    = st.number_input("Seuil d'alerte minimum", min_value=0.0, step=0.1)

            submitted = st.form_submit_button("Ajouter au catalogue", icon=":material/add:", use_container_width=True)

            if submitted:
                if not nom:
                    st.error("Le nom du produit est obligatoire.")
                elif prix_achat <= 0:
                    st.error("Le prix d'achat doit être supérieur à 0.")
                else:
                    ajouter_produit(nom, unite, prix_achat, quantite, seuil)
                    st.success(f"Le produit **{nom}** a été ajouté.")
                    st.rerun()

# ── ONGLET 2 ──
with tab2:
    with st.container(border=True):
        st.subheader("Enregistrer une livraison fournisseur")

        produits = get_tous_produits()

        if not produits:
            st.info("Ajoutez d'abord des produits dans le stock.")
        else:
            options        = {p['nom']: p for p in produits}
            produit_choisi = st.selectbox("Produit réceptionné", list(options.keys()))

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
                        "Nouveau prix d'achat unitaire (€)",
                        min_value=0.0, step=0.01,
                        value=float(prix_actuel)
                    )

                submitted2 = st.form_submit_button(
                    "Valider la réception",
                    icon=":material/check_circle:",
                    use_container_width=True
                )

                if submitted2:
                    reception_stock(
                        produit_selectionne['id'],
                        qte_recue,
                        nouveau_prix
                    )
                    st.success(
                        f"**{qte_recue} {unite_actuelle}** de "
                        f"**{produit_choisi}** ajoutés au stock."
                    )
                    st.rerun()

# ── ONGLET 3 ──
with tab3:
    with st.container(border=True):
        st.subheader("Modifier ou supprimer une référence")

        produits = get_tous_produits()

        if not produits:
            st.info("Aucun produit à modifier.")
        else:
            options        = {p['nom']: p for p in produits}
            produit_choisi = st.selectbox("Sélectionner un produit", list(options.keys()))
            p              = options[produit_choisi]

            unites_dispo = ["kg", "litre", "pièce", "gramme", "cl", "portion", "dose", "autre"]

            with st.form("form_modifier"):
                col1, col2 = st.columns(2)

                with col1:
                    nouveau_nom    = st.text_input("Nom", value=p['nom'])
                    nouvelle_unite = st.selectbox(
                        "Unité",
                        unites_dispo,
                        index=unites_dispo.index(p['unite']) if p['unite'] in unites_dispo else 0
                    )
                    nouveau_prix = st.number_input(
                        "Prix d'achat (€)",
                        value=float(p['prix_achat']),
                        step=0.01
                    )

                with col2:
                    nouvelle_qte  = st.number_input(
                        "Quantité en stock",
                        value=float(p['quantite_stock']),
                        step=0.1
                    )
                    nouveau_seuil = st.number_input(
                        "Seuil d'alerte",
                        value=float(p['seuil_alerte']),
                        step=0.1
                    )

                col_mod, col_sup = st.columns(2)

                with col_mod:
                    if st.form_submit_button("Enregistrer les modifications", icon=":material/save:", use_container_width=True):
                        modifier_produit(
                            p['id'], nouveau_nom, nouvelle_unite,
                            nouveau_prix, nouvelle_qte, nouveau_seuil
                        )
                        st.success(f"Le produit **{nouveau_nom}** a été mis à jour.")
                        st.rerun()

                with col_sup:
                    if st.form_submit_button("Supprimer le produit", icon=":material/delete:", use_container_width=True):
                        supprimer_produit(p['id'])
                        st.success(f"Le produit **{p['nom']}** a été supprimé.")
                        st.rerun()
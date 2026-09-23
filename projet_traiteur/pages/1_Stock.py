import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_connection, créer_tables

# Initialisation base de données
créer_tables()

st.set_page_config(page_title="Gestion du Stock", page_icon="📦")
# Vérification de la sécurité (À PLACER EXACTEMENT ICI)
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")
st.title("📦 Gestion du Stock")

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────

def get_tous_produits():
    """Récupère tous les produits du stock"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produits ORDER BY nom")
    produits = cursor.fetchall()
    conn.close()
    return produits


def ajouter_produit(nom, unite, prix_achat, quantite, seuil):
    """Ajoute un nouveau produit dans le stock"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO produits (nom, unite, prix_achat, quantite_stock, seuil_alerte)
        VALUES (?, ?, ?, ?, ?)
    """, (nom, unite, prix_achat, quantite, seuil))
    conn.commit()
    conn.close()


def modifier_produit(id, nom, unite, prix_achat, quantite, seuil):
    """Modifie un produit existant"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE produits
        SET nom = ?, unite = ?, prix_achat = ?,
            quantite_stock = ?, seuil_alerte = ?,
            date_maj = date('now')
        WHERE id = ?
    """, (nom, unite, prix_achat, quantite, seuil, id))
    conn.commit()
    conn.close()


def supprimer_produit(id):
    """Supprime un produit"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produits WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def reception_stock(produit_id, quantite_achetee, nouveau_prix):
    """Réception d'un achat — augmente le stock"""
    conn = get_connection()
    cursor = conn.cursor()

    # Mise à jour quantité et prix dans produits
    cursor.execute("""
        UPDATE produits
        SET quantite_stock = quantite_stock + ?,
            prix_achat = ?,
            date_maj = date('now')
        WHERE id = ?
    """, (quantite_achetee, nouveau_prix, produit_id))

    # Sauvegarde dans historique achats
    cursor.execute("""
        INSERT INTO achats_stock (produit_id, quantite_achetee, prix_achat)
        VALUES (?, ?, ?)
    """, (produit_id, quantite_achetee, nouveau_prix))

    conn.commit()
    conn.close()


def get_alertes():
    """Retourne les produits sous le seuil d'alerte"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM produits
        WHERE quantite_stock <= seuil_alerte
        ORDER BY quantite_stock ASC
    """)
    alertes = cursor.fetchall()
    conn.close()
    return alertes


# ─────────────────────────────────────────────
# AFFICHAGE DES ALERTES EN HAUT DE PAGE
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
    # Construction du tableau
    data = []
    for p in produits:
        # Définir le statut selon le stock
        if p['quantite_stock'] == 0:
            statut = "🔴 Rupture"
        elif p['quantite_stock'] <= p['seuil_alerte']:
            statut = "🟠 Faible"
        else:
            statut = "🟢 OK"

        data.append({
            "Produit"       : p['nom'],
            "Unité"         : p['unite'],
            "Prix Achat"    : f"{p['prix_achat']} €",
            "Quantité"      : p['quantite_stock'],
            "Seuil Alerte"  : p['seuil_alerte'],
            "Statut"        : statut,
            "Dernière MAJ"  : p['date_maj']
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Bouton export Excel
    excel_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exporter en Excel",
        data=excel_data,
        file_name="stock_traiteur.csv",
        mime="text/csv"
    )

st.divider()

# ─────────────────────────────────────────────
# LES 3 ONGLETS D'ACTIONS
# ─────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "➕ Ajouter un produit",
    "📦 Réception stock",
    "✏️ Modifier / Supprimer"
])

# ──────────────────────────────
# ONGLET 1 — Ajouter un produit
# ──────────────────────────────
with tab1:
    st.subheader("➕ Ajouter un nouveau produit")

    with st.form("form_ajouter"):
        col1, col2 = st.columns(2)

        with col1:
            nom         = st.text_input("Nom du produit", placeholder="ex: Poulet")
            unite       = st.selectbox("Unité", ["kg", "litre", "pièce", "gramme", "cl", "autre"])
            prix_achat  = st.number_input("Prix d'achat (€)", min_value=0.0, step=0.01)

        with col2:
            quantite    = st.number_input("Quantité initiale", min_value=0.0, step=0.1)
            seuil       = st.number_input("Seuil d'alerte minimum", min_value=0.0, step=0.1)

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

# ──────────────────────────────────
# ONGLET 2 — Réception de stock
# ──────────────────────────────────
with tab2:
    st.subheader("📦 Réception de nouveaux achats")

    produits = get_tous_produits()

    if not produits:
        st.info("Ajoutez d'abord des produits dans le stock.")
    else:
        options  = {p['nom']: p for p in produits}

        # ← selectbox EN DEHORS du form pour mise à jour en temps réel
        produit_choisi = st.selectbox("Produit reçu", list(options.keys()))

        produit_selectionne = options[produit_choisi]
        unite_actuelle      = produit_selectionne['unite']
        prix_actuel         = produit_selectionne['prix_achat']

        with st.form("form_reception"):
            col1, col2 = st.columns(2)
            with col1:
                qte_recue = st.number_input(
                    f"Quantité reçue ({unite_actuelle})",  # ← unité correcte ✅
                    min_value=0.1,
                    step=0.1
                )
            with col2:
                nouveau_prix = st.number_input(
                    "Nouveau prix d'achat (€)",
                    min_value=0.01,
                    step=0.01,
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
                    f"**{produit_choisi}** ajoutés au stock ! "
                    f"Nouveau prix : {nouveau_prix} €"
                )
                st.rerun()
# ──────────────────────────────────────
# ONGLET 3 — Modifier / Supprimer
# ──────────────────────────────────────
with tab3:
    st.subheader("✏️ Modifier ou Supprimer un produit")

    produits = get_tous_produits()

    if not produits:
        st.info("Aucun produit à modifier.")
    else:
        options = {p['nom']: p for p in produits}
        produit_choisi = st.selectbox("Choisir un produit", list(options.keys()))
        p = options[produit_choisi]

        with st.form("form_modifier"):
            col1, col2 = st.columns(2)

            with col1:
                nouveau_nom     = st.text_input("Nom", value=p['nom'])
                nouvelle_unite  = st.selectbox(
                    "Unité",
                    ["kg", "litre", "pièce", "gramme", "cl", "autre"],
                    index=["kg", "litre", "pièce", "gramme", "cl", "autre"].index(p['unite'])
                    if p['unite'] in ["kg", "litre", "pièce", "gramme", "cl", "autre"] else 0
                )
                nouveau_prix    = st.number_input("Prix d'achat (€)", value=float(p['prix_achat']), step=0.01)

            with col2:
                nouvelle_qte    = st.number_input("Quantité", value=float(p['quantite_stock']), step=0.1)
                nouveau_seuil   = st.number_input("Seuil alerte", value=float(p['seuil_alerte']), step=0.1)

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
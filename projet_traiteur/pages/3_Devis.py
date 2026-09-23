import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_connection, créer_tables
from datetime import date
from modules.pdf_generator import generer_pdf_devis

créer_tables()

st.set_page_config(page_title="Générateur de Devis", page_icon="🧮")
# Vérification de la sécurité (À PLACER EXACTEMENT ICI)
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")
st.title("🧮 Générateur de Devis")

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


def get_ingredients_recette(recette_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ri.quantite_par_personne, p.nom,
               p.unite, p.prix_achat, p.id as produit_id
        FROM recette_ingredients ri
        JOIN produits p ON ri.produit_id = p.id
        WHERE ri.recette_id = ?
    """, (recette_id,))
    ingredients = cursor.fetchall()
    conn.close()
    return ingredients


def get_parametres():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parametres WHERE id = 1")
    params = cursor.fetchone()
    conn.close()
    return params


def get_recette(recette_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recettes WHERE id = ?", (recette_id,))
    recette = cursor.fetchone()
    conn.close()
    return recette


def calculer_devis(recette_id, nb_personnes, employes, frais_fixes_supplementaires):
    """Calcule le devis complet"""
    params      = get_parametres()
    ingredients = get_ingredients_recette(recette_id)
    recette     = get_recette(recette_id)

    # Coût ingrédients
    detail_ingredients = []
    cout_ingredients = 0
    for ing in ingredients:
        qte_totale  = ing['quantite_par_personne'] * nb_personnes
        cout        = qte_totale * ing['prix_achat']
        cout_ingredients += cout
        detail_ingredients.append({
            "Ingrédient"         : ing['nom'],
            "Qté / personne"     : f"{ing['quantite_par_personne']} {ing['unite']}",
            "Qté totale"         : f"{qte_totale:.2f} {ing['unite']}",
            "Prix achat"         : f"{ing['prix_achat']} €",
            "Coût total"         : f"{cout:.2f} €"
        })

    # Coût employés
    detail_employes = []
    cout_employes = 0
    taux_horaire = params['taux_horaire']
    for emp in employes:
        cout = emp['nombre'] * emp['heures'] * taux_horaire
        cout_employes += cout
        detail_employes.append({
            "Type"         : emp['type'],
            "Nb employés"  : emp['nombre'],
            "Nb heures"    : emp['heures'],
            "Taux horaire" : f"{taux_horaire} €/h",
            "Coût total"   : f"{cout:.2f} €"
        })

    # Frais fixes (recette + supplémentaires)
    frais_fixes_total = recette['frais_fixes'] + frais_fixes_supplementaires

    # Calcul final
    cout_total  = cout_ingredients + cout_employes + frais_fixes_total
    prix_final  = cout_total / params['taux_charges']
    benefice    = prix_final * params['taux_benefice']

    return {
        "cout_ingredients"           : cout_ingredients,
        "cout_employes"              : cout_employes,
        "frais_fixes_recette"        : recette['frais_fixes'],
        "frais_fixes_supplementaires": frais_fixes_supplementaires,
        "frais_fixes_total"          : frais_fixes_total,
        "cout_total"                 : cout_total,
        "prix_final"                 : prix_final,
        "benefice"                   : benefice,
        "detail_ingredients"         : detail_ingredients,
        "detail_employes"            : detail_employes,
        "taux_horaire"               : taux_horaire
    }


def sauvegarder_devis(nom_client, date_mariage, recette_id,
                       nb_personnes, employes, resultat, statut):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO devis (
            nom_client, date_mariage, recette_id, nb_personnes,
            cout_ingredients, cout_employes, frais_fixes,
            cout_total, prix_final, benefice, statut
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nom_client, str(date_mariage), recette_id, nb_personnes,
        resultat['cout_ingredients'], resultat['cout_employes'],
        resultat['frais_fixes_total'], resultat['cout_total'],
        resultat['prix_final'], resultat['benefice'], statut
    ))

    devis_id = cursor.lastrowid

    params = get_parametres()
    for emp in employes:
        cout = emp['nombre'] * emp['heures'] * params['taux_horaire']
        cursor.execute("""
            INSERT INTO employes_devis (devis_id, type_employe, nombre, heures, cout_total)
            VALUES (?, ?, ?, ?, ?)
        """, (devis_id, emp['type'], emp['nombre'], emp['heures'], cout))

    conn.commit()
    conn.close()
    return devis_id


def valider_mariage(devis_id, recette_id, nb_personnes):
    """Valide le mariage et met à jour le stock"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE devis SET statut = 'validé' WHERE id = ?
    """, (devis_id,))

    cursor.execute("""
        SELECT produit_id, quantite_par_personne
        FROM recette_ingredients
        WHERE recette_id = ?
    """, (recette_id,))
    ingredients = cursor.fetchall()

    for ing in ingredients:
        qte_utilisee = ing['quantite_par_personne'] * nb_personnes
        cursor.execute("""
            UPDATE produits
            SET quantite_stock = quantite_stock - ?,
                date_maj = date('now')
            WHERE id = ?
        """, (qte_utilisee, ing['produit_id']))

    conn.commit()
    conn.close()


def get_alertes_apres_validation():
    """Vérifie les alertes stock après validation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nom, p.quantite_stock, p.seuil_alerte, p.unite
        FROM produits p
        WHERE p.quantite_stock <= p.seuil_alerte
    """)
    alertes = cursor.fetchall()
    conn.close()
    return alertes


# ─────────────────────────────────────────────
# FORMULAIRE DEVIS
# ─────────────────────────────────────────────

recettes = get_toutes_recettes()

if not recettes:
    st.warning("⚠️ Aucune recette disponible. Créez d'abord des recettes !")
    st.stop()

# ── ÉTAPE 1 : Informations de base ──
st.subheader("1️⃣ Informations de base")

col1, col2 = st.columns(2)
with col1:
    nom_client   = st.text_input("Nom du client", placeholder="ex: M. Ahmed")
    date_mariage = st.date_input("Date du mariage", value=date.today())

with col2:
    options_recettes = {r['nom']: r for r in recettes}
    recette_choisie  = st.selectbox("Recette", list(options_recettes.keys()))
    nb_personnes     = st.number_input("Nombre de personnes", min_value=1, step=1, value=100)

recette = options_recettes[recette_choisie]

st.divider()

# ── ÉTAPE 2 : Employés ──
st.subheader("2️⃣ Employés")

if 'employes' not in st.session_state:
    st.session_state.employes = [
        {"type": "Serveurs",   "nombre": 1, "heures": 8},
        {"type": "Cuisiniers", "nombre": 1, "heures": 8}
    ]

params = get_parametres()

# En-tête des colonnes
col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
col1.markdown("**Type d'employé**")
col2.markdown("**Nb employés**")
col3.markdown("**Nb heures**")
col4.markdown("**Coût**")

employes_valides = []
for i, emp in enumerate(st.session_state.employes):
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
        type_emp = st.text_input(
            "Type", value=emp['type'],
            key=f"type_{i}",
            label_visibility="collapsed",
            placeholder="ex: Serveurs"
        )
    with col2:
        nb_emp = st.number_input(
            "Nb", value=emp['nombre'],
            min_value=1, key=f"nb_{i}",
            label_visibility="collapsed"
        )
    with col3:
        nb_h = st.number_input(
            "Heures", value=float(emp['heures']),
            min_value=1.0, step=0.5,
            key=f"h_{i}",
            label_visibility="collapsed"
        )
    with col4:
        cout_ligne = nb_emp * nb_h * params['taux_horaire']
        st.markdown(f"**{cout_ligne:.0f} €**")

    employes_valides.append({
        "type"   : type_emp,
        "nombre" : nb_emp,
        "heures" : nb_h
    })

col_add, col_reset = st.columns(2)
with col_add:
    if st.button("➕ Ajouter une ligne employé"):
        st.session_state.employes.append(
            {"type": "Autre", "nombre": 1, "heures": 8}
        )
        st.rerun()
with col_reset:
    if st.button("🗑️ Réinitialiser employés"):
        st.session_state.employes = [
            {"type": "Serveurs",   "nombre": 1, "heures": 8},
            {"type": "Cuisiniers", "nombre": 1, "heures": 8}
        ]
        st.rerun()

st.divider()

# ── ÉTAPE 3 : Frais supplémentaires ──
st.subheader("3️⃣ Frais supplémentaires")

col1, col2 = st.columns(2)
with col1:
    st.info(f"Frais fixes recette : **{recette['frais_fixes']} €**")
with col2:
    frais_supp = st.number_input(
        "Frais supplémentaires (€)",
        min_value=0.0, step=50.0,
        help="Transport, décoration supplémentaire..."
    )

st.divider()

# ─────────────────────────────────────────────
# CALCUL ET RÉSULTAT
# ─────────────────────────────────────────────

if st.button("🧮 CALCULER LE DEVIS", type="primary", use_container_width=True):
    if not nom_client:
        st.error("❌ Le nom du client est obligatoire !")
    else:
        resultat = calculer_devis(
            recette['id'], nb_personnes,
            employes_valides, frais_supp
        )
        st.session_state.resultat      = resultat
        st.session_state.devis_calcule = True
        st.session_state.nom_client    = nom_client
        st.session_state.date_mariage  = date_mariage
        st.session_state.recette_id    = recette['id']
        st.session_state.nb_personnes  = nb_personnes
        st.session_state.employes_snap = employes_valides

# ─────────────────────────────────────────────
# AFFICHAGE DU RÉSULTAT
# ─────────────────────────────────────────────

if st.session_state.get('devis_calcule'):
    r = st.session_state.resultat

    st.success("✅ Devis calculé avec succès !")
    st.subheader(
        f"📄 Devis — {st.session_state.nom_client} "
        f"— {st.session_state.nb_personnes} personnes"
    )

    # Résumé financier
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛒 Ingrédients", f"{r['cout_ingredients']:.2f} €")
    col2.metric("👨‍🍳 Employés",    f"{r['cout_employes']:.2f} €")
    col3.metric("📌 Frais fixes",  f"{r['frais_fixes_total']:.2f} €")
    col4.metric("💰 Coût total",   f"{r['cout_total']:.2f} €")

    st.divider()

    col1, col2 = st.columns(2)
    col1.metric("💵 Prix final client", f"{r['prix_final']:.2f} €")
    col2.metric("🤑 Votre bénéfice",   f"{r['benefice']:.2f} €")

    st.divider()

    # Détails
    with st.expander("🔍 Voir le détail des ingrédients"):
        df_ing = pd.DataFrame(r['detail_ingredients'])
        st.dataframe(df_ing, use_container_width=True, hide_index=True)

    with st.expander("🔍 Voir le détail des employés"):
        df_emp = pd.DataFrame(r['detail_employes'])
        st.dataframe(df_emp, use_container_width=True, hide_index=True)

    st.divider()

    # ── ACTIONS ──
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Sauvegarder simulation", use_container_width=True):
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                st.session_state.recette_id,
                st.session_state.nb_personnes,
                st.session_state.employes_snap,
                r, "simulation"
            )
            st.success(f"✅ Devis #{devis_id} sauvegardé en simulation !")

    with col2:
        if st.button("🖨️ Télécharger PDF", use_container_width=True):
            params      = get_parametres()
            recette_obj = get_recette(st.session_state.recette_id)
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                st.session_state.recette_id,
                st.session_state.nb_personnes,
                st.session_state.employes_snap,
                r, "simulation"
            )
            nom_fichier = generer_pdf_devis(
                nom_client         = st.session_state.nom_client,
                date_mariage       = st.session_state.date_mariage,
                recette_nom        = recette_obj['nom'],
                nb_personnes       = st.session_state.nb_personnes,
                detail_ingredients = r['detail_ingredients'],
                detail_employes    = r['detail_employes'],
                resultat           = r,
                params             = dict(params),
                devis_id           = devis_id
            )
            with open(nom_fichier, "rb") as f:
                st.download_button(
                    label     = "📥 Cliquez ici pour télécharger",
                    data      = f,
                    file_name = os.path.basename(nom_fichier),
                    mime      = "application/pdf"
                )
            st.success("✅ PDF généré avec succès !")

    with col3:
        if st.button("✅ VALIDER LE MARIAGE", type="primary", use_container_width=True):
        
            # --- 1. SUPPRIMER L'ANCIENNE SIMULATION ---
            conn = get_connection()
            cursor = conn.cursor()
            
            # Supprimer les employés liés à la simulation
            cursor.execute("""
                DELETE FROM employes_devis 
                WHERE devis_id IN (
                    SELECT id FROM devis 
                    WHERE nom_client = ? AND date_mariage = ? AND statut = 'simulation'
                )
            """, (st.session_state.nom_client, str(st.session_state.date_mariage)))
            
            # Supprimer le devis de la simulation
            cursor.execute("""
                DELETE FROM devis 
                WHERE nom_client = ? AND date_mariage = ? AND statut = 'simulation'
            """, (st.session_state.nom_client, str(st.session_state.date_mariage)))
            
            conn.commit()
            conn.close()
            # ------------------------------------------

            # --- 2. SAUVEGARDER LE NOUVEAU (Validé) ---
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                st.session_state.recette_id,
                st.session_state.nb_personnes,
                st.session_state.employes_snap,
                r, "validé"
            )
            valider_mariage(
                devis_id,
                st.session_state.recette_id,
                st.session_state.nb_personnes
            )
            st.success(f"✅ Mariage validé ! Devis #{devis_id} enregistré.")
            st.balloons()

            alertes = get_alertes_apres_validation()
            if alertes:
                st.error("⚠️ PRODUITS À RÉAPPROVISIONNER APRÈS CE MARIAGE :")
                for a in alertes:
                    st.warning(
                        f"🔴 **{a['nom']}** — "
                        f"Stock restant : {a['quantite_stock']:.2f} {a['unite']} "
                        f"(seuil : {a['seuil_alerte']} {a['unite']})"
                    )
            st.session_state.devis_calcule = False
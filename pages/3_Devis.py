import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from database import get_client, créer_tables
from datetime import date
from modules.pdf_generator import generer_pdf_devis

créer_tables()

st.set_page_config(page_title="Générateur de Devis", page_icon="🧮")

# Vérification sécurité
if not st.session_state.get("authentifie", False):
    st.switch_page("app.py")

st.title("🧮 Générateur de Devis")

supabase = get_client()

# ─────────────────────────────────────────────
# FONCTIONS
# ─────────────────────────────────────────────
def get_toutes_recettes():
    res = supabase.table("recettes").select("*").order("nom").execute()
    return res.data

def get_ingredients_recette(recette_id):
    res = supabase.table("recette_ingredients")\
        .select("*, produits(nom, unite, prix_achat, id)")\
        .eq("recette_id", recette_id).execute()
    return res.data

def get_parametres():
    res = supabase.table("parametres").select("*").eq("id", 1).execute()
    return res.data[0]

def get_recette(recette_id):
    res = supabase.table("recettes").select("*").eq("id", recette_id).execute()
    return res.data[0]

def calculer_devis(recettes_selectionnees, employes, frais_fixes_supplementaires):
    params = get_parametres()

    # Coût ingrédients et frais fixes cumulés sur toutes les recettes choisies
    detail_ingredients  = []
    cout_ingredients    = 0
    frais_fixes_recette = 0

    for item in recettes_selectionnees:
        recette_id   = item['id']
        nb_personnes = item['nb_personnes']
        recette      = get_recette(recette_id)
        ingredients  = get_ingredients_recette(recette_id)

        frais_fixes_recette += recette['frais_fixes']

        for ing in ingredients:
            produit    = ing['produits']
            qte_totale = ing['quantite_par_personne'] * nb_personnes
            cout       = qte_totale * produit['prix_achat']
            cout_ingredients += cout
            detail_ingredients.append({
                "Ingrédient"     : f"{produit['nom']} ({recette['nom']} - {nb_personnes}p)",
                "Qté / personne" : f"{ing['quantite_par_personne']} {produit['unite']}",
                "Qté totale"     : f"{qte_totale:.2f} {produit['unite']}",
                "Prix achat"     : f"{produit['prix_achat']} €",
                "Coût total"     : f"{cout:.2f} €"
            })

    # Coût employés
    detail_employes = []
    cout_employes   = 0
    taux_horaire    = params['taux_horaire']
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

    frais_fixes_total = frais_fixes_recette + frais_fixes_supplementaires
    cout_total        = cout_ingredients + cout_employes + frais_fixes_total
    prix_final        = cout_total / params['taux_charges']
    benefice          = prix_final * params['taux_benefice']

    return {
        "cout_ingredients"           : cout_ingredients,
        "cout_employes"              : cout_employes,
        "frais_fixes_recette"        : frais_fixes_recette,
        "frais_fixes_supplementaires": frais_fixes_supplementaires,
        "frais_fixes_total"          : frais_fixes_total,
        "cout_total"                 : cout_total,
        "prix_final"                 : prix_final,
        "benefice"                   : benefice,
        "detail_ingredients"         : detail_ingredients,
        "detail_employes"            : detail_employes,
        "taux_horaire"               : taux_horaire
    }

def sauvegarder_devis(nom_client, date_mariage, recettes_selectionnees,
                      employes, resultat, statut):

    premiere_recette_id = recettes_selectionnees[0]['id']
    total_personnes     = sum(r['nb_personnes'] for r in recettes_selectionnees)

    # Si on valide → on supprime l'ancienne simulation du même client
    if statut == "validé":
        anciennes_simus = supabase.table("devis")\
            .select("id")\
            .eq("nom_client", nom_client)\
            .eq("statut", "simulation")\
            .execute()

        for sim in anciennes_simus.data:
            supabase.table("devis_recettes").delete().eq("devis_id", sim['id']).execute()
            supabase.table("employes_devis").delete().eq("devis_id", sim['id']).execute()
            supabase.table("devis").delete().eq("id", sim['id']).execute()

    res = supabase.table("devis").insert({
        "nom_client"      : nom_client,
        "date_mariage"    : str(date_mariage),
        "recette_id"      : premiere_recette_id,
        "nb_personnes"    : total_personnes,
        "cout_ingredients": resultat['cout_ingredients'],
        "cout_employes"   : resultat['cout_employes'],
        "frais_fixes"     : resultat['frais_fixes_total'],
        "cout_total"      : resultat['cout_total'],
        "prix_final"      : resultat['prix_final'],
        "benefice"        : resultat['benefice'],
        "statut"          : statut
    }).execute()

    devis_id = res.data[0]['id']
    params   = get_parametres()

    # Enregistrer chaque recette choisie et son nombre de personnes
    for r_sel in recettes_selectionnees:
        supabase.table("devis_recettes").insert({
            "devis_id"    : devis_id,
            "recette_id"  : r_sel['id'],
            "nb_personnes": r_sel['nb_personnes']
        }).execute()

    # Enregistrer les employés
    for emp in employes:
        cout = emp['nombre'] * emp['heures'] * params['taux_horaire']
        supabase.table("employes_devis").insert({
            "devis_id"    : devis_id,
            "type_employe": emp['type'],
            "nombre"      : emp['nombre'],
            "heures"      : emp['heures'],
            "cout_total"  : cout
        }).execute()

    return devis_id

def valider_mariage(devis_id, recettes_selectionnees):
    supabase.table("devis").update({"statut": "validé"}).eq("id", devis_id).execute()

    for r_sel in recettes_selectionnees:
        ingredients = get_ingredients_recette(r_sel['id'])
        for ing in ingredients:
            produit = supabase.table("produits").select("quantite_stock")\
                .eq("id", ing['produits']['id']).execute().data[0]
            qte_utilisee = ing['quantite_par_personne'] * r_sel['nb_personnes']
            nouvelle_qte = produit['quantite_stock'] - qte_utilisee
            supabase.table("produits").update({
                "quantite_stock": nouvelle_qte
            }).eq("id", ing['produits']['id']).execute()

def get_alertes():
    produits = supabase.table("produits").select("*").execute()
    return [p for p in produits.data if p['quantite_stock'] <= p['seuil_alerte']]


# ─────────────────────────────────────────────
# FORMULAIRE DEVIS
# ─────────────────────────────────────────────

recettes = get_toutes_recettes()

if not recettes:
    st.warning("⚠️ Aucune recette disponible. Créez d'abord des recettes !")
    st.stop()

options_recettes = {r['nom']: r for r in recettes}
noms_recettes    = list(options_recettes.keys())

# ── ÉTAPE 1 ──
st.subheader("1️⃣ Informations de base & Recettes")

col1, col2 = st.columns(2)
with col1:
    nom_client = st.text_input("Nom du client", placeholder="ex: M. Ahmed")
with col2:
    date_mariage = st.date_input("Date du mariage", value=date.today())

st.markdown("**📋 Choix des recettes et du nombre de personnes :**")

if 'lignes_recettes' not in st.session_state:
    st.session_state.lignes_recettes = [
        {"nom": noms_recettes[0], "nb_personnes": 100}
    ]

recettes_valides = []
frais_fixes_cumules = 0

for i, ligne in enumerate(st.session_state.lignes_recettes):
    col_r, col_p = st.columns([3, 2])
    with col_r:
        index_defaut = noms_recettes.index(ligne['nom']) if ligne['nom'] in noms_recettes else 0
        recette_nom_choisie = st.selectbox(
            f"Recette numéro {i+1:02d}",
            noms_recettes,
            index=index_defaut,
            key=f"rec_{i}"
        )
    with col_p:
        nb_pers = st.number_input(
            f"Nombre de personnes (Recette numéro {i+1:02d})",
            min_value=1,
            step=1,
            value=int(ligne['nb_personnes']),
            key=f"pers_{i}"
        )

    rec_obj = options_recettes[recette_nom_choisie]
    frais_fixes_cumules += rec_obj['frais_fixes']
    recettes_valides.append({
        "id"          : rec_obj['id'],
        "nom"         : rec_obj['nom'],
        "nb_personnes": nb_pers,
        "frais_fixes" : rec_obj['frais_fixes']
    })

col_add_r, col_reset_r = st.columns(2)
with col_add_r:
    if st.button("➕ Ajouter une autre recette"):
        st.session_state.lignes_recettes.append({"nom": noms_recettes[0], "nb_personnes": 100})
        st.rerun()
with col_reset_r:
    if len(st.session_state.lignes_recettes) > 1:
        if st.button("🗑️ Garder une seule recette"):
            st.session_state.lignes_recettes = [{"nom": noms_recettes[0], "nb_personnes": 100}]
            st.rerun()

st.divider()

# ── ÉTAPE 2 ──
st.subheader("2️⃣ Employés")

if 'employes' not in st.session_state:
    st.session_state.employes = [
        {"type": "Serveurs",   "nombre": 1, "heures": 8},
        {"type": "Cuisiniers", "nombre": 1, "heures": 8}
    ]

params = get_parametres()

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
            key=f"type_{i}", label_visibility="collapsed"
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
            key=f"h_{i}", label_visibility="collapsed"
        )
    with col4:
        cout_ligne = nb_emp * nb_h * params['taux_horaire']
        st.markdown(f"**{cout_ligne:.0f} €**")

    employes_valides.append({
        "type"  : type_emp,
        "nombre": nb_emp,
        "heures": nb_h
    })

col_add, col_reset = st.columns(2)
with col_add:
    if st.button("➕ Ajouter une ligne employé"):
        st.session_state.employes.append({"type": "Autre", "nombre": 1, "heures": 8})
        st.rerun()
with col_reset:
    if st.button("🗑️ Réinitialiser employés"):
        st.session_state.employes = [
            {"type": "Serveurs",   "nombre": 1, "heures": 8},
            {"type": "Cuisiniers", "nombre": 1, "heures": 8}
        ]
        st.rerun()

st.divider()

# ── ÉTAPE 3 ──
st.subheader("3️⃣ Frais supplémentaires")

col1, col2 = st.columns(2)
with col1:
    st.info(f"Frais fixes des recettes sélectionnées : **{frais_fixes_cumules} €**")
with col2:
    frais_supp = st.number_input(
        "Frais supplémentaires (€)",
        min_value=0.0, step=50.0
    )

st.divider()

# ─────────────────────────────────────────────
# CALCUL
# ─────────────────────────────────────────────

if st.button("🧮 CALCULER LE DEVIS", type="primary", use_container_width=True):
    if not nom_client:
        st.error("❌ Le nom du client est obligatoire !")
    else:
        resultat = calculer_devis(
            recettes_valides,
            employes_valides,
            frais_supp
        )
        st.session_state.resultat              = resultat
        st.session_state.devis_calcule         = True
        st.session_state.nom_client            = nom_client
        st.session_state.date_mariage          = date_mariage
        st.session_state.recettes_selectionnees = recettes_valides
        st.session_state.employes_snap         = employes_valides

# ─────────────────────────────────────────────
# RÉSULTAT
# ─────────────────────────────────────────────

if st.session_state.get('devis_calcule'):
    r      = st.session_state.resultat
    r_list = st.session_state.recettes_selectionnees
    resume_recettes = " + ".join([f"{x['nom']} ({x['nb_personnes']} pers.)" for x in r_list])
    total_pers      = sum(x['nb_personnes'] for x in r_list)

    st.success("✅ Devis calculé avec succès !")
    st.subheader(f"📄 Devis — {st.session_state.nom_client} — {resume_recettes}")

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

    with st.expander("🔍 Voir le détail des ingrédients"):
        st.dataframe(pd.DataFrame(r['detail_ingredients']),
                     use_container_width=True, hide_index=True)

    with st.expander("🔍 Voir le détail des employés"):
        st.dataframe(pd.DataFrame(r['detail_employes']),
                     use_container_width=True, hide_index=True)

    st.divider()

    # ── ACTIONS ──
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Sauvegarder simulation", use_container_width=True):
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                r_list,
                st.session_state.employes_snap,
                r, "simulation"
            )
            st.success(f"✅ Devis #{devis_id} sauvegardé !")

    with col2:
        if st.button("🖨️ Télécharger PDF", use_container_width=True):
            params   = get_parametres()
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                r_list,
                st.session_state.employes_snap,
                r, "simulation"
            )
            nom_fichier = generer_pdf_devis(
                nom_client         = st.session_state.nom_client,
                date_mariage       = st.session_state.date_mariage,
                recette_nom        = resume_recettes,
                nb_personnes       = total_pers,
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
            devis_id = sauvegarder_devis(
                st.session_state.nom_client,
                st.session_state.date_mariage,
                r_list,
                st.session_state.employes_snap,
                r, "validé"
            )
            valider_mariage(devis_id, r_list)
            st.success(f"✅ Mariage validé ! Devis #{devis_id} enregistré.")
            st.balloons()

            alertes = get_alertes()
            if alertes:
                st.error("⚠️ PRODUITS À RÉAPPROVISIONNER :")
                for a in alertes:
                    st.warning(
                        f"🔴 **{a['nom']}** — "
                        f"Stock : {a['quantite_stock']:.2f} {a['unite']} "
                        f"(seuil : {a['seuil_alerte']} {a['unite']})"
                    )
            st.session_state.devis_calcule = False
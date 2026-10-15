from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
import os
from datetime import datetime


def generer_pdf_devis(
    nom_client, date_mariage, recette_nom,
    nb_personnes, detail_ingredients,
    detail_employes, resultat, params,
    devis_id
):
    """Génère un PDF professionnel pour le devis avec retour à la ligne automatique"""

    # Créer le dossier exports si pas existant
    os.makedirs("exports", exist_ok=True)

    # Nom du fichier
    nom_fichier = f"exports/Devis_{devis_id}_{nom_client.replace(' ', '_')}.pdf"

    # Création du document
    doc = SimpleDocTemplate(
        nom_fichier,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Styles
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle(
        'titre',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=5
    )
    style_sous_titre = ParagraphStyle(
        'sous_titre',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=3
    )
    style_section = ParagraphStyle(
        'section',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#2C3E50'),
        spaceBefore=15,
        spaceAfter=8
    )
    style_cell_info = ParagraphStyle(
        'cell_info',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555')
    )
    style_cell_tableau = ParagraphStyle(
        'cell_tableau',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2C3E50')
    )

    # Contenu du PDF
    contenu = []

    # ── EN-TÊTE ──────────────────────────────────
    contenu.append(Paragraph(f"{params['nom_traiteur']}", style_titre))
    if params.get('adresse'):
        contenu.append(Paragraph(params['adresse'], style_sous_titre))
    if params.get('telephone'):
        contenu.append(Paragraph(f"Tél : {params['telephone']}", style_sous_titre))

    contenu.append(Spacer(1, 0.5*cm))
    contenu.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2C3E50')))
    contenu.append(Spacer(1, 0.5*cm))

    # ── INFOS DEVIS ───────────────────────────────
    contenu.append(Paragraph(f"DEVIS N° {devis_id:04d}", style_titre))
    contenu.append(Spacer(1, 0.3*cm))

    detail_recettes = resultat.get("detail_recettes", [])

    # Si toutes les recettes ont le même nombre de personnes (ex: 150 pers.), on affiche juste "150 personnes"
    if detail_recettes:
        nb_uniques = list(set(r['Nb personnes'] for r in detail_recettes))
        if len(nb_uniques) == 1:
            texte_nb_personnes = nb_uniques[0].replace("pers.", "personnes")
        else:
            texte_nb_personnes = "<br/>".join(
                [f"• {r['Nb personnes']} ({r['Recette']})" for r in detail_recettes]
            )
    else:
        texte_nb_personnes = f"{nb_personnes} personnes"

    # Retour à la ligne automatique entre chaque recette dans l'en-tête
    recettes_formatees = recette_nom.replace(" + ", "<br/>• ")
    if " + " in recette_nom:
        recettes_formatees = "• " + recettes_formatees

    infos_data = [
        ["Client",              Paragraph(str(nom_client), style_cell_info)],
        ["Date de l'événement", Paragraph(str(date_mariage), style_cell_info)],
        ["Prestation(s)",       Paragraph(recettes_formatees, style_cell_info)],
        ["Nombre de convives",  Paragraph(texte_nb_personnes, style_cell_info)],
        ["Date d'édition",      Paragraph(datetime.now().strftime("%d/%m/%Y"), style_cell_info)],
    ]

    infos_table = Table(infos_data, colWidths=[4.5*cm, 11.5*cm])
    infos_table.setStyle(TableStyle([
        ('FONTNAME',       (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE',       (0, 0), (-1, -1), 10),
        ('FONTNAME',       (0, 0), (0, -1),  'Helvetica-Bold'),
        ('TEXTCOLOR',      (0, 0), (0, -1),  colors.HexColor('#2C3E50')),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1),
         [colors.HexColor('#F8F9FA'), colors.white]),
        ('PADDING',        (0, 0), (-1, -1), 6),
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    contenu.append(infos_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── DÉTAIL DES RECETTES ───────────────────────
    contenu.append(Paragraph("Détail des Recettes", style_section))

    rec_headers = ["Recette", "Nb personnes", "Coût / pers.", "Coût total"]
    rec_data    = [rec_headers]

    if detail_recettes:
        for rec in detail_recettes:
            rec_data.append([
                Paragraph(str(rec["Recette"]), style_cell_tableau),
                str(rec["Nb personnes"]),
                rec["Coût / pers."],
                rec["Coût total"]
            ])
    else:
        cout_unit = resultat['cout_ingredients'] / nb_personnes if nb_personnes else 0
        rec_data.append([
            Paragraph(str(recette_nom), style_cell_tableau),
            f"{nb_personnes} pers.",
            f"{cout_unit:.2f} €",
            f"{resultat['cout_ingredients']:.2f} €"
        ])

    rec_data.append([
        "TOTAL RECETTES", "", "",
        f"{resultat['cout_ingredients']:.2f} €"
    ])

    rec_table = Table(rec_data, colWidths=[7.5*cm, 2.8*cm, 2.7*cm, 3*cm])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 9),
        ('ALIGN',          (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2),
         [colors.white, colors.HexColor('#F8F9FA')]),
        ('BACKGROUND',     (0, -1), (-1, -1), colors.HexColor('#27AE60')),
        ('TEXTCOLOR',      (0, -1), (-1, -1), colors.white),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',           (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',        (0, 0),  (-1, -1), 6),
    ]))
    contenu.append(rec_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── DÉTAIL EMPLOYÉS ───────────────────────────
    contenu.append(Paragraph("Détail des Employés", style_section))

    emp_headers = ["Type", "Nb employés", "Nb heures", "Taux horaire", "Coût total"]
    emp_data    = [emp_headers]

    for emp in detail_employes:
        emp_data.append([
            Paragraph(str(emp["Type"]), style_cell_tableau),
            str(emp["Nb employés"]),
            str(emp["Nb heures"]),
            emp.get("Taux horaire", f"{params.get('taux_horaire', 0)} €/h"),
            emp["Coût total"]
        ])

    emp_data.append([
        "TOTAL EMPLOYÉS", "", "", "",
        f"{resultat['cout_employes']:.2f} €"
    ])

    emp_table = Table(emp_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 9),
        ('ALIGN',          (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2),
         [colors.white, colors.HexColor('#F8F9FA')]),
        ('BACKGROUND',     (0, -1), (-1, -1), colors.HexColor('#27AE60')),
        ('TEXTCOLOR',      (0, -1), (-1, -1), colors.white),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',           (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',        (0, 0),  (-1, -1), 6),
    ]))
    contenu.append(emp_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── RÉCAPITULATIF FINANCIER (NOUVELLE LOGIQUE COMPTABLE) ──
    contenu.append(Paragraph("Récapitulatif Financier", style_section))

    marge_brute = resultat.get('marge_brute', resultat['prix_final'] - resultat['cout_ingredients'])

    recap_data = [
        ["Coût matières premières (Ingrédients)", f"{resultat['cout_ingredients']:.2f} €"],
        ["PRIX FINAL FACTURÉ AU CLIENT", f"{resultat['prix_final']:.2f} €"],
        ["MARGE BRUTE (Sur matière)", f"{marge_brute:.2f} €"],
        ["", ""],
        ["Déduction : Main d'œuvre estimée", f"- {resultat['cout_employes']:.2f} €"],
        ["Déduction : Frais logistiques et annexes", f"- {resultat['frais_fixes_total']:.2f} €"],
        ["RÉSULTAT NET (Bénéfice final)", f"{resultat['benefice']:.2f} €"],
    ]

    recap_table = Table(recap_data, colWidths=[10*cm, 6*cm])
    recap_table.setStyle(TableStyle([
        ('FONTNAME',       (0, 0),  (-1, 2),  'Helvetica'),
        ('FONTNAME',       (0, 1),  (-1, 1),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0),  (-1, -1), 11),
        ('ALIGN',          (1, 0),  (1, -1),  'RIGHT'),
        ('VALIGN',         (0, 0),  (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0),  (-1, 3),
         [colors.white, colors.white, colors.HexColor('#F8F9FA'), colors.white]),
        ('BACKGROUND',     (0, 1),  (-1, 1),  colors.HexColor('#2980B9')),
        ('TEXTCOLOR',      (0, 1),  (-1, 1),  colors.white),
        ('BACKGROUND',     (0, 2),  (-1, 2),  colors.HexColor('#27AE60')),
        ('TEXTCOLOR',      (0, 2),  (-1, 2),  colors.white),
        ('TEXTCOLOR',      (0, 4),  (-1, 5),  colors.HexColor('#E74C3C')), # Rouge pour les déductions
        ('BACKGROUND',     (0, 6),  (-1, 6),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',      (0, 6),  (-1, 6),  colors.white),
        ('FONTNAME',       (0, 6),  (-1, 6),  'Helvetica-Bold'),
        ('GRID',           (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',        (0, 0),  (-1, -1), 8),
    ]))
    contenu.append(recap_table)
    contenu.append(Spacer(1, 1*cm))

    # ── PIED DE PAGE ──────────────────────────────
    contenu.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#DDDDDD')
    ))
    contenu.append(Spacer(1, 0.3*cm))
    contenu.append(Paragraph(
        f"Devis généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"— {params['nom_traiteur']}",
        style_sous_titre
    ))

    # Génération du PDF
    doc.build(contenu)
    return nom_fichier
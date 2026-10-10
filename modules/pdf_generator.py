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
    """Génère un PDF professionnel pour le devis"""

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
    style_normal = ParagraphStyle(
        'normal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=4
    )
    style_total = ParagraphStyle(
        'total',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#27AE60'),
        spaceAfter=4
    )

    # Contenu du PDF
    contenu = []

    # ── EN-TÊTE ──────────────────────────────────
    contenu.append(Paragraph(f"🍽️ {params['nom_traiteur']}", style_titre))
    if params['adresse']:
        contenu.append(Paragraph(params['adresse'], style_sous_titre))
    if params['telephone']:
        contenu.append(Paragraph(f"Tél : {params['telephone']}", style_sous_titre))

    contenu.append(Spacer(1, 0.5*cm))
    contenu.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2C3E50')))
    contenu.append(Spacer(1, 0.5*cm))

    # ── INFOS DEVIS ───────────────────────────────
    contenu.append(Paragraph(f"DEVIS N° {devis_id:04d}", style_titre))
    contenu.append(Spacer(1, 0.3*cm))

    infos_data = [
        ["Client",          nom_client],
        ["Date du mariage", str(date_mariage)],
        ["Recette",         recette_nom],
        ["Nombre de personnes", f"{nb_personnes} personnes"],
        ["Date du devis",   datetime.now().strftime("%d/%m/%Y")],
    ]

    infos_table = Table(infos_data, colWidths=[5*cm, 11*cm])
    infos_table.setStyle(TableStyle([
        ('FONTNAME',     (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE',     (0, 0), (-1, -1), 10),
        ('FONTNAME',     (0, 0), (0, -1),  'Helvetica-Bold'),
        ('TEXTCOLOR',    (0, 0), (0, -1),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',    (1, 0), (1, -1),  colors.HexColor('#555555')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1),
         [colors.HexColor('#F8F9FA'), colors.white]),
        ('PADDING',      (0, 0), (-1, -1), 6),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    contenu.append(infos_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── DÉTAIL INGRÉDIENTS ────────────────────────
    contenu.append(Paragraph("📦 Détail des Ingrédients", style_section))

    ing_headers = ["Ingrédient", "Qté/pers.", "Qté totale", "Prix achat", "Coût total"]
    ing_data    = [ing_headers]

    for ing in detail_ingredients:
        ing_data.append([
            ing["Ingrédient"],
            ing["Qté / personne"],
            ing["Qté totale"],
            ing["Prix achat"],
            ing["Coût total"]
        ])

    ing_data.append([
        "TOTAL INGRÉDIENTS", "", "", "",
        f"{resultat['cout_ingredients']:.2f} €"
    ])

    ing_table = Table(ing_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    ing_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 9),
        ('ALIGN',        (1, 0), (-1, -1), 'CENTER'),
        # Lignes alternées
        ('ROWBACKGROUNDS', (0, 1), (-1, -2),
         [colors.white, colors.HexColor('#F8F9FA')]),
        # Total
        ('BACKGROUND',   (0, -1), (-1, -1), colors.HexColor('#27AE60')),
        ('TEXTCOLOR',    (0, -1), (-1, -1), colors.white),
        ('FONTNAME',     (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',         (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',      (0, 0),  (-1, -1), 6),
    ]))
    contenu.append(ing_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── DÉTAIL EMPLOYÉS ───────────────────────────
    contenu.append(Paragraph("👨‍🍳 Détail des Employés", style_section))

    emp_headers = ["Type", "Nb employés", "Nb heures", "Taux horaire", "Coût total"]
    emp_data    = [emp_headers]

    for emp in detail_employes:
        emp_data.append([
            emp["Type"],
            str(emp["Nb employés"]),
            str(emp["Nb heures"]),
            emp["Taux horaire"],
            emp["Coût total"]
        ])

    emp_data.append([
        "TOTAL EMPLOYÉS", "", "", "",
        f"{resultat['cout_employes']:.2f} €"
    ])

    emp_table = Table(emp_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 9),
        ('ALIGN',        (1, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2),
         [colors.white, colors.HexColor('#F8F9FA')]),
        ('BACKGROUND',   (0, -1), (-1, -1), colors.HexColor('#27AE60')),
        ('TEXTCOLOR',    (0, -1), (-1, -1), colors.white),
        ('FONTNAME',     (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',         (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',      (0, 0),  (-1, -1), 6),
    ]))
    contenu.append(emp_table)
    contenu.append(Spacer(1, 0.5*cm))

    # ── RÉCAPITULATIF FINANCIER ───────────────────
    contenu.append(Paragraph("💰 Récapitulatif Financier", style_section))

    recap_data = [
        ["🛒 Coût ingrédients",   f"{resultat['cout_ingredients']:.2f} €"],
        ["👨‍🍳 Coût employés",      f"{resultat['cout_employes']:.2f} €"],
        ["📌 Frais fixes",         f"{resultat['frais_fixes_total']:.2f} €"],
        ["💰 COÛT TOTAL",          f"{resultat['cout_total']:.2f} €"],
        ["💵 PRIX FINAL CLIENT",   f"{resultat['prix_final']:.2f} €"],
        ["🤑 BÉNÉFICE TRAITEUR",   f"{resultat['benefice']:.2f} €"],
    ]

    recap_table = Table(recap_data, colWidths=[10*cm, 6*cm])
    recap_table.setStyle(TableStyle([
        ('FONTNAME',   (0, 0),  (-1, 2),  'Helvetica'),
        ('FONTNAME',   (0, 3),  (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0),  (-1, -1), 11),
        ('ALIGN',      (1, 0),  (1, -1),  'RIGHT'),
        ('ROWBACKGROUNDS', (0, 0), (-1, 2),
         [colors.white, colors.HexColor('#F8F9FA'), colors.white]),
        # Coût total
        ('BACKGROUND', (0, 3),  (-1, 3),  colors.HexColor('#2C3E50')),
        ('TEXTCOLOR',  (0, 3),  (-1, 3),  colors.white),
        # Prix final
        ('BACKGROUND', (0, 4),  (-1, 4),  colors.HexColor('#2980B9')),
        ('TEXTCOLOR',  (0, 4),  (-1, 4),  colors.white),
        # Bénéfice
        ('BACKGROUND', (0, 5),  (-1, 5),  colors.HexColor('#27AE60')),
        ('TEXTCOLOR',  (0, 5),  (-1, 5),  colors.white),
        ('GRID',       (0, 0),  (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING',    (0, 0),  (-1, -1), 8),
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
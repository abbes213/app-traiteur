import sqlite3
import os

# Chemin vers la base de données
DB_PATH = "data/traiteur.db"

def get_connection():
    """Connexion à la base de données"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # pour avoir les résultats en dictionnaire
    return conn


def créer_tables():
    """Crée toutes les tables si elles n'existent pas encore"""
    conn = get_connection()
    cursor = conn.cursor()

    # ─── TABLE 1 : Produits (stock) ───────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produits (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nom             TEXT    NOT NULL,
            unite           TEXT    NOT NULL,
            prix_achat      REAL    NOT NULL,
            quantite_stock  REAL    NOT NULL DEFAULT 0,
            seuil_alerte    REAL    NOT NULL DEFAULT 0,
            date_maj        TEXT    DEFAULT (date('now'))
        )
    """)

    # ─── TABLE 2 : Recettes ───────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recettes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT    NOT NULL,
            description TEXT,
            frais_fixes REAL    NOT NULL DEFAULT 0
        )
    """)

    # ─── TABLE 3 : Ingrédients par recette ───────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recette_ingredients (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            recette_id            INTEGER NOT NULL,
            produit_id            INTEGER NOT NULL,
            quantite_par_personne REAL    NOT NULL,
            FOREIGN KEY (recette_id) REFERENCES recettes(id),
            FOREIGN KEY (produit_id) REFERENCES produits(id)
        )
    """)

    # ─── TABLE 4 : Devis ─────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devis (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_client       TEXT    NOT NULL,
            date_mariage     TEXT,
            recette_id       INTEGER NOT NULL,
            nb_personnes     INTEGER NOT NULL,
            cout_ingredients REAL    DEFAULT 0,
            cout_employes    REAL    DEFAULT 0,
            frais_fixes      REAL    DEFAULT 0,
            cout_total       REAL    DEFAULT 0,
            prix_final       REAL    DEFAULT 0,
            benefice         REAL    DEFAULT 0,
            statut           TEXT    DEFAULT 'simulation',
            date_creation    TEXT    DEFAULT (date('now')),
            FOREIGN KEY (recette_id) REFERENCES recettes(id)
        )
    """)

    # ─── TABLE 5 : Employés par devis ────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employes_devis (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id      INTEGER NOT NULL,
            type_employe  TEXT    NOT NULL,
            nombre        INTEGER NOT NULL,
            heures        REAL    NOT NULL,
            cout_total    REAL    NOT NULL,
            FOREIGN KEY (devis_id) REFERENCES devis(id)
        )
    """)

    # ─── TABLE 6 : Historique des achats stock ────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achats_stock (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id        INTEGER NOT NULL,
            quantite_achetee  REAL    NOT NULL,
            prix_achat        REAL    NOT NULL,
            date_achat        TEXT    DEFAULT (date('now')),
            FOREIGN KEY (produit_id) REFERENCES produits(id)
        )
    """)

    # ─── TABLE 7 : Paramètres ────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            taux_horaire   REAL    DEFAULT 12.0,
            taux_benefice  REAL    DEFAULT 0.70,
            taux_charges   REAL    DEFAULT 0.30,
            nom_traiteur   TEXT    DEFAULT 'Mon Traiteur',
            adresse        TEXT    DEFAULT '',
            telephone      TEXT    DEFAULT ''
        )
    """)

    # ─── Insérer les paramètres par défaut ───────────────────
    cursor.execute("""
        INSERT INTO parametres (id, taux_horaire, taux_benefice, taux_charges)
        SELECT 1, 12.0, 0.70, 0.30
        WHERE NOT EXISTS (SELECT 1 FROM parametres WHERE id = 1)
    """)

    conn.commit()
    conn.close()
    print("✅ Base de données créée avec succès !")


def tester_connexion():
    """Teste que tout fonctionne"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("✅ Tables créées :")
        for table in tables:
            print(f"   → {table['name']}")
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")


# Lance la création quand on exécute ce fichier
if __name__ == "__main__":
    créer_tables()
    tester_connexion()
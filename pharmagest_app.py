import sqlite3
from datetime import datetime, timedelta
import os
import re
import csv
from typing import List, Dict, Any, Tuple
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

# =================================================================
# PARTIE 1 : LOGIQUE MÉTIER (CLASSE PharmacieLogic)
# =================================================================

DB_NAME = 'pharmagest_database.db'

class PharmacieLogic:
    """
    Encapsule toute la logique métier et les interactions avec la base de données SQLite.
    """

    def __init__(self):
        """Initialise la base de données et les données de démonstration au démarrage."""
        self._creer_base_de_donnees()
        self._initialiser_stock_demarrage()

    # --- 1.1 INITIALISATION ET MIGRATION ---

    def _migrer_tables(self, cursor: sqlite3.Cursor):
        """Exécute les migrations nécessaires pour mettre à jour la structure de la base de données."""
        try:
            cursor.execute("ALTER TABLE utilisateurs ADD COLUMN mot_de_passe TEXT NOT NULL DEFAULT 'defaut'")
            cursor.execute("UPDATE utilisateurs SET mot_de_passe = '123456' WHERE mot_de_passe = 'defaut'")
        except sqlite3.OperationalError:
            pass 
        try:
            cursor.execute("ALTER TABLE medicaments ADD COLUMN code_numerique TEXT UNIQUE")
            cursor.execute("ALTER TABLE medicaments ADD COLUMN rayon TEXT")
            cursor.execute("ALTER TABLE medicaments ADD COLUMN dci TEXT")
            cursor.execute("ALTER TABLE medicaments ADD COLUMN classe_pharmaco TEXT")
        except sqlite3.OperationalError:
            pass 
        try:
            # Ajout de tables pour la nouvelle gestion des assurances
            cursor.execute("CREATE TABLE IF NOT EXISTS societes_assurance (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL UNIQUE, contact TEXT, taux_base REAL NOT NULL DEFAULT 0.8)")
            cursor.execute("CREATE TABLE IF NOT EXISTS contrats_assurance (id INTEGER PRIMARY KEY AUTOINCREMENT, societe_id INTEGER, nom_contrat TEXT NOT NULL, taux_couverture REAL NOT NULL, FOREIGN KEY (societe_id) REFERENCES societes_assurance(id))")
        except sqlite3.OperationalError:
            pass

    def _creer_base_de_donnees(self):
        """Crée toutes les tables si elles n'existent pas."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Table Medicaments (Références)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medicaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, code_numerique TEXT UNIQUE, rayon TEXT, dci TEXT, classe_pharmaco TEXT, 
                prix_unitaire REAL NOT NULL, prix_achat REAL NOT NULL DEFAULT 0.00, fournisseur TEXT, seuil_alerte INTEGER DEFAULT 5,
                qte_min_commande INTEGER DEFAULT 10, qte_max_commande INTEGER DEFAULT 100
            )
        """)
        
        # Autres tables...
        cursor.execute("CREATE TABLE IF NOT EXISTS fournisseurs (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL UNIQUE, contact TEXT, ville TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS lots (id INTEGER PRIMARY KEY AUTOINCREMENT, medicament_id INTEGER, numero_lot TEXT NOT NULL, quantite INTEGER NOT NULL, date_expiration TEXT, emplacement TEXT, date_livraison TEXT, FOREIGN KEY (medicament_id) REFERENCES medicaments(id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS utilisateurs (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL UNIQUE, mot_de_passe TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Vendeur')")
        cursor.execute("CREATE TABLE IF NOT EXISTS permissions_utilisateur (id INTEGER PRIMARY KEY AUTOINCREMENT, utilisateur_id INTEGER NOT NULL, operation_code TEXT NOT NULL, autorise INTEGER NOT NULL DEFAULT 0, UNIQUE (utilisateur_id, operation_code), FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id))")

        # Tables Ventes
        cursor.execute("CREATE TABLE IF NOT EXISTS ventes (id INTEGER PRIMARY KEY AUTOINCREMENT, date_vente TEXT, utilisateur_id INTEGER, total_montant REAL NOT NULL, assure_id INTEGER, FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id))")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS details_vente (
                id INTEGER PRIMARY KEY AUTOINCREMENT, vente_id INTEGER, medicament_id INTEGER, lot_id INTEGER, quantite_vendue INTEGER NOT NULL, 
                prix_unitaire_vendu REAL NOT NULL, montant_assurance REAL DEFAULT 0.0, 
                FOREIGN KEY (vente_id) REFERENCES ventes(id), FOREIGN KEY (medicament_id) REFERENCES medicaments(id), FOREIGN KEY (lot_id) REFERENCES lots(id)
            )
        """)
        
        conn.commit()
        self._migrer_tables(cursor)
        conn.close()

    def _ajouter_utilisateur(self, nom: str, mot_de_passe: str, role: str = 'Vendeur'):
        """Ajoute un utilisateur de démo."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO utilisateurs (nom, mot_de_passe, role) VALUES (?, ?, ?)", (nom, mot_de_passe, role))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    def _initialiser_stock_demarrage(self):
        """Initialise les données de démonstration si les tables sont vides."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM medicaments")
        if cursor.fetchone()[0] == 0:
            # Utilisateurs
            self._ajouter_utilisateur("admin", "12345", "Admin") 
            self._ajouter_utilisateur("Bob", "vendeur789", "Vendeur") 
            cursor.execute("INSERT OR IGNORE INTO permissions_utilisateur (utilisateur_id, operation_code, autorise) VALUES (1, 'REDUCTION', 1)")
            
            # Autres données de DÉMO
            cursor.execute("INSERT OR IGNORE INTO fournisseurs (nom) VALUES ('PharmaCentral'), ('DistriMed')")
            cursor.execute("INSERT OR IGNORE INTO societes_assurance (nom, contact) VALUES ('NSIA', 'contact@nsia.ci'), ('Allianz', 'info@allianz.ci')")
            cursor.execute("INSERT OR IGNORE INTO contrats_assurance (societe_id, nom_contrat, taux_couverture) VALUES (1, 'Contrat Gold', 0.85), (2, 'Contrat Silver', 0.70)")
            
            # Médicaments 
            cursor.execute("""
                INSERT INTO medicaments (nom, code_numerique, prix_unitaire, prix_achat, fournisseur, seuil_alerte) 
                VALUES 
                ('Paracétamol 500mg', '2201', 500.0, 350.0, 'PharmaCentral', 10),
                ('Amoxicilline 1g', '2202', 1500.0, 1000.0, 'DistriMed', 5),
                ('Vitamine C 1000mg', '3305', 2500.0, 1800.0, 'PharmaCentral', 20)
            """)
            
            # Lots initiaux
            cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison) VALUES (1, 'PARA2025A', 100, '2025-12-31', '2024-05-10')")
            cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison) VALUES (1, 'PARA2026B', 50, '2026-06-30', '2025-01-20')")
            cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison) VALUES (2, 'AMO2024B', 50, '2024-10-01', '2024-03-20')")
            cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison) VALUES (3, 'VITC2026X', 3, '2026-06-01', '2024-08-15')") 
            
            conn.commit()
        conn.close()
    
    # --- 1.2 GESTION DES UTILISATEURS ---
    
    def verifier_connexion(self, nom_utilisateur: str, mot_de_passe: str) -> Tuple[int, str, str] | None:
        """Vérifie les identifiants et retourne (user_id, nom, role)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, role FROM utilisateurs WHERE nom = ? AND mot_de_passe = ?", 
                       (nom_utilisateur, mot_de_passe))
        user_info = cursor.fetchone()
        conn.close()
        return user_info

    def get_all_users(self) -> List[Tuple]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, role FROM utilisateurs")
        users = cursor.fetchall()
        conn.close()
        return users

    def add_or_update_user(self, user_id: int, nom: str, role: str, mot_de_passe: str = None) -> bool:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            if user_id is None: # Ajouter
                if mot_de_passe:
                    cursor.execute("INSERT INTO utilisateurs (nom, mot_de_passe, role) VALUES (?, ?, ?)", (nom, mot_de_passe, role))
                else:
                    return False
            else: # Modifier
                if mot_de_passe:
                    cursor.execute("UPDATE utilisateurs SET nom = ?, role = ?, mot_de_passe = ? WHERE id = ?", (nom, role, mot_de_passe, user_id))
                else:
                    cursor.execute("UPDATE utilisateurs SET nom = ?, role = ? WHERE id = ?", (nom, role, user_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    # --- 1.3 GESTION DES FOURNISSEURS ---
    
    def get_all_fournisseurs(self) -> List[Tuple]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, contact, ville FROM fournisseurs")
        fournisseurs = cursor.fetchall()
        conn.close()
        return fournisseurs

    def add_or_update_fournisseur(self, fourn_id: int, nom: str, contact: str, ville: str) -> bool:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            if fourn_id is None:
                cursor.execute("INSERT INTO fournisseurs (nom, contact, ville) VALUES (?, ?, ?)", (nom, contact, ville))
            else:
                cursor.execute("UPDATE fournisseurs SET nom = ?, contact = ?, ville = ? WHERE id = ?", (nom, contact, ville, fourn_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    # --- 1.4 GESTION ASSURANCES ---
    
    def get_all_societes(self) -> List[Tuple]:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, contact, taux_base FROM societes_assurance")
        societes = cursor.fetchall()
        conn.close()
        return societes

    def add_or_update_societe(self, societe_id: int, nom: str, contact: str, taux_base: float) -> bool:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            if societe_id is None:
                cursor.execute("INSERT INTO societes_assurance (nom, contact, taux_base) VALUES (?, ?, ?)", (nom, contact, taux_base))
            else:
                cursor.execute("UPDATE societes_assurance SET nom = ?, contact = ?, taux_base = ? WHERE id = ?", (nom, contact, taux_base, societe_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
            
    # --- 2. GESTION DES MÉDICAMENTS (RÉFÉRENCES) ---

    def ajouter_nouveau_medicament(self, nom: str, code: str, prix_vente: float, prix_achat: float, seuil: int, rayon: str = None, dci: str = None) -> bool:
        """Ajoute une nouvelle référence de médicament."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO medicaments (nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, rayon, dci) VALUES (?, ?, ?, ?, ?, ?, ?)", (nom, code, prix_vente, prix_achat, seuil, rayon, dci))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
            
    def modifier_details_medicament(self, med_id: int, nom: str, code: str, prix_vente: float, prix_achat: float, seuil: int, rayon: str, dci: str) -> bool:
        """Modifie les détails d'une référence."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE medicaments SET nom=?, code_numerique=?, prix_unitaire=?, prix_achat=?, seuil_alerte=?, rayon=?, dci=? WHERE id=?",
                           (nom, code, prix_vente, prix_achat, seuil, rayon, dci, med_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def modifier_seuils_medicament(self, med_id: int, seuil_alerte: int, qte_min_commande: int) -> bool:
        """Modifie les seuils d'alerte et de commande."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE medicaments SET seuil_alerte = ?, qte_min_commande = ? WHERE id = ?", 
                           (seuil_alerte, qte_min_commande, med_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()


    def importer_base_csv(self, file_path: str) -> Tuple[int, int]:
        """Importe des références depuis un fichier CSV."""
        if not os.path.exists(file_path):
            raise FileNotFoundError("Fichier non trouvé.")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        compteur_ajoutes = 0
        compteur_erreurs = 0
        
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            delimiter = ';' 
            reader = csv.reader(f, delimiter=delimiter)
            
            try:
                headers = [h.strip().lower() for h in next(reader)] 
                header_map = {
                    'nom': headers.index('nom'), 'code': headers.index('code_numerique'), 'prix_vente': headers.index('prix_unitaire'),
                    'prix_achat': headers.index('prix_achat'), 'seuil': headers.index('seuil_alerte'),
                    'rayon': headers.index('rayon'), 'dci': headers.index('dci')
                }
            except (ValueError, StopIteration):
                raise ValueError("En-têtes CSV manquants ou invalides.")
            
            for row in reader:
                if not row or not row[0].strip(): continue

                try:
                    nom = row[header_map['nom']].strip()
                    code = row[header_map['code']].strip()
                    prix_vente = float(row[header_map['prix_vente']].strip().replace(',', '.'))
                    
                    prix_achat = float(row[header_map.get('prix_achat', -1)].strip().replace(',', '.')) if header_map.get('prix_achat', -1) != -1 and row[header_map.get('prix_achat', -1)].strip() else 0.0
                    seuil = int(row[header_map.get('seuil', -1)].strip()) if header_map.get('seuil', -1) != -1 and row[header_map.get('seuil', -1)].strip().isdigit() else 5
                    rayon = row[header_map.get('rayon', -1)].strip() if header_map.get('rayon', -1) != -1 else None
                    dci = row[header_map.get('dci', -1)].strip() if header_map.get('dci', -1) != -1 else None
                    
                    cursor.execute("INSERT OR IGNORE INTO medicaments (nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, rayon, dci) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (nom, code, prix_vente, prix_achat, seuil, rayon, dci))
                    
                    if cursor.rowcount > 0:
                        compteur_ajoutes += 1
                    else:
                        compteur_erreurs += 1

                except (ValueError, IndexError):
                    compteur_erreurs += 1
                    continue
                        
        conn.commit()
        conn.close()
        return compteur_ajoutes, compteur_erreurs

    # --- 3. GESTION DU STOCK (Lots, Inventaire, Ajustements) ---

    def get_stock_actuel(self) -> List[Tuple]:
        """Récupère l'état complet du stock (quantité par référence)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                m.id, m.code_numerique, m.nom, m.rayon, 
                IFNULL(SUM(l.quantite), 0) AS quantite_totale,
                m.prix_unitaire, m.prix_achat, m.fournisseur, m.seuil_alerte, m.qte_min_commande
            FROM medicaments m
            LEFT JOIN lots l ON m.id = l.medicament_id AND l.quantite > 0 AND l.date_expiration > date('now')
            GROUP BY m.id
            ORDER BY m.nom
        """)
        stock = cursor.fetchall()
        conn.close()
        return stock

    def get_medicaments_par_recherche(self, terme: str, limite: int = 10) -> List[Tuple]:
        """Recherche de médicaments pour les suggestions."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        terme_like = f"%{terme}%"
        
        try: terme_int = int(terme)
        except ValueError: terme_int = -1
        
        cursor.execute("""
            SELECT 
                m.id, m.code_numerique, m.nom, m.prix_unitaire,
                IFNULL(SUM(l.quantite), 0) as stock_dispo
            FROM medicaments m
            LEFT JOIN lots l ON m.id = l.medicament_id AND l.quantite > 0
            WHERE m.nom LIKE ? OR m.code_numerique LIKE ? OR m.id = ?
            GROUP BY m.id
            ORDER BY m.nom ASC
            LIMIT ?
        """, (terme_like, terme_like, terme_int, limite))
        
        resultats = cursor.fetchall()
        conn.close()
        return resultats
    
    def get_medicament_by_id(self, med_id: int) -> Tuple | None:
        """Récupère les détails d'une référence."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, qte_min_commande, qte_max_commande, rayon, dci FROM medicaments WHERE id = ?", (med_id,))
        med = cursor.fetchone()
        conn.close()
        return med

    def get_lots_by_med_id(self, med_id: int) -> List[Tuple]:
        """Récupère les lots d'un médicament (FIFO)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, numero_lot, quantite, date_expiration, date_livraison, emplacement FROM lots WHERE medicament_id = ? AND quantite > 0 ORDER BY date_expiration ASC", (med_id,))
        lots = cursor.fetchall()
        conn.close()
        return lots
    
    def ajuster_stock_manuel(self, med_id: int, qte_ajustement: int, raison: str) -> bool:
        """Ajuste manuellement le stock en créant un lot d'ajustement ou en modifiant un lot existant."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        date_ajustement = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Pour simplifier, on cherche un lot "AJUSTEMENT" ou on en crée un.
            cursor.execute("SELECT id, quantite FROM lots WHERE medicament_id = ? AND numero_lot = 'AJUSTEMENT'", (med_id,))
            lot_info = cursor.fetchone()
            
            if lot_info:
                lot_id, qte_actuelle = lot_info
                # Vérifie si l'ajustement est une décrémentation et s'il reste assez de stock
                if qte_actuelle + qte_ajustement < 0:
                     # On pourrait rendre cela plus granulaire, mais pour un ajustement manuel, on limite souvent au stock actuel.
                     conn.rollback()
                     return False
                     
                cursor.execute("UPDATE lots SET quantite = quantite + ? WHERE id = ?", (qte_ajustement, lot_id))
            else:
                if qte_ajustement < 0:
                    conn.rollback() # Ne pas créer un lot d'ajustement négatif si aucun n'existe
                    return False
                    
                cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison, emplacement) VALUES (?, 'AJUSTEMENT', ?, '2099-12-31', ?, ?)",
                               (med_id, qte_ajustement, date_ajustement, f"RAISON: {raison}"))
            
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()


    def modifier_details_lot(self, lot_id: int, nouvelle_qte: int, nouvelle_date_exp: str) -> bool:
        """Modifie un lot existant."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE lots SET quantite = ?, date_expiration = ? WHERE id = ?", (nouvelle_qte, nouvelle_date_exp, lot_id))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def enregistrer_entree_lot(self, fourn_nom: str, contact: str, ville: str, bl_lots: List[Dict[str, Any]]) -> bool:
        """Enregistre un Bordereau de Livraison (plusieurs lots)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        date_livraison = datetime.now().strftime("%Y-%m-%d")
        
        try:
            cursor.execute("INSERT OR IGNORE INTO fournisseurs (nom, contact, ville) VALUES (?, ?, ?)", (fourn_nom, contact, ville))

            for lot in bl_lots:
                cursor.execute("INSERT INTO lots (medicament_id, numero_lot, quantite, date_expiration, date_livraison) VALUES (?, ?, ?, ?, ?)",
                               (lot['med_id'], lot['lot_num'], lot['qte'], lot['date_exp'], date_livraison))
                # Mise à jour du prix d'achat de référence (peut être optimisé)
                cursor.execute("UPDATE medicaments SET prix_achat = ? WHERE id = ?", (lot['prix_achat'], lot['med_id']))
                
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # --- 4. CAISSE / VENTES ---

    def enregistrer_vente(self, utilisateur_id: int, articles: List[Dict[str, Any]], total_montant: float, assure_id: int = None) -> int | None:
        """Enregistre la vente et décrémente le stock par lot (FIFO)."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        date_vente = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 1. Vérification du stock avant de commencer la transaction
            for item in articles:
                med_id = item['id']
                qte_demandee = item['qte']
                
                # Calcul du stock total disponible pour ce médicament
                cursor.execute("SELECT IFNULL(SUM(quantite), 0) FROM lots WHERE medicament_id = ? AND quantite > 0 AND date_expiration > date('now')", (med_id,))
                stock_dispo = cursor.fetchone()[0]
                
                if stock_dispo < qte_demandee:
                    messagebox.showerror("Stock Insuffisant", f"Stock insuffisant pour le médicament ID {med_id}. Disponible: {stock_dispo}, Demandé: {qte_demandee}")
                    conn.close()
                    return None
            
            # 2. Enregistrement de la vente
            cursor.execute("INSERT INTO ventes (date_vente, utilisateur_id, total_montant, assure_id) VALUES (?, ?, ?, ?)",
                           (date_vente, utilisateur_id, total_montant, assure_id))
            vente_id = cursor.lastrowid

            # 3. Traitement des articles et décrémentation du stock par lot (FIFO)
            for item in articles:
                med_id = item['id']
                qte_demandee = item['qte']
                prix_unitaire_vendu = item['prix_vente']
                
                qte_restante = qte_demandee
                
                # Récupérer les lots disponibles (FIFO: par date d'expiration ASC)
                lots_dispo = self.get_lots_by_med_id(med_id) 
                
                for lot in lots_dispo:
                    lot_id, _, lot_qte, _, _, _ = lot
                    if qte_restante == 0: break

                    qte_vendue_lot = min(qte_restante, lot_qte)
                    
                    # Décrémentation du lot
                    cursor.execute("UPDATE lots SET quantite = quantite - ? WHERE id = ?", (qte_vendue_lot, lot_id))
                    
                    # Enregistrement du détail de la vente
                    cursor.execute("INSERT INTO details_vente (vente_id, medicament_id, lot_id, quantite_vendue, prix_unitaire_vendu) VALUES (?, ?, ?, ?, ?)",
                                   (vente_id, med_id, lot_id, qte_vendue_lot, prix_unitaire_vendu))

                    qte_restante -= qte_vendue_lot

                if qte_restante > 0:
                    # Théoriquement impossible si l'étape 1 a réussi, mais rollback de sécurité
                    conn.rollback()
                    return None 
            
            conn.commit()
            return vente_id
        except Exception as e:
            messagebox.showerror("Erreur de transaction", f"Une erreur s'est produite lors de l'enregistrement: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def annuler_vente(self, vente_id: int) -> bool:
        """Annule une vente et réintègre le stock."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT medicament_id, lot_id, quantite_vendue FROM details_vente WHERE vente_id = ?", (vente_id,))
            details = cursor.fetchall()
            
            if not details: 
                messagebox.showwarning("Annulation", "Vente non trouvée ou déjà annulée.")
                return False 

            for _, lot_id, qte_vendue in details:
                cursor.execute("UPDATE lots SET quantite = quantite + ? WHERE id = ?", (qte_vendue, lot_id))
                
            cursor.execute("DELETE FROM details_vente WHERE vente_id = ?", (vente_id,))
            cursor.execute("DELETE FROM ventes WHERE id = ?", (vente_id,))
            
            conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Erreur d'annulation", f"Impossible d'annuler la vente: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_last_ventes(self, limit: int = 10) -> List[Tuple]:
        """Récupère les dernières transactions."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT v.id, v.date_vente, u.nom, v.total_montant FROM ventes v JOIN utilisateurs u ON v.utilisateur_id = u.id ORDER BY v.date_vente DESC LIMIT ?", (limit,))
        ventes = cursor.fetchall()
        conn.close()
        return ventes

    # --- 5. INVENTAIRE / EXPORTATION ---

    def get_inventaire_global(self) -> List[Tuple]:
        """Récupère l'inventaire valorisé."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                m.id, m.nom, m.code_numerique, 
                IFNULL(SUM(l.quantite), 0) AS quantite_totale,
                m.prix_achat, m.prix_unitaire
            FROM medicaments m
            LEFT JOIN lots l ON m.id = l.medicament_id AND l.quantite > 0
            GROUP BY m.id
            ORDER BY m.nom
        """)
        inventaire = cursor.fetchall()
        conn.close()
        return inventaire

    def exporter_stock_commande(self) -> str | None:
        """Crée un fichier CSV pour les commandes."""
        export_dir = 'Exports_Stock'
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        filename = os.path.join(export_dir, f"Commande_Stock_Bas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.id, m.nom, m.code_numerique, 
                IFNULL(SUM(l.quantite), 0) AS quantite_actuelle, 
                m.seuil_alerte, 
                m.qte_min_commande, 
                m.fournisseur
            FROM medicaments m
            LEFT JOIN lots l ON m.id = l.medicament_id AND l.quantite > 0
            GROUP BY m.id
            HAVING quantite_actuelle < m.seuil_alerte
            ORDER BY m.nom
        """)
        
        medicaments_a_commander = cursor.fetchall()
        conn.close()

        if not medicaments_a_commander:
            return None 

        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(['ID', 'Nom Medicament', 'Code Numerique', 'Stock Actuel', 'Seuil Alerte', 'Qte Min Commande', 'Fournisseur', 'Qte Suggeree'])
            
            for med in medicaments_a_commander:
                id_med, nom, code, qte_act, seuil, qte_min, fournisseur = med
                # Calcul de la quantité suggérée: (Seuil + Qte Min Commande) - Qte Actuelle
                qte_suggeree = max(0, seuil + qte_min - qte_act) 

                writer.writerow([id_med, nom, code, qte_act, seuil, qte_min, fournisseur, qte_suggeree])
        
        return filename

# =================================================================
# PARTIE 2 : INTERFACE GRAPHIQUE (GUI)
# =================================================================

class PharmacieApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PharmaGest - Gestion de Pharmacie")
        self.geometry("1400x800")
        
        # Logique Métier
        self.logic = PharmacieLogic()

        # Variables de session
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_role = None
        self.current_post = None 

        # Configuration du style (Design Esthétique)
        self.style = ttk.Style(self)
        self.style.theme_use('alt') 
        
        PRIMARY_COLOR = "#008080"  
        BG_COLOR = "#ECECEC"       
        
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("TLabel", background=BG_COLOR, font=('Segoe UI', 10))
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        self.style.configure("Primary.TButton", padding=8, relief="flat", background=PRIMARY_COLOR, foreground="white", font=('Segoe UI', 10, 'bold'))
        self.style.map("Primary.TButton", background=[('active', '#006666')])

        self.style.configure("Menu.TButton", padding=6, relief="flat", background="#34495e", foreground="white", font=('Segoe UI', 10))
        self.style.map("Menu.TButton", background=[('active', '#2c3e50')])

        self.title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold", slant="italic")

        # Création des cadres
        self.create_widgets()
        
        self.show_frame("connexion") # Démarrer sur l'écran de connexion

    def show_frame(self, page_name: str, data: Any = None):
        """Affiche une frame spécifique."""
        frame = self.frames.get(page_name)
        if frame:
            # Appel du callback de mise à jour si la frame en a un
            if hasattr(frame, 'on_show'):
                frame.on_show(data) 
            frame.tkraise()
        else:
            messagebox.showerror("Erreur GUI", f"La page '{page_name}' n'existe pas.")

    def create_widgets(self):
        # Cadre principal (Conteneur)
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # ----------------------------------------------------
        # Définition des Frames (Ecrans)
        # ----------------------------------------------------
        self.connexion_frame = ConnexionFrame(self.container, self)
        self.post_selection_frame = PostSelectionFrame(self.container, self) 
        self.menu_gestion_frame = MenuGestionFrame(self.container, self) 
        
        self.stock_frame = StockFrame(self.container, self)
        self.recherche_frame = RechercheFrame(self.container, self)
        self.ajout_ref_frame = AjoutRefFrame(self.container, self)
        self.import_csv_frame = ImportCSVFrame(self.container, self)
        self.bl_frame = BLFrame(self.container, self)
        self.pdv_frame = PDVFrame(self.container, self) 
        self.retour_vente_frame = RetourVenteFrame(self.container, self) 
        self.gestion_users_frame = GestionUsersFrame(self.container, self) 
        self.gestion_fourn_frame = GestionFournFrame(self.container, self) 
        self.modifier_lot_frame = ModifierLotFrame(self.container, self) 
        self.ajustement_stock_frame = AjustementStockFrame(self.container, self) 
        self.modifier_seuils_frame = ModifierSeuilsFrame(self.container, self)
        self.gestion_assurances_frame = GestionAssurancesFrame(self.container, self) 
        self.inventaire_frame = InventaireFrame(self.container, self) 
        
        # Dictionnaire de frames
        self.frames = {
            "connexion": self.connexion_frame, "post_selection": self.post_selection_frame, 
            "menu_gestion": self.menu_gestion_frame, "stock": self.stock_frame, 
            "recherche": self.recherche_frame, "ajout_ref": self.ajout_ref_frame, "import_csv": self.import_csv_frame, 
            "bl": self.bl_frame, "pdv": self.pdv_frame, "retour_vente": self.retour_vente_frame, 
            "gestion_users": self.gestion_users_frame, "gestion_fourn": self.gestion_fourn_frame,
            "modifier_lot": self.modifier_lot_frame, "ajustement_stock": self.ajustement_stock_frame,
            "modifier_seuils": self.modifier_seuils_frame, "gestion_assurances": self.gestion_assurances_frame,
            "inventaire": self.inventaire_frame
        }
        
        # Placement des frames
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def login(self, username: str, password: str):
        """Tente la connexion de l'utilisateur."""
        user_info = self.logic.verifier_connexion(username, password)
        if user_info:
            self.current_user_id, self.current_user_name, self.current_user_role = user_info
            self.show_frame("post_selection")
        else:
            messagebox.showerror("Erreur de Connexion", "Nom d'utilisateur ou mot de passe incorrect.")

    def select_post(self, post_type: str):
        """Sélectionne le poste de travail et navigue."""
        role = self.current_user_role
        self.current_post = post_type
        
        if post_type == "Gestion":
            if role == "Admin":
                self.show_frame("menu_gestion")
            else:
                messagebox.showwarning("Accès Restreint", "Seuls les administrateurs ont accès à la gestion.")
        elif post_type == "PDV":
             self.show_frame("pdv")
        else:
            messagebox.showerror("Erreur", "Poste inconnu.")

    def logout(self):
        """Déconnecte l'utilisateur et retourne à l'écran de connexion."""
        self.current_user_id = None
        self.current_user_name = None
        self.current_user_role = None
        self.current_post = None
        self.show_frame("connexion")

# ----------------------------------------------------
# DEFINITION DES CLASSES DE FRAMES (GUI)
# ----------------------------------------------------

class BaseFrame(ttk.Frame):
    """Classe de base pour toutes les Frames de l'application."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # Méthode vide à surcharger par les sous-classes
        self.on_show = lambda data=None: None

class ConnexionFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        # Structure de la frame de connexion (simple)
        main_frame = ttk.Frame(self)
        main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(main_frame, text="PHARMAGEST", font=controller.title_font).pack(pady=20)

        # Nom d'utilisateur
        ttk.Label(main_frame, text="Nom d'utilisateur:").pack(pady=5)
        self.user_entry = ttk.Entry(main_frame, width=30, font=('Segoe UI', 12))
        self.user_entry.pack(pady=5)

        # Mot de passe
        ttk.Label(main_frame, text="Mot de passe:").pack(pady=5)
        self.pass_entry = ttk.Entry(main_frame, width=30, show="*", font=('Segoe UI', 12))
        self.pass_entry.pack(pady=5)

        # Bouton
        ttk.Button(main_frame, text="Connexion", style="Primary.TButton", command=self._attempt_login).pack(pady=20)
        
    def _attempt_login(self):
        self.controller.login(self.user_entry.get(), self.pass_entry.get())

class PostSelectionFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        main_frame = ttk.Frame(self)
        main_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(main_frame, text="Sélection du Poste", font=('Segoe UI', 16, 'bold')).pack(pady=20)
        
        ttk.Button(main_frame, text="Poste de Vente (PDV)", command=lambda: controller.select_post("PDV"), width=30, style="Menu.TButton").pack(pady=10)
        ttk.Button(main_frame, text="Gestion & Stock", command=lambda: controller.select_post("Gestion"), width=30, style="Menu.TButton").pack(pady=10)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=20)
        
        ttk.Button(main_frame, text="Déconnexion", command=controller.logout, style="TButton").pack(pady=10)

class MenuGestionFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        # Structure: Menu latéral et zone de contenu
        menu_frame = ttk.Frame(self, width=200)
        menu_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        content_frame = ttk.Frame(self)
        content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(menu_frame, text="MENU GESTION", font=('Segoe UI', 12, 'bold')).pack(pady=10)
        
        # Boutons du menu
        ttk.Button(menu_frame, text="1. Stock / Inventaire", command=lambda: controller.show_frame("stock"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="2. Entrée BL / Lots", command=lambda: controller.show_frame("bl"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="3. Références Médocs", command=lambda: controller.show_frame("recherche"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="4. Import CSV", command=lambda: controller.show_frame("import_csv"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="5. Gestion Utilisateurs", command=lambda: controller.show_frame("gestion_users"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="6. Fournisseurs / Assurances", command=lambda: controller.show_frame("gestion_fourn"), style="Menu.TButton", width=25).pack(pady=5)
        ttk.Button(menu_frame, text="7. Inventaire Valorisé", command=lambda: controller.show_frame("inventaire"), style="Menu.TButton", width=25).pack(pady=5)
        
        ttk.Separator(menu_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Button(menu_frame, text="⬅️ Retour Postes", command=lambda: controller.show_frame("post_selection"), style="TButton", width=25).pack(pady=10)

class StockFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Stock Actuel et Alertes")
        
        # Zone de la liste
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id', 'code', 'nom', 'rayon', 'qte', 'prix_u', 'prix_a', 'seuil', 'qte_min_cmd', 'fourn')
        self.stock_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        
        for col in columns:
            self.stock_tree.heading(col, text=col.replace('_', ' ').capitalize())
            self.stock_tree.column(col, anchor=tk.W, width=80)
            
        self.stock_tree.column('nom', width=200)
        self.stock_tree.column('qte', width=60, anchor=tk.CENTER)
        self.stock_tree.column('seuil', width=60, anchor=tk.CENTER)
        
        self.stock_tree.tag_configure('alerte', background='#ffcccc') # Alerte rouge
        
        self.stock_tree.pack(fill='both', expand=True, side='left')
        
        # Scrollbar
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.stock_tree.yview)
        vsb.pack(side='right', fill='y')
        self.stock_tree.configure(yscrollcommand=vsb.set)
        
        # Boutons d'action
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Actualiser", command=self.on_show).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Lots et Expiration (Détails)", command=self._show_lots_details).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Ajuster Stock", command=self._show_ajustement).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Exporter Commandes (CSV)", command=self._exporter_commandes).pack(side='right', padx=5)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def on_show(self, data=None):
        """Chargement et affichage des données de stock."""
        for i in self.stock_tree.get_children():
            self.stock_tree.delete(i)
        
        stock = self.controller.logic.get_stock_actuel()
        for item in stock:
            med_id, code, nom, rayon, qte, prix_u, prix_a, seuil, qte_min_cmd, fourn = item
            tags = ()
            if qte <= seuil:
                tags = ('alerte',)
            
            self.stock_tree.insert('', 'end', values=item, tags=tags)

    def _show_lots_details(self):
        selected_item = self.stock_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un médicament.")
            return
            
        med_id = self.stock_tree.item(selected_item, 'values')[0]
        self.controller.show_frame("modifier_lot", med_id)

    def _show_ajustement(self):
        selected_item = self.stock_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un médicament pour ajustement.")
            return
            
        med_id = self.stock_tree.item(selected_item, 'values')[0]
        self.controller.show_frame("ajustement_stock", med_id)
        
    def _exporter_commandes(self):
        try:
            filename = self.controller.logic.exporter_stock_commande()
            if filename:
                messagebox.showinfo("Exportation Réussie", f"Fichier de commande créé:\n{filename}")
            else:
                messagebox.showinfo("Exportation", "Aucun médicament n'est en dessous du seuil d'alerte. Pas de fichier créé.")
        except Exception as e:
            messagebox.showerror("Erreur d'Exportation", f"Une erreur s'est produite: {e}")

class RechercheFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Recherche et Gestion des Références")

        # Zone de recherche et de liste
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(search_frame, text="Rechercher (Nom/Code/ID):").pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side='left', padx=5)
        ttk.Button(search_frame, text="Rechercher", command=self._perform_search).pack(side='left', padx=10)
        ttk.Button(search_frame, text="Ajouter Nouvelle Référence", command=lambda: controller.show_frame("ajout_ref")).pack(side='right', padx=10)

        # Liste des résultats (similaire à stock, mais avec moins de colonnes pour la recherche)
        columns = ('id', 'code', 'nom', 'prix_u', 'prix_a', 'rayon', 'dci')
        self.results_tree = ttk.Treeview(self, columns=columns, show='headings')
        
        for col in columns:
            self.results_tree.heading(col, text=col.replace('_', ' ').capitalize())
            self.results_tree.column(col, anchor=tk.W, width=100)
        self.results_tree.column('nom', width=250)
        
        self.results_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Bouton Modifier
        ttk.Button(self, text="Modifier Référence Sélectionnée", command=self._modify_selected).pack(pady=5)
        ttk.Button(self, text="Modifier Seuils", command=self._modify_seuils).pack(pady=5)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def _perform_search(self):
        terme = self.search_entry.get().strip()
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
            
        if not terme:
            return

        # Simuler une recherche plus large pour cet écran (on utilise la méthode pour PDV, mais avec une limite élevée)
        results = self.controller.logic.get_medicaments_par_recherche(terme, limite=50)
        
        for med_id, code, nom, prix_u, _ in results:
            med_details = self.controller.logic.get_medicament_by_id(med_id)
            # Tuple: id, nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, qte_min_commande, qte_max_commande, rayon, dci
            if med_details:
                # Affichage des colonnes pour cet écran: id, code, nom, prix_u, prix_a, rayon, dci
                row_data = (
                    med_details[0], med_details[2], med_details[1], med_details[3], med_details[4], med_details[8], med_details[9]
                )
                self.results_tree.insert('', 'end', values=row_data)

    def _modify_selected(self):
        selected_item = self.results_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une référence à modifier.")
            return
            
        med_id = self.results_tree.item(selected_item, 'values')[0]
        self.controller.show_frame("ajout_ref", int(med_id)) # Utiliser la même frame d'ajout pour la modification

    def _modify_seuils(self):
        selected_item = self.results_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une référence à modifier.")
            return
            
        med_id = self.results_tree.item(selected_item, 'values')[0]
        self.controller.show_frame("modifier_seuils", int(med_id))

class AjoutRefFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.med_id = None
        self._create_header("Ajouter/Modifier Référence Médicament")
        
        # Formulaire
        form_frame = ttk.Frame(self)
        form_frame.pack(padx=20, pady=20)

        fields = [
            ("Nom", "nom_entry"), ("Code Numérique", "code_entry"), 
            ("Prix Vente (XOF)", "pv_entry"), ("Prix Achat (XOF)", "pa_entry"),
            ("Seuil Alerte", "seuil_entry"), ("Rayon/Emplacement", "rayon_entry"), 
            ("DCI", "dci_entry")
        ]
        
        for i, (label_text, entry_name) in enumerate(fields):
            ttk.Label(form_frame, text=f"{label_text}:").grid(row=i, column=0, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=i, column=1, padx=5, pady=5)
            setattr(self, entry_name, entry)

        self.submit_btn = ttk.Button(form_frame, text="Ajouter", style="Primary.TButton", command=self._submit)
        self.submit_btn.grid(row=len(fields), column=0, columnspan=2, pady=20)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        self.title_label = ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold'))
        self.title_label.pack(side='left')
        ttk.Button(header_frame, text="Retour Référence", command=lambda: self.controller.show_frame("recherche")).pack(side='right')
        
    def on_show(self, med_id: int = None):
        self.med_id = med_id
        
        # Réinitialisation
        for attr in ['nom_entry', 'code_entry', 'pv_entry', 'pa_entry', 'seuil_entry', 'rayon_entry', 'dci_entry']:
            entry = getattr(self, attr)
            entry.delete(0, tk.END)
            
        if med_id:
            self.title_label.config(text="Modifier Référence Médicament")
            self.submit_btn.config(text="Modifier")
            
            med_details = self.controller.logic.get_medicament_by_id(med_id)
            if med_details:
                # Tuple: id, nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, qte_min_commande, qte_max_commande, rayon, dci
                self.nom_entry.insert(0, med_details[1])
                self.code_entry.insert(0, med_details[2])
                self.pv_entry.insert(0, med_details[3])
                self.pa_entry.insert(0, med_details[4])
                self.seuil_entry.insert(0, med_details[5])
                self.rayon_entry.insert(0, med_details[8] if med_details[8] else "")
                self.dci_entry.insert(0, med_details[9] if med_details[9] else "")
                
        else:
            self.title_label.config(text="Ajouter Nouvelle Référence Médicament")
            self.submit_btn.config(text="Ajouter")

    def _submit(self):
        try:
            nom = self.nom_entry.get()
            code = self.code_entry.get()
            prix_v = float(self.pv_entry.get())
            prix_a = float(self.pa_entry.get())
            seuil = int(self.seuil_entry.get())
            rayon = self.rayon_entry.get() if self.rayon_entry.get() else None
            dci = self.dci_entry.get() if self.dci_entry.get() else None
            
            if not nom or not code or prix_v <= 0 or prix_a < 0 or seuil < 0:
                messagebox.showerror("Erreur", "Veuillez remplir tous les champs obligatoires avec des valeurs valides.")
                return

            if self.med_id:
                success = self.controller.logic.modifier_details_medicament(self.med_id, nom, code, prix_v, prix_a, seuil, rayon, dci)
                if success:
                    messagebox.showinfo("Succès", "Référence modifiée avec succès.")
                    self.controller.show_frame("recherche")
                else:
                    messagebox.showerror("Erreur", "Échec de la modification (code numérique déjà existant?).")
            else:
                success = self.controller.logic.ajouter_nouveau_medicament(nom, code, prix_v, prix_a, seuil, rayon, dci)
                if success:
                    messagebox.showinfo("Succès", "Nouvelle référence ajoutée avec succès.")
                    self.on_show() # Réinitialise le formulaire
                else:
                    messagebox.showerror("Erreur", "Échec de l'ajout (code numérique déjà existant?).")
                    
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Veuillez entrer des nombres valides pour les prix et le seuil.")
            
class ImportCSVFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Importation de Références par CSV")

        info_label = ttk.Label(self, text="⚠️ Le fichier CSV doit contenir les en-têtes suivants (séparateur: ';'):\n'nom;code_numerique;prix_unitaire;prix_achat;seuil_alerte;rayon;dci'", justify=tk.LEFT)
        info_label.pack(padx=20, pady=20)

        file_frame = ttk.Frame(self)
        file_frame.pack(padx=20, pady=10)

        self.path_entry = ttk.Entry(file_frame, width=60)
        self.path_entry.pack(side='left', padx=5)
        ttk.Button(file_frame, text="Parcourir...", command=self._select_file).pack(side='left', padx=5)
        
        ttk.Button(self, text="Démarrer l'Importation", style="Primary.TButton", command=self._start_import).pack(pady=20)
        
    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def _select_file(self):
        file_path = filedialog.askopenfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, file_path)

    def _start_import(self):
        file_path = self.path_entry.get()
        if not file_path:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier CSV.")
            return

        try:
            ajoutes, erreurs = self.controller.logic.importer_base_csv(file_path)
            messagebox.showinfo("Importation Terminée", f"Opération réussie:\n- {ajoutes} nouvelles références ajoutées ou mises à jour.\n- {erreurs} lignes ignorées (doublons ou erreurs de format).")
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Fichier non trouvé.")
        except ValueError as e:
            messagebox.showerror("Erreur de Format", str(e))
        except Exception as e:
            messagebox.showerror("Erreur Inconnue", f"Erreur lors de l'importation: {e}")

class BLFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.bl_items: List[Dict[str, Any]] = []
        self._create_header("Enregistrement Bordereau de Livraison (BL)")
        
        # Fournisseur Info
        fourn_frame = ttk.LabelFrame(self, text="Information Fournisseur/BL")
        fourn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(fourn_frame, text="Nom Fournisseur:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.fourn_entry = ttk.Entry(fourn_frame, width=30)
        self.fourn_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(fourn_frame, text="Contact:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.contact_entry = ttk.Entry(fourn_frame, width=30)
        self.contact_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(fourn_frame, text="Ville:").grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.ville_entry = ttk.Entry(fourn_frame, width=30)
        self.ville_entry.grid(row=1, column=3, padx=5, pady=5)

        # Ajout de Lot
        add_frame = ttk.LabelFrame(self, text="Ajouter Lot")
        add_frame.pack(fill='x', padx=10, pady=5)
        
        self.med_id_entry = self._create_add_field(add_frame, "ID Médoc", 0)
        self.lot_num_entry = self._create_add_field(add_frame, "N° Lot", 1)
        self.qte_entry = self._create_add_field(add_frame, "Quantité", 2)
        self.date_exp_entry = self._create_add_field(add_frame, "Date Exp. (YYYY-MM-DD)", 3)
        self.prix_achat_entry = self._create_add_field(add_frame, "Prix Achat U.", 4)
        
        ttk.Button(add_frame, text="Ajouter à la Liste", command=self._add_lot).grid(row=0, column=5, rowspan=2, padx=10)

        # Liste des Lots
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id', 'nom', 'lot_num', 'qte', 'date_exp', 'prix_achat')
        self.bl_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        for col in columns:
            self.bl_tree.heading(col, text=col.replace('_', ' ').capitalize())
        self.bl_tree.pack(fill='both', expand=True)

        # Validation
        ttk.Button(self, text="Valider le Bordereau de Livraison (Enregistrer Stock)", style="Primary.TButton", command=self._validate_bl).pack(pady=10)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def _create_add_field(self, parent, label_text, column):
        ttk.Label(parent, text=f"{label_text}:").grid(row=0, column=column, padx=5, pady=5, sticky='w')
        entry = ttk.Entry(parent, width=15)
        entry.grid(row=1, column=column, padx=5, pady=5)
        return entry

    def _add_lot(self):
        try:
            med_id = int(self.med_id_entry.get())
            lot_num = self.lot_num_entry.get()
            qte = int(self.qte_entry.get())
            date_exp = self.date_exp_entry.get()
            prix_achat = float(self.prix_achat_entry.get())
            
            if qte <= 0 or not lot_num or not date_exp:
                raise ValueError("Champs incomplets ou invalides.")
            if not re.match(r"\d{4}-\d{2}-\d{2}", date_exp):
                 raise ValueError("Format de date invalide (YYYY-MM-DD).")

            med_info = self.controller.logic.get_medicament_by_id(med_id)
            if not med_info:
                messagebox.showerror("Erreur", f"Médicament ID {med_id} non trouvé.")
                return

            lot_data = {
                'med_id': med_id, 'lot_num': lot_num, 'qte': qte, 'date_exp': date_exp, 'prix_achat': prix_achat,
                'nom': med_info[1] # Nom pour affichage dans la Treeview
            }
            self.bl_items.append(lot_data)
            self._update_bl_tree()
            
            # Réinitialiser les champs d'ajout
            self.med_id_entry.delete(0, tk.END)
            self.lot_num_entry.delete(0, tk.END)
            self.qte_entry.delete(0, tk.END)
            self.date_exp_entry.delete(0, tk.END)
            self.prix_achat_entry.delete(0, tk.END)
            
        except ValueError as e:
            messagebox.showerror("Erreur de Saisie", f"Erreur: {e}")

    def _update_bl_tree(self):
        for i in self.bl_tree.get_children():
            self.bl_tree.delete(i)
        for item in self.bl_items:
            self.bl_tree.insert('', 'end', values=(item['med_id'], item['nom'], item['lot_num'], item['qte'], item['date_exp'], item['prix_achat']))

    def _validate_bl(self):
        fourn_nom = self.fourn_entry.get()
        contact = self.contact_entry.get()
        ville = self.ville_entry.get()
        
        if not fourn_nom or not self.bl_items:
            messagebox.showwarning("Validation", "Nom du fournisseur et au moins un lot sont requis.")
            return

        if self.controller.logic.enregistrer_entree_lot(fourn_nom, contact, ville, self.bl_items):
            messagebox.showinfo("Succès", "Bordereau de Livraison enregistré et stock mis à jour.")
            self.bl_items = []
            self._update_bl_tree()
            self.fourn_entry.delete(0, tk.END)
            self.contact_entry.delete(0, tk.END)
            self.ville_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Erreur", "Échec de l'enregistrement du Bordereau de Livraison.")

class PDVFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.panier: Dict[int, Dict[str, Any]] = {}
        self._create_header("Poste de Vente (PDV)")
        
        main_paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True, padx=10, pady=10)

        # Panneau de Gauche: Recherche et Ajout (70%)
        left_pane = ttk.Frame(main_paned)
        main_paned.add(left_pane, weight=7)
        
        # Champ de recherche
        search_frame = ttk.Frame(left_pane)
        search_frame.pack(fill='x', pady=5)
        ttk.Label(search_frame, text="Rechercher:").pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', self._autocomplete)

        # Suggestions (Treeview)
        cols = ('id', 'code', 'nom', 'prix', 'stock')
        self.suggestions_tree = ttk.Treeview(left_pane, columns=cols, show='headings', height=10)
        for col in cols:
            self.suggestions_tree.heading(col, text=col.capitalize())
            self.suggestions_tree.column(col, width=100)
        self.suggestions_tree.column('nom', width=250)
        self.suggestions_tree.pack(fill='x', padx=5, pady=5)
        
        # Ajout au panier
        add_frame = ttk.Frame(left_pane)
        add_frame.pack(fill='x', pady=5)
        self.qte_entry = ttk.Entry(add_frame, width=10)
        ttk.Label(add_frame, text="Quantité:").pack(side='left', padx=5)
        self.qte_entry.pack(side='left', padx=5)
        ttk.Button(add_frame, text="Ajouter au Panier", style="Primary.TButton", command=self._add_to_cart).pack(side='left', padx=10)

        # Panneau de Droite: Panier (30%)
        right_pane = ttk.Frame(main_paned)
        main_paned.add(right_pane, weight=3)
        
        ttk.Label(right_pane, text="PANIER", font=('Segoe UI', 12, 'bold')).pack(pady=5)
        
        cart_cols = ('nom', 'qte', 'prix_u', 'total')
        self.cart_tree = ttk.Treeview(right_pane, columns=cart_cols, show='headings', height=15)
        for col in cart_cols:
            self.cart_tree.heading(col, text=col.capitalize())
        self.cart_tree.column('nom', width=150)
        self.cart_tree.pack(fill='both', expand=True)

        # Total et Validation
        self.total_label = ttk.Label(right_pane, text="Total: 0.00 XOF", font=('Segoe UI', 14, 'bold'))
        self.total_label.pack(pady=10)
        ttk.Button(right_pane, text="Enregistrer Vente", style="Primary.TButton", command=self._validate_sale).pack(pady=10)
        ttk.Button(right_pane, text="Vider Panier", command=self._clear_cart).pack(pady=5)
        
    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Label(header_frame, text=f"Utilisateur: {self.controller.current_user_name if self.controller.current_user_name else ''}", font=('Segoe UI', 10, 'italic')).pack(side='left', padx=20)
        ttk.Button(header_frame, text="⬅️ Retour Postes", command=lambda: self.controller.show_frame("post_selection")).pack(side='right')

    def _autocomplete(self, event=None):
        terme = self.search_entry.get().strip()
        for i in self.suggestions_tree.get_children():
            self.suggestions_tree.delete(i)
            
        if not terme:
            return

        results = self.controller.logic.get_medicaments_par_recherche(terme)
        for med_id, code, nom, prix_u, stock in results:
            self.suggestions_tree.insert('', 'end', values=(med_id, code, nom, prix_u, stock))

    def _add_to_cart(self):
        selected_item = self.suggestions_tree.focus()
        if not selected_item:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un médicament dans la liste.")
            return

        try:
            med_id, _, nom, prix_u, stock = self.suggestions_tree.item(selected_item, 'values')
            med_id = int(med_id)
            prix_u = float(prix_u)
            stock = int(stock)
            
            qte_str = self.qte_entry.get()
            qte = int(qte_str) if qte_str else 1
            
            # Stock check
            current_qte_in_cart = self.panier.get(med_id, {}).get('qte', 0)
            if current_qte_in_cart + qte > stock:
                messagebox.showwarning("Stock Insuffisant", f"Quantité demandée ({current_qte_in_cart + qte}) dépasse le stock disponible ({stock}).")
                return

            if med_id in self.panier:
                self.panier[med_id]['qte'] += qte
            else:
                self.panier[med_id] = {'id': med_id, 'nom': nom, 'prix_vente': prix_u, 'qte': qte}
                
            self._update_cart_display()
            self.qte_entry.delete(0, tk.END)
            
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Quantité invalide.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout: {e}")

    def _update_cart_display(self):
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
            
        total_montant = 0.0
        for med_id, item in self.panier.items():
            subtotal = item['qte'] * item['prix_vente']
            total_montant += subtotal
            self.cart_tree.insert('', 'end', values=(item['nom'], item['qte'], f"{item['prix_vente']:.2f}", f"{subtotal:.2f}"))
            
        self.total_label.config(text=f"Total: {total_montant:.2f} XOF")

    def _clear_cart(self):
        self.panier = {}
        self._update_cart_display()

    def _validate_sale(self):
        if not self.panier:
            messagebox.showwarning("Panier Vide", "Veuillez ajouter des articles avant de valider la vente.")
            return

        total_montant = sum(item['qte'] * item['prix_vente'] for item in self.panier.values())
        
        articles_list = list(self.panier.values()) # Convertir le dict en liste d'articles
        
        vente_id = self.controller.logic.enregistrer_vente(
            utilisateur_id=self.controller.current_user_id,
            articles=articles_list,
            total_montant=total_montant
        )
        
        if vente_id:
            messagebox.showinfo("Succès", f"Vente enregistrée sous l'ID: {vente_id}\nTotal: {total_montant:.2f} XOF")
            self._clear_cart()
        else:
            # L'erreur spécifique est gérée dans la logique pour le stock insuffisant
            messagebox.showerror("Échec", "La vente n'a pas pu être enregistrée. Vérifiez le stock.")
            
class RetourVenteFrame(BaseFrame):
    # Ce frame n'était pas entièrement défini, je le laisse comme placeholder ou je le définis pour l'annulation
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Annulation de Vente / Retour")

        # Zone de recherche de vente
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(search_frame, text="ID Vente à Annuler:").pack(side='left', padx=5)
        self.vente_id_entry = ttk.Entry(search_frame, width=15)
        self.vente_id_entry.pack(side='left', padx=5)
        ttk.Button(search_frame, text="Annuler la Vente", style="Primary.TButton", command=self._annuler_vente).pack(side='left', padx=10)
        
        # Affichage des dernières ventes
        ttk.Label(self, text="Dernières Ventes", font=('Segoe UI', 12, 'bold')).pack(pady=10)
        cols = ('id', 'date', 'utilisateur', 'montant')
        self.ventes_tree = ttk.Treeview(self, columns=cols, show='headings', height=10)
        for col in cols:
            self.ventes_tree.heading(col, text=col.capitalize())
        self.ventes_tree.pack(fill='x', padx=10)
        
    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def on_show(self, data=None):
        self._load_last_ventes()

    def _load_last_ventes(self):
        for i in self.ventes_tree.get_children():
            self.ventes_tree.delete(i)
        
        ventes = self.controller.logic.get_last_ventes(limit=20)
        for vente in ventes:
            self.ventes_tree.insert('', 'end', values=vente)

    def _annuler_vente(self):
        try:
            vente_id = int(self.vente_id_entry.get())
            if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir annuler la vente ID {vente_id} ? Le stock sera réintégré."):
                if self.controller.logic.annuler_vente(vente_id):
                    messagebox.showinfo("Succès", f"Vente ID {vente_id} annulée. Stock réintégré.")
                    self._load_last_ventes()
                    self.vente_id_entry.delete(0, tk.END)
                else:
                    messagebox.showerror("Échec", "Annulation impossible (Vente introuvable ou erreur BD).")
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Veuillez entrer un ID de vente valide.")

class GestionUsersFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Gestion des Utilisateurs")

        # Formulaire
        form_frame = ttk.LabelFrame(self, text="Ajouter / Modifier Utilisateur")
        form_frame.pack(fill='x', padx=10, pady=5)
        
        self.id_user = tk.IntVar()

        ttk.Label(form_frame, text="Nom:").grid(row=0, column=0, padx=5, pady=5)
        self.nom_entry = ttk.Entry(form_frame, width=20)
        self.nom_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Rôle:").grid(row=0, column=2, padx=5, pady=5)
        self.role_var = tk.StringVar(value='Vendeur')
        self.role_combo = ttk.Combobox(form_frame, textvariable=self.role_var, values=['Admin', 'Vendeur'], width=18)
        self.role_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Mot de Passe:").grid(row=1, column=0, padx=5, pady=5)
        self.mdp_entry = ttk.Entry(form_frame, width=20, show='*')
        self.mdp_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.submit_btn = ttk.Button(form_frame, text="Ajouter", command=self._submit_user)
        self.submit_btn.grid(row=1, column=3, padx=5, pady=5)
        ttk.Button(form_frame, text="Effacer Sélection", command=self._clear_form).grid(row=1, column=4, padx=5, pady=5)
        
        # Liste
        self.user_tree = ttk.Treeview(self, columns=('id', 'nom', 'role'), show='headings', height=10)
        self.user_tree.heading('id', text='ID')
        self.user_tree.heading('nom', text='Nom')
        self.user_tree.heading('role', text='Rôle')
        self.user_tree.column('id', width=50, anchor=tk.CENTER)
        self.user_tree.pack(fill='x', padx=10, pady=10)
        self.user_tree.bind('<<TreeviewSelect>>', self._load_selected_user)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def on_show(self, data=None):
        self._load_users()
        self._clear_form()

    def _load_users(self):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        
        users = self.controller.logic.get_all_users()
        for user in users:
            self.user_tree.insert('', 'end', values=user)
            
    def _clear_form(self):
        self.id_user.set(0)
        self.nom_entry.delete(0, tk.END)
        self.mdp_entry.delete(0, tk.END)
        self.role_var.set('Vendeur')
        self.submit_btn.config(text="Ajouter")
        
    def _load_selected_user(self, event):
        selected_item = self.user_tree.focus()
        if not selected_item: return
        
        user_id, nom, role = self.user_tree.item(selected_item, 'values')
        self.id_user.set(int(user_id))
        self.nom_entry.delete(0, tk.END)
        self.nom_entry.insert(0, nom)
        self.role_var.set(role)
        self.mdp_entry.delete(0, tk.END) # Ne pas charger l'ancien MDP
        self.submit_btn.config(text="Modifier")

    def _submit_user(self):
        user_id = self.id_user.get() if self.id_user.get() != 0 else None
        nom = self.nom_entry.get()
        role = self.role_var.get()
        mdp = self.mdp_entry.get() if self.mdp_entry.get() else None

        if not nom or not role or (user_id is None and not mdp):
            messagebox.showerror("Erreur", "Nom, Rôle et Mot de Passe (pour nouvel utilisateur) sont requis.")
            return

        success = self.controller.logic.add_or_update_user(user_id, nom, role, mdp)
        
        if success:
            messagebox.showinfo("Succès", f"Utilisateur {'modifié' if user_id else 'ajouté'} avec succès.")
            self._load_users()
            self._clear_form()
        else:
            messagebox.showerror("Erreur", "Nom d'utilisateur déjà existant.")
            
class GestionFournFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Gestion Fournisseurs et Assurances")

        # Note: Ce frame devrait être un onglet (Notebook) pour les deux gestions.
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab 1: Fournisseurs
        self.fourn_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.fourn_tab, text='Fournisseurs')
        self._setup_fournisseur_tab(self.fourn_tab)

        # Tab 2: Sociétés d'Assurance
        self.assurance_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.assurance_tab, text="Sociétés d'Assurance")
        self._setup_assurance_tab(self.assurance_tab)
        
    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def on_show(self, data=None):
        self._load_fournisseurs()
        self._load_societes()

    # --- Configuration Fournisseurs ---
    def _setup_fournisseur_tab(self, tab):
        self.fourn_id = tk.IntVar()
        
        form_frame = ttk.LabelFrame(tab, text="Ajouter / Modifier Fournisseur")
        form_frame.pack(fill='x', padx=10, pady=5)
        
        fields = [("Nom:", "fourn_nom_entry"), ("Contact:", "fourn_contact_entry"), ("Ville:", "fourn_ville_entry")]
        for i, (label_text, entry_name) in enumerate(fields):
            ttk.Label(form_frame, text=label_text).grid(row=0, column=i*2, padx=5, pady=5)
            entry = ttk.Entry(form_frame, width=20)
            entry.grid(row=0, column=i*2+1, padx=5, pady=5)
            setattr(self, entry_name, entry)
            
        self.fourn_submit_btn = ttk.Button(form_frame, text="Ajouter", command=self._submit_fournisseur)
        self.fourn_submit_btn.grid(row=0, column=6, padx=10, pady=5)
        ttk.Button(form_frame, text="Effacer", command=self._clear_fourn_form).grid(row=0, column=7, padx=5, pady=5)

        self.fourn_tree = ttk.Treeview(tab, columns=('id', 'nom', 'contact', 'ville'), show='headings', height=10)
        for col in self.fourn_tree['columns']:
            self.fourn_tree.heading(col, text=col.capitalize())
        self.fourn_tree.column('id', width=50, anchor=tk.CENTER)
        self.fourn_tree.pack(fill='x', padx=10, pady=10)
        self.fourn_tree.bind('<<TreeviewSelect>>', self._load_selected_fourn)
        
    def _load_fournisseurs(self):
        for i in self.fourn_tree.get_children(): self.fourn_tree.delete(i)
        for fourn in self.controller.logic.get_all_fournisseurs():
            self.fourn_tree.insert('', 'end', values=fourn)

    def _clear_fourn_form(self):
        self.fourn_id.set(0)
        self.fourn_nom_entry.delete(0, tk.END)
        self.fourn_contact_entry.delete(0, tk.END)
        self.fourn_ville_entry.delete(0, tk.END)
        self.fourn_submit_btn.config(text="Ajouter")

    def _load_selected_fourn(self, event):
        selected_item = self.fourn_tree.focus()
        if not selected_item: return
        fourn_id, nom, contact, ville = self.fourn_tree.item(selected_item, 'values')
        
        self.fourn_id.set(int(fourn_id))
        self.fourn_nom_entry.delete(0, tk.END)
        self.fourn_nom_entry.insert(0, nom)
        self.fourn_contact_entry.delete(0, tk.END)
        self.fourn_contact_entry.insert(0, contact)
        self.fourn_ville_entry.delete(0, tk.END)
        self.fourn_ville_entry.insert(0, ville)
        self.fourn_submit_btn.config(text="Modifier")

    def _submit_fournisseur(self):
        fourn_id = self.fourn_id.get() if self.fourn_id.get() != 0 else None
        nom = self.fourn_nom_entry.get()
        contact = self.fourn_contact_entry.get()
        ville = self.fourn_ville_entry.get()

        if not nom:
            messagebox.showerror("Erreur", "Le nom du fournisseur est obligatoire.")
            return

        success = self.controller.logic.add_or_update_fournisseur(fourn_id, nom, contact, ville)
        
        if success:
            messagebox.showinfo("Succès", f"Fournisseur {'modifié' if fourn_id else 'ajouté'} avec succès.")
            self._load_fournisseurs()
            self._clear_fourn_form()
        else:
            messagebox.showerror("Erreur", "Échec de l'opération (Nom déjà existant?).")
            
    # --- Configuration Assurances ---
    def _setup_assurance_tab(self, tab):
        self.societe_id = tk.IntVar()

        form_frame = ttk.LabelFrame(tab, text="Ajouter / Modifier Société Assurance")
        form_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(form_frame, text="Nom:").grid(row=0, column=0, padx=5, pady=5)
        self.soc_nom_entry = ttk.Entry(form_frame, width=20)
        self.soc_nom_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Contact:").grid(row=0, column=2, padx=5, pady=5)
        self.soc_contact_entry = ttk.Entry(form_frame, width=20)
        self.soc_contact_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(form_frame, text="Taux Base (%):").grid(row=1, column=0, padx=5, pady=5)
        self.soc_taux_entry = ttk.Entry(form_frame, width=10)
        self.soc_taux_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.soc_submit_btn = ttk.Button(form_frame, text="Ajouter", command=self._submit_societe)
        self.soc_submit_btn.grid(row=1, column=3, padx=10, pady=5)
        ttk.Button(form_frame, text="Effacer", command=self._clear_societe_form).grid(row=1, column=4, padx=5, pady=5)
        
        self.soc_tree = ttk.Treeview(tab, columns=('id', 'nom', 'contact', 'taux_base'), show='headings', height=10)
        for col in self.soc_tree['columns']:
            self.soc_tree.heading(col, text=col.capitalize())
        self.soc_tree.column('id', width=50, anchor=tk.CENTER)
        self.soc_tree.column('taux_base', width=100, anchor=tk.CENTER)
        self.soc_tree.pack(fill='x', padx=10, pady=10)
        self.soc_tree.bind('<<TreeviewSelect>>', self._load_selected_societe)

    def _load_societes(self):
        for i in self.soc_tree.get_children(): self.soc_tree.delete(i)
        for societe in self.controller.logic.get_all_societes():
            soc_id, nom, contact, taux = societe
            self.soc_tree.insert('', 'end', values=(soc_id, nom, contact, f"{taux * 100:.0f}%"))

    def _clear_societe_form(self):
        self.societe_id.set(0)
        self.soc_nom_entry.delete(0, tk.END)
        self.soc_contact_entry.delete(0, tk.END)
        self.soc_taux_entry.delete(0, tk.END)
        self.soc_submit_btn.config(text="Ajouter")

    def _load_selected_societe(self, event):
        selected_item = self.soc_tree.focus()
        if not selected_item: return
        soc_id, nom, contact, taux_str = self.soc_tree.item(selected_item, 'values')
        
        self.societe_id.set(int(soc_id))
        self.soc_nom_entry.delete(0, tk.END)
        self.soc_nom_entry.insert(0, nom)
        self.soc_contact_entry.delete(0, tk.END)
        self.soc_contact_entry.insert(0, contact)
        self.soc_taux_entry.delete(0, tk.END)
        self.soc_taux_entry.insert(0, taux_str.replace('%', '')) # Remet le taux en pourcentage
        self.soc_submit_btn.config(text="Modifier")
        
    def _submit_societe(self):
        soc_id = self.societe_id.get() if self.societe_id.get() != 0 else None
        nom = self.soc_nom_entry.get()
        contact = self.soc_contact_entry.get()
        
        try:
            taux_base = float(self.soc_taux_entry.get()) / 100.0 # Convertir pourcentage en décimal
            if not nom or taux_base < 0 or taux_base > 1:
                raise ValueError("Nom requis ou Taux invalide.")
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Le taux doit être un nombre valide entre 0 et 100.")
            return

        success = self.controller.logic.add_or_update_societe(soc_id, nom, contact, taux_base)
        
        if success:
            messagebox.showinfo("Succès", f"Société {'modifiée' if soc_id else 'ajoutée'} avec succès.")
            self._load_societes()
            self._clear_societe_form()
        else:
            messagebox.showerror("Erreur", "Échec de l'opération (Nom déjà existant?).")

class ModifierLotFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.med_id = None
        self._create_header("Détails des Lots et Modification")

        # Infos Médoc
        info_frame = ttk.Frame(self)
        info_frame.pack(fill='x', padx=10, pady=5)
        self.med_name_label = ttk.Label(info_frame, text="Médicament: N/A", font=('Segoe UI', 12, 'bold'))
        self.med_name_label.pack(side='left')

        # Liste des Lots
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id', 'numero_lot', 'quantite', 'date_expiration', 'date_livraison', 'emplacement')
        self.lots_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        for col in columns:
            self.lots_tree.heading(col, text=col.replace('_', ' ').capitalize())
        self.lots_tree.pack(fill='both', expand=True)

        # Formulaire de modification
        mod_frame = ttk.LabelFrame(self, text="Modifier Lot Sélectionné")
        mod_frame.pack(fill='x', padx=10, pady=5)
        
        self.lot_id = tk.IntVar()
        
        ttk.Label(mod_frame, text="N° Lot:").grid(row=0, column=0, padx=5, pady=5)
        self.lot_num_display = ttk.Label(mod_frame, text="N/A")
        self.lot_num_display.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(mod_frame, text="Nouvelle Quantité:").grid(row=0, column=2, padx=5, pady=5)
        self.new_qte_entry = ttk.Entry(mod_frame, width=15)
        self.new_qte_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(mod_frame, text="Nouvelle Date Exp. (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5)
        self.new_date_exp_entry = ttk.Entry(mod_frame, width=15)
        self.new_date_exp_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(mod_frame, text="Appliquer Modification", style="Primary.TButton", command=self._apply_modification).grid(row=1, column=3, padx=10, pady=5)
        
        self.lots_tree.bind('<<TreeviewSelect>>', self._load_selected_lot)
        
    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Stock", command=lambda: self.controller.show_frame("stock")).pack(side='right')

    def on_show(self, med_id: int):
        if med_id:
            self.med_id = med_id
            med_info = self.controller.logic.get_medicament_by_id(med_id)
            self.med_name_label.config(text=f"Médicament: {med_info[1]}")
            self._load_lots()
            self._clear_form()

    def _load_lots(self):
        for i in self.lots_tree.get_children(): self.lots_tree.delete(i)
        
        if self.med_id:
            lots = self.controller.logic.get_lots_by_med_id(self.med_id)
            for lot in lots:
                self.lots_tree.insert('', 'end', values=lot)

    def _clear_form(self):
        self.lot_id.set(0)
        self.lot_num_display.config(text="N/A")
        self.new_qte_entry.delete(0, tk.END)
        self.new_date_exp_entry.delete(0, tk.END)

    def _load_selected_lot(self, event):
        selected_item = self.lots_tree.focus()
        if not selected_item: return
        
        lot_id, numero_lot, quantite, date_expiration, _, _ = self.lots_tree.item(selected_item, 'values')
        
        self.lot_id.set(int(lot_id))
        self.lot_num_display.config(text=numero_lot)
        self.new_qte_entry.delete(0, tk.END)
        self.new_qte_entry.insert(0, quantite)
        self.new_date_exp_entry.delete(0, tk.END)
        self.new_date_exp_entry.insert(0, date_expiration)

    def _apply_modification(self):
        if self.lot_id.get() == 0:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un lot à modifier.")
            return

        try:
            lot_id = self.lot_id.get()
            nouvelle_qte = int(self.new_qte_entry.get())
            nouvelle_date_exp = self.new_date_exp_entry.get()
            
            if nouvelle_qte < 0:
                messagebox.showerror("Erreur", "La quantité ne peut pas être négative.")
                return
            if not re.match(r"\d{4}-\d{2}-\d{2}", nouvelle_date_exp):
                 raise ValueError("Format de date invalide (YYYY-MM-DD).")

            if self.controller.logic.modifier_details_lot(lot_id, nouvelle_qte, nouvelle_date_exp):
                messagebox.showinfo("Succès", "Lot modifié avec succès.")
                self._load_lots()
                self._clear_form()
            else:
                messagebox.showerror("Échec", "Impossible de modifier le lot.")
        except ValueError as e:
            messagebox.showerror("Erreur de Saisie", f"Valeur invalide: {e}")

class AjustementStockFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.med_id = None
        self._create_header("Ajustement Manuel du Stock")
        
        # Infos Médoc
        info_frame = ttk.Frame(self)
        info_frame.pack(fill='x', padx=10, pady=5)
        self.med_name_label = ttk.Label(info_frame, text="Médicament: N/A", font=('Segoe UI', 12, 'bold'))
        self.med_name_label.pack(side='left')
        self.current_qte_label = ttk.Label(info_frame, text="Stock Actuel: N/A", font=('Segoe UI', 12, 'italic'))
        self.current_qte_label.pack(side='right')

        # Formulaire d'Ajustement
        form_frame = ttk.LabelFrame(self, text="Opération d'Ajustement (Création ou Retrait)")
        form_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(form_frame, text="Quantité à ajuster (Positif = ajout, Négatif = retrait):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.qte_ajustement_entry = ttk.Entry(form_frame, width=15)
        self.qte_ajustement_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(form_frame, text="Raison de l'ajustement:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.raison_entry = ttk.Entry(form_frame, width=40)
        self.raison_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky='w')

        ttk.Button(form_frame, text="Appliquer l'Ajustement", style="Primary.TButton", command=self._apply_ajustement).grid(row=2, column=0, columnspan=3, pady=10)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Stock", command=lambda: self.controller.show_frame("stock")).pack(side='right')

    def on_show(self, med_id: int):
        self.med_id = med_id
        med_info = self.controller.logic.get_medicament_by_id(med_id)
        current_stock = self.controller.logic.get_stock_actuel()
        
        qte_actuelle = 0
        for item in current_stock:
            if item[0] == med_id:
                qte_actuelle = item[4]
                break
        
        self.med_name_label.config(text=f"Médicament: {med_info[1]} (ID: {med_id})")
        self.current_qte_label.config(text=f"Stock Actuel: {qte_actuelle}")
        self.qte_ajustement_entry.delete(0, tk.END)
        self.raison_entry.delete(0, tk.END)
        
    def _apply_ajustement(self):
        if not self.med_id: return
        
        try:
            qte_ajustement = int(self.qte_ajustement_entry.get())
            raison = self.raison_entry.get()

            if not raison:
                messagebox.showwarning("Raison Requise", "Veuillez fournir une raison pour cet ajustement.")
                return

            if self.controller.logic.ajuster_stock_manuel(self.med_id, qte_ajustement, raison):
                messagebox.showinfo("Succès", "Ajustement de stock appliqué avec succès.")
                self.controller.show_frame("stock")
            else:
                messagebox.showerror("Échec", "Échec de l'ajustement (stock négatif ou erreur BD).")
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Quantité à ajuster invalide.")

class ModifierSeuilsFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.med_id = None
        self._create_header("Modification des Seuils d'Alerte/Commande")
        
        # Infos Médoc
        info_frame = ttk.Frame(self)
        info_frame.pack(fill='x', padx=10, pady=5)
        self.med_name_label = ttk.Label(info_frame, text="Médicament: N/A", font=('Segoe UI', 12, 'bold'))
        self.med_name_label.pack(side='left')

        # Formulaire
        form_frame = ttk.LabelFrame(self, text="Nouveaux Seuils")
        form_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(form_frame, text="Seuil d'Alerte (Stock Min):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.seuil_alerte_entry = ttk.Entry(form_frame, width=15)
        self.seuil_alerte_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(form_frame, text="Quantité Min. de Commande:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.qte_min_cmd_entry = ttk.Entry(form_frame, width=15)
        self.qte_min_cmd_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Button(form_frame, text="Appliquer les Seuils", style="Primary.TButton", command=self._apply_seuils).grid(row=2, column=0, columnspan=2, pady=10)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Référence", command=lambda: self.controller.show_frame("recherche")).pack(side='right')

    def on_show(self, med_id: int):
        self.med_id = med_id
        med_info = self.controller.logic.get_medicament_by_id(med_id)
        # Tuple: id, nom, code_numerique, prix_unitaire, prix_achat, seuil_alerte, qte_min_commande, qte_max_commande, rayon, dci
        
        self.med_name_label.config(text=f"Médicament: {med_info[1]} (ID: {med_id})")
        
        self.seuil_alerte_entry.delete(0, tk.END)
        self.seuil_alerte_entry.insert(0, med_info[5])
        
        self.qte_min_cmd_entry.delete(0, tk.END)
        self.qte_min_cmd_entry.insert(0, med_info[6])
        
    def _apply_seuils(self):
        if not self.med_id: return
        
        try:
            seuil_alerte = int(self.seuil_alerte_entry.get())
            qte_min_commande = int(self.qte_min_cmd_entry.get())

            if seuil_alerte < 0 or qte_min_commande < 0:
                messagebox.showerror("Erreur", "Les seuils ne peuvent être négatifs.")
                return

            if self.controller.logic.modifier_seuils_medicament(self.med_id, seuil_alerte, qte_min_commande):
                messagebox.showinfo("Succès", "Seuils modifiés avec succès.")
                self.controller.show_frame("recherche")
            else:
                messagebox.showerror("Échec", "Échec de la modification des seuils.")
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Veuillez entrer des nombres entiers valides.")
            
class GestionAssurancesFrame(BaseFrame):
    # Ceci est un placeholder, car la gestion des assurances est incluse dans GestionFournFrame pour l'instant
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Gestion des Contrats d'Assurance (A Développer)")

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

class InventaireFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._create_header("Inventaire Global et Valorisation")

        # Liste
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id', 'nom', 'code', 'qte', 'prix_a', 'prix_v', 'val_a', 'val_v')
        self.inventaire_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        
        self.inventaire_tree.heading('id', text='ID')
        self.inventaire_tree.heading('nom', text='Nom')
        self.inventaire_tree.heading('code', text='Code')
        self.inventaire_tree.heading('qte', text='Stock')
        self.inventaire_tree.heading('prix_a', text='Prix Achat U.')
        self.inventaire_tree.heading('prix_v', text='Prix Vente U.')
        self.inventaire_tree.heading('val_a', text='Valorisation Achat')
        self.inventaire_tree.heading('val_v', text='Valorisation Vente')
        
        self.inventaire_tree.pack(fill='both', expand=True, side='left')
        
        # Scrollbar
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.inventaire_tree.yview)
        vsb.pack(side='right', fill='y')
        self.inventaire_tree.configure(yscrollcommand=vsb.set)
        
        # Totaux
        footer_frame = ttk.Frame(self)
        footer_frame.pack(fill='x', padx=10, pady=5)
        self.total_achat_label = ttk.Label(footer_frame, text="Total Valorisation Achat: 0.00 XOF", font=('Segoe UI', 12, 'bold'))
        self.total_achat_label.pack(side='left', padx=10)
        self.total_vente_label = ttk.Label(footer_frame, text="Total Valorisation Vente: 0.00 XOF", font=('Segoe UI', 12, 'bold'))
        self.total_vente_label.pack(side='right', padx=10)

    def _create_header(self, title):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(header_frame, text=title, font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Retour Menu", command=lambda: self.controller.show_frame("menu_gestion")).pack(side='right')

    def on_show(self, data=None):
        for i in self.inventaire_tree.get_children():
            self.inventaire_tree.delete(i)
        
        inventaire = self.controller.logic.get_inventaire_global()
        total_val_achat = 0.0
        total_val_vente = 0.0
        
        for item in inventaire:
            med_id, nom, code, qte, prix_a, prix_v = item
            
            val_a = qte * prix_a
            val_v = qte * prix_v
            
            total_val_achat += val_a
            total_val_vente += val_v
            
            self.inventaire_tree.insert('', 'end', values=(
                med_id, nom, code, qte, f"{prix_a:.2f}", f"{prix_v:.2f}", f"{val_a:.2f}", f"{val_v:.2f}"
            ))
            
        self.total_achat_label.config(text=f"Total Valorisation Achat: {total_val_achat:.2f} XAF")
        self.total_vente_label.config(text=f"Total Valorisation Vente: {total_val_vente:.2f} XAF")

# Point d'entrée de l'application
if __name__ == "__main__":
    app = PharmacieApp()
    app.mainloop()
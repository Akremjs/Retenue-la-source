# CDC v2 — Roadmap Retenue à la source (retenue_source_tn)

Objectif : aligner le module sur le CDC Tunisie / TEJ, par phases.

## Phase 1 — Controles metier (livree)
- [x] Seuil configurable (défaut 1000 TND)
- [x] Types d'opérations TEJ (codes + taux indicatifs)
- [x] Lien taxe Odoo ↔ type TEJ
- [x] Blocage / alerte sous seuil
- [x] Controle matricule (VAT) partenaire
- [x] Exoneration partenaire
- [x] Deploye sur merkago.net

## Phase 2 — Certificat PDF (livree 17.0.2.0.0)
- [x] Rapport PDF certificat RAS
- [x] Numéro certificat + archivage (séquence CERT-RAS)
- [x] Envoi email au beneficiaire

## Phase 3 — Declaration mensuelle (livree 17.0.2.0.0)
- [x] Wizard mois / annee
- [x] Lignes agregees / liées aux documents RAS
- [x] Etats : brouillon → valide → depose → paye
- [x] Alerte échéance J-7 / J-1 (cron activités)

## Phase 4 — Export XML TEJ (livree 17.0.2.0.0)
- [x] Generation XML UTF-8 structure DeclarationsRS (CCT V2.0)
- [x] Nom fichier [MATRICULE]-[EXERCICE]-[MOIS]-[ACTE].xml
- [x] Fichier rectificatif (acte dépôt 1 / ModifierCertificats)
- [x] Guide depot : https://tej.finances.gov.tn
- [x] Validation XSD optionnelle si fichiers placés dans data/tej/

## Hors scope v2
- API depot automatique TEJ
- RAS salaires / CNSS
- Facturation electronique TEIF

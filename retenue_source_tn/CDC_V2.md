# CDC v2 — Roadmap Retenue à la source (retenue_source_tn)

Objectif : aligner le module sur le CDC Tunisie / TEJ, par phases.

## Phase 1 — Controles metier (livree 17.0.1.1.0)
- [x] Seuil configurable (défaut 1000 TND)
- [x] Types d'opérations TEJ (codes + taux indicatifs)
- [x] Lien taxe Odoo ↔ type TEJ
- [x] Blocage / alerte sous seuil
- [x] Controle matricule (VAT) partenaire
- [x] Exoneration partenaire
- [x] Deploye sur merkago.net

## Phase 2 — Certificat PDF
- [ ] Rapport PDF certificat RAS
- [ ] Numéro certificat + archivage
- [ ] Envoi email au beneficiaire

## Phase 3 — Declaration mensuelle
- [ ] Wizard mois / annee
- [ ] Lignes agregees par type / partenaire
- [ ] Etats : brouillon → valide → depose → paye
- [ ] Alerte échéance J-7 / J-1 (28 du mois suivant)

## Phase 4 — Export XML TEJ
- [ ] Generation XML UTF-8 conforme XSD
- [ ] Nom fichier [MATRICULE]-[EXERCICE]-[MOIS]-[ACTE].xml
- [ ] Fichier rectificatif
- [ ] Guide depot tej.finances.gov.tn

## Hors scope v2
- API depot automatique TEJ
- RAS salaires / CNSS
- Facturation electronique TEIF

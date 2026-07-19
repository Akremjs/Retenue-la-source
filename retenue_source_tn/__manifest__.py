# -*- coding: utf-8 -*-
{
    "name": "Retenue à la source (Tunisie)",
    "version": "18.0.2.0.2",
    "category": "Accounting/Localizations",
    "summary": "Retenue à la source clients et fournisseurs - Tunisie",
    "description": """
Retenue à la source - Tunisie
=============================

Gerez la retenue à la source sur vos factures clients et fournisseurs Odoo.
Conforme a la reglementation tunisienne (CDC v2 phases 1-4).

Fonctionnement
--------------
* Assistant depuis la facture comptabilisee (client / fournisseur)
* Calcul automatique de la base (hors timbre fiscal)
* Seuil RAS configurable (defaut 1000)
* Types d'operations TEJ + lien sur les taxes
* Controles matricule / exoneration partenaire
* Ecriture comptable dediee + lettrage automatique
* Certificat PDF + envoi email
* Declaration mensuelle RAS
* Export XML TEJ (depot manuel sur tej.finances.gov.tn)

Support - AKREM.KHELIFI
-----------------------
Email : akremkhelifi07@gmail.com
WhatsApp : +216 54 444 373
""",
    "author": "AKREM.KHELIFI",
    "website": "https://merkago.net",
    "license": "OPL-1",
    "price": 71.43,
    "currency": "USD",
    "depends": ["account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/retenue_source_type_data.xml",
        "report/retenue_source_report_actions.xml",
        "report/retenue_source_certificate_report.xml",
        "data/mail_template_and_cron.xml",
        "views/retenue_source_type_views.xml",
        "views/account_journal_views.xml",
        "views/account_tax_views.xml",
        "views/account_payment_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_move_views.xml",
        "views/retenu_source_record_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/retenu_source_wizard_views.xml",
        "wizard/retenue_source_declaration_wizard_views.xml",
        "views/retenue_source_declaration_views.xml",
    ],
    "images": ["static/description/banner.png", "static/description/cover.png"],
    "installable": True,
    "application": True,
}

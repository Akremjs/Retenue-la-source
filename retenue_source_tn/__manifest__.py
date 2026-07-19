# -*- coding: utf-8 -*-
{
    "name": "Retenue à la source (Tunisie)",
    "version": "17.0.1.2.3",
    "category": "Accounting/Localizations",
    "summary": "Retenue à la source clients et fournisseurs - Tunisie",
    "description": """
Retenue à la source - Tunisie
=============================

Gerez la retenue à la source sur vos factures clients et fournisseurs Odoo.
Conforme a la règlementation tunisienne (phase CDC v2.1).

Fonctionnement
--------------
* Assistant depuis la facture comptabilisée (client / fournisseur)
* Calcul automatique de la base (hors timbre fiscal)
* Seuil RAS configurable (défaut 1000)
* Types d'opérations TEJ + lien sur les taxes
* Controles matricule / exonération partenaire
* Écriture comptable dediee + lettrage automatique
* Documents RAS avec cycle brouillon / comptabilise / annule

Support - AKREM.KHELIFI
-----------------------
Email : akremkhelifi07@gmail.com
WhatsApp : +216 54 444 373
""",
    "author": "AKREM.KHELIFI",
    "website": "https://merkago.net",
    "license": "OPL-1",
    "price": 50.0,
    "currency": "USD",
    "depends": ["account", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/retenue_source_type_data.xml",
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
    ],
    "images": ["static/description/banner.png", "static/description/cover.png"],
    "installable": True,
    "application": True,
}

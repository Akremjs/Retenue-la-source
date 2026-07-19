# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    rs_threshold_amount = fields.Float(
        string="Seuil RAS (HT)",
        default=1000.0,
        help="Montant minimum de base pour appliquer la retenue à la source (défaut 1000 TND).",
    )
    rs_enforce_threshold = fields.Boolean(
        string="Bloquer sous seuil",
        default=True,
        help="Si active, empêche la creation d'une RAS si la base est sous le seuil.",
    )
    rs_require_partner_vat = fields.Boolean(
        string="Exiger matricule fiscal",
        default=True,
        help="Si active, exige un matricule/VAT sur le partenaire avant creation RAS.",
    )

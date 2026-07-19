# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    rs_retenue_exempt = fields.Boolean(
        string="Exonéré RAS",
        help="Si coche, aucune retenue à la source ne peut etre creee pour ce partenaire.",
    )
    rs_retenue_exempt_reason = fields.Char(string="Motif exonération RAS")
    rs_tej_id_type = fields.Selection(
        [
            ("1", "Matricule fiscal"),
            ("2", "CIN"),
            ("3", "Passeport"),
            ("4", "Carte de séjour"),
            ("5", "Autre identifiant fiscal"),
        ],
        string="Type identifiant TEJ",
        default="1",
    )
    rs_tej_category = fields.Selection(
        [
            ("pp", "Personne physique"),
            ("pm", "Personne morale"),
        ],
        string="Catégorie contribuable TEJ",
        default="pm",
    )
    rs_tej_resident = fields.Boolean(string="Résident Tunisie", default=True)
    rs_tej_activity = fields.Char(string="Activité TEJ")
    rs_tej_birth_date = fields.Date(string="Date de naissance (TEJ)")
    rs_tej_id_country_id = fields.Many2one(
        "res.country",
        string="Pays identifiant TEJ",
        help="Requis pour passeport / carte de séjour / autre identifiant.",
    )

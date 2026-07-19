# -*- coding: utf-8 -*-
from odoo import fields, models


class RetenueSourceType(models.Model):
    _name = "retenue.source.type"
    _description = "Type operation RAS / TEJ"
    _order = "sequence, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help="Code interne Odoo")
    tej_code = fields.Char(
        string="Code TEJ (IdTypeOperation)",
        help="Code officiel IdTypeOperation pour le XML TEJ.",
    )
    sequence = fields.Integer(default=10)
    rate = fields.Float(
        string="Taux %",
        digits=(16, 3),
        help="Taux indicatif. La taxe Odoo liee reste la source de calcul.",
    )
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Le code type RAS doit etre unique."),
    ]

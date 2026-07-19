# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    rs_retenu_tax = fields.Boolean(string="Taxe RAS")
    rs_type_id = fields.Many2one(
        "retenue.source.type",
        string="Type d'opération TEJ",
        help="Code / nature d'operation pour la declaration TEJ.",
    )

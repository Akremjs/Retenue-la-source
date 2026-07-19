# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    rs_retenue_exempt = fields.Boolean(
        string="Exonéré RAS",
        help="Si coche, aucune retenue à la source ne peut etre creee pour ce partenaire.",
    )
    rs_retenue_exempt_reason = fields.Char(string="Motif exonération RAS")

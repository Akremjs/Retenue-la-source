# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    rs_numero_document = fields.Char(string="Numéro de document")
    rs_clearing_date = fields.Date(string="Date d'échéance")
    rs_source_bank_id = fields.Many2one(
        "res.bank",
        string="Banque source",
    )
    rs_journal_type = fields.Selection(related="journal_id.type", string="Type de journal")

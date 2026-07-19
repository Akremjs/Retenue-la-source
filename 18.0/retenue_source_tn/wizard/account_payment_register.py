# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    rs_numero_document = fields.Char(string="Numéro de document")
    rs_clearing_date = fields.Date(string="Date d'échéance")
    rs_source_bank_id = fields.Many2one(
        "res.bank",
        string="Banque source",
    )
    rs_journal_type = fields.Selection(related="journal_id.type", string="Type de journal")

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update(
            {
                "rs_numero_document": self.rs_numero_document,
                "rs_clearing_date": self.rs_clearing_date,
                "rs_source_bank_id": self.rs_source_bank_id.id,
            }
        )
        return vals

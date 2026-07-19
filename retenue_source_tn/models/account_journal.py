# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    rs_withholding_sales = fields.Boolean(string="RAS Clients")
    rs_withholding_purchases = fields.Boolean(string="RAS Fournisseurs")

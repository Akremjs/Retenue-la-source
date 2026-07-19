# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rs_threshold_amount = fields.Float(
        related="company_id.rs_threshold_amount",
        readonly=False,
    )
    rs_enforce_threshold = fields.Boolean(
        related="company_id.rs_enforce_threshold",
        readonly=False,
    )
    rs_require_partner_vat = fields.Boolean(
        related="company_id.rs_require_partner_vat",
        readonly=False,
    )

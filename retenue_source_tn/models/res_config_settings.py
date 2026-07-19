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
    rs_tej_id_type = fields.Selection(
        related="company_id.rs_tej_id_type",
        readonly=False,
    )
    rs_tej_category = fields.Selection(
        related="company_id.rs_tej_category",
        readonly=False,
    )
    rs_tej_schema_version = fields.Char(
        related="company_id.rs_tej_schema_version",
        readonly=False,
    )

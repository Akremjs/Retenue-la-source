# -*- coding: utf-8 -*-
from odoo import fields, models


class RetenueSourceDeclarationWizard(models.TransientModel):
    _name = "retenue.source.declaration.wizard"
    _description = "Générer déclaration mensuelle RAS"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    month = fields.Selection(
        [(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month).zfill(2),
    )
    acte_depot = fields.Selection(
        [("0", "Initial (0)"), ("1", "Rectificatif (1)")],
        required=True,
        default="0",
    )

    def action_generate(self):
        self.ensure_one()
        Declaration = self.env["retenue.source.declaration"]
        existing = Declaration.search(
            [
                ("company_id", "=", self.company_id.id),
                ("year", "=", self.year),
                ("month", "=", self.month),
                ("acte_depot", "=", self.acte_depot),
            ],
            limit=1,
        )
        if existing:
            decl = existing
            if decl.state == "draft":
                decl.action_load_records()
        else:
            decl = Declaration.create(
                {
                    "company_id": self.company_id.id,
                    "year": self.year,
                    "month": self.month,
                    "acte_depot": self.acte_depot,
                }
            )
            decl.action_load_records()
        return {
            "type": "ir.actions.act_window",
            "name": "Déclaration RAS",
            "res_model": "retenue.source.declaration",
            "res_id": decl.id,
            "view_mode": "form",
            "target": "current",
        }

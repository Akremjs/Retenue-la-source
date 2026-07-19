# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RetenueSourceRecord(models.Model):
    _name = "retenue.source.record"
    _description = "Document de retenue à la source"
    _inherit = ["mail.thread"]
    _order = "date_reglement desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default="/",
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("posted", "Comptabilisé"),
            ("cancel", "Annulé"),
        ],
        string="Etat",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    move_type = fields.Selection(
        [("sale", "Client"), ("purchase", "Fournisseur")],
        string="Type",
        required=True,
    )
    invoice_id = fields.Many2one("account.move", string="Facture", required=True, ondelete="restrict")
    rs_account_move_id = fields.Many2one(
        "account.move", string="Écriture de retenue", readonly=True, ondelete="restrict"
    )
    partner_id = fields.Many2one("res.partner", string="Partenaire", related="invoice_id.partner_id", store=True)
    payment_journal_id = fields.Many2one("account.journal", string="Journal de paiement", required=True, ondelete="restrict")
    date_reglement = fields.Date(string="Date de règlement", required=True)
    memo = fields.Char(string="Mémo")
    withholding_tax_id = fields.Many2one("account.tax", string="Taxe de retenue", required=True, ondelete="restrict")
    rs_type_id = fields.Many2one(
        "retenue.source.type",
        string="Type d'opération TEJ",
        related="withholding_tax_id.rs_type_id",
        store=True,
        readonly=True,
    )
    withholding_number = fields.Char(string="N° de retenue")
    withholding_base_amount = fields.Monetary(string="Base de retenue", required=True, currency_field="currency_id")
    withholding_tax_amount = fields.Monetary(
        string="Montant retenu",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    payment_amount = fields.Monetary(
        string="Montant retenu",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        help="Montant de la retenue à la source (deduit de la base).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                move_type = vals.get("move_type", "sale")
                code = "retenue.source.record.sale" if move_type == "sale" else "retenue.source.record.purchase"
                vals["name"] = self.env["ir.sequence"].next_by_code(code) or "Nouveau"
        return super().create(vals_list)

    @api.depends("withholding_base_amount", "withholding_tax_id.amount", "withholding_tax_id.amount_type")
    def _compute_amounts(self):
        for rec in self:
            tax_amount = 0.0
            if rec.withholding_tax_id and rec.withholding_tax_id.amount_type == "percent":
                tax_amount = rec.withholding_base_amount * rec.withholding_tax_id.amount / 100.0
            rec.withholding_tax_amount = tax_amount
            rec.payment_amount = tax_amount

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seuls les documents RAS en brouillon peuvent être confirmés."))
            if not rec.rs_account_move_id:
                raise UserError(_("Aucune écriture de retenue trouvée. Impossible de confirmer."))
            if rec.rs_account_move_id.state == "draft":
                rec.rs_account_move_id.action_post()
            rec.state = "posted"

    def action_reset_to_draft_posted(self):
        for rec in self:
            if rec.state != "posted":
                raise UserError(_("Seuls les documents RAS comptabilisés peuvent être remis en brouillon."))
            move = rec.rs_account_move_id
            if move and move.state == "posted":
                move.line_ids.filtered(lambda l: l.reconciled).remove_move_reconcile()
                move.button_draft()
            rec.state = "draft"

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(_("Seuls les documents RAS annulés peuvent être remis en brouillon."))
            rec.write({"rs_account_move_id": False, "state": "draft"})

    def unlink(self):
        for rec in self:
            if rec.state == "posted":
                raise UserError(
                    _("Vous ne pouvez pas supprimer une retenue comptabilisée. Remettez-la d'abord en brouillon.")
                )
            move = rec.rs_account_move_id
            if move and move.state == "draft":
                rec.rs_account_move_id = False
                move.unlink()
        return super().unlink()

    def action_open_withholding_entry(self):
        self.ensure_one()
        return {
            "name": _("Écriture de retenue"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.rs_account_move_id.id,
            "context": {"create": False},
        }

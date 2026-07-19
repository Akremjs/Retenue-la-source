# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RetenueSourceRecord(models.Model):
    _name = "retenue.source.record"
    _description = "Document de retenue à la source"
    _inherit = ["mail.thread", "mail.activity.mixin"]
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
    certificate_number = fields.Char(
        string="N° certificat",
        copy=False,
        readonly=True,
        help="Ref_certif_chez_declarant pour TEJ.",
    )
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
    amount_untaxed = fields.Monetary(
        string="Montant HT",
        compute="_compute_certificate_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        string="Montant TVA",
        compute="_compute_certificate_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        string="Montant TTC",
        compute="_compute_certificate_amounts",
        store=True,
        currency_field="currency_id",
    )
    amount_net_served = fields.Monetary(
        string="Montant net servi",
        compute="_compute_certificate_amounts",
        store=True,
        currency_field="currency_id",
    )
    tax_rate = fields.Float(string="Taux RAS %", compute="_compute_amounts", store=True)
    invoice_year = fields.Char(string="Année facturation", compute="_compute_certificate_amounts", store=True)
    declaration_line_ids = fields.One2many(
        "retenue.source.declaration.line",
        "record_id",
        string="Lignes de déclaration",
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
            rate = 0.0
            if rec.withholding_tax_id and rec.withholding_tax_id.amount_type == "percent":
                rate = rec.withholding_tax_id.amount
                tax_amount = rec.withholding_base_amount * rate / 100.0
            rec.tax_rate = rate
            rec.withholding_tax_amount = tax_amount
            rec.payment_amount = tax_amount

    @api.depends(
        "invoice_id.amount_untaxed",
        "invoice_id.amount_tax",
        "invoice_id.amount_total",
        "invoice_id.invoice_date",
        "invoice_id.date",
        "withholding_base_amount",
        "withholding_tax_amount",
    )
    def _compute_certificate_amounts(self):
        for rec in self:
            invoice = rec.invoice_id
            if invoice:
                rec.amount_untaxed = abs(invoice.amount_untaxed or 0.0)
                rec.amount_tax = abs(invoice.amount_tax or 0.0)
                rec.amount_total = abs(invoice.amount_total or 0.0)
                inv_date = invoice.invoice_date or invoice.date
                rec.invoice_year = inv_date and str(inv_date.year) or ""
            else:
                rec.amount_untaxed = rec.withholding_base_amount
                rec.amount_tax = 0.0
                rec.amount_total = rec.withholding_base_amount
                rec.invoice_year = ""
            rec.amount_net_served = (rec.amount_total or 0.0) - (rec.withholding_tax_amount or 0.0)

    def _ensure_certificate_number(self):
        for rec in self:
            if not rec.certificate_number:
                rec.certificate_number = (
                    self.env["ir.sequence"].next_by_code("retenue.source.certificate") or rec.name
                )

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seuls les documents RAS en brouillon peuvent être confirmés."))
            if not rec.rs_account_move_id:
                raise UserError(_("Aucune écriture de retenue trouvée. Impossible de confirmer."))
            if rec.rs_account_move_id.state == "draft":
                rec.rs_account_move_id.action_post()
            rec._ensure_certificate_number()
            rec.state = "posted"

    def action_reset_to_draft_posted(self):
        for rec in self:
            if rec.state != "posted":
                raise UserError(_("Seuls les documents RAS comptabilisés peuvent être remis en brouillon."))
            if rec.declaration_line_ids.filtered(lambda l: l.declaration_id.state != "draft"):
                raise UserError(
                    _("Impossible : cette RAS est liée à une déclaration mensuelle déjà validée.")
                )
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

    def action_print_certificate(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("Comptabilisez la RAS avant d'imprimer le certificat."))
        self._ensure_certificate_number()
        return self.env.ref("retenue_source_tn.action_report_retenue_certificate").report_action(self)

    def action_send_certificate(self):
        self.ensure_one()
        if self.state != "posted":
            raise UserError(_("Comptabilisez la RAS avant d'envoyer le certificat."))
        self._ensure_certificate_number()
        template = self.env.ref("retenue_source_tn.mail_template_retenue_certificate", raise_if_not_found=False)
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", raise_if_not_found=False)
        ctx = {
            "default_model": "retenue.source.record",
            "default_res_ids": self.ids,
            "default_composition_mode": "comment",
            "default_use_template": bool(template),
            "default_template_id": template.id if template else False,
            "force_email": True,
            "mark_rs_certificate_sent": True,
        }
        return {
            "name": _("Envoyer certificat RAS"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")] if compose_form else [(False, "form")],
            "target": "new",
            "context": ctx,
        }

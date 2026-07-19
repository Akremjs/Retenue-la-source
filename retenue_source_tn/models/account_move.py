# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    retenue_source_record_ids = fields.One2many(
        "retenue.source.record",
        "invoice_id",
        string="Documents RAS",
        copy=False,
    )
    retenue_source_count = fields.Integer(
        compute="_compute_retenue_source_count",
        string="Nb RAS",
    )
    rs_has_retenu = fields.Boolean(
        compute="_compute_retenue_source_count",
        string="A une RAS",
    )

    @api.depends("retenue_source_record_ids")
    def _compute_retenue_source_count(self):
        for move in self:
            count = len(move.retenue_source_record_ids)
            move.retenue_source_count = count
            move.rs_has_retenu = count > 0

    def action_open_retenu_source_moves(self):
        self.ensure_one()
        move_id = self.retenue_source_record_ids[:1].rs_account_move_id
        return {
            "name": _("Retenue à la source"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move_id.id,
            "context": {"create": False},
        }

    def action_open_retenu_source_wizard(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "in_invoice"):
            raise UserError(_("La retenue à la source est disponible uniquement sur les factures clients et fournisseurs."))
        if self.state != "posted":
            raise UserError(_("Vous ne pouvez créer une RAS que depuis une facture comptabilisée."))
        if self.payment_state == "paid":
            raise UserError(_("La facture est déjà payee."))
        if self.rs_has_retenu:
            raise UserError(_("Cette facture a déjà une retenue à la source."))

        return {
            "name": _("Retenue à la source"),
            "type": "ir.actions.act_window",
            "res_model": "retenue.source.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_id": self.id,
            },
        }

    def unlink(self):
        for invoice in self:
            posted_retenu = invoice.retenue_source_record_ids.filtered(
                lambda r: r.state == "posted"
            )
            if posted_retenu:
                raise UserError(
                    _(
                        "Impossible de supprimer la facture '%s' : une RAS comptabilisée existe.\n"
                        "Remettez d'abord la RAS en brouillon puis supprimez-la."
                    ) % invoice.name
                )
            draft_or_cancel_retenu = invoice.retenue_source_record_ids.filtered(
                lambda r: r.state in ("draft", "cancel")
            )
            draft_or_cancel_retenu.unlink()
        return super().unlink()

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RetenueSourceWizard(models.TransientModel):
    _name = "retenue.source.wizard"
    _description = "Retenue à la source Wizard"

    invoice_id = fields.Many2one("account.move", string="Facture", required=True, readonly=True)
    move_type = fields.Selection(
        [("sale", "Client"), ("purchase", "Fournisseur")],
        string="Type",
        required=True,
        readonly=True,
    )
    payment_journal_id = fields.Many2one("account.journal", string="Journal de paiement", required=True, ondelete="restrict")
    withholding_tax_id = fields.Many2one("account.tax", string="Taxe de retenue", required=True, ondelete="restrict")
    withholding_number = fields.Char(string="N° de retenue")
    withholding_base_amount = fields.Monetary(string="Base de retenue", readonly=True, currency_field='currency_id')
    withholding_tax_amount = fields.Monetary(
        string="Montant retenu",
        compute="_compute_amounts",
        store=False,
        readonly=True,
        currency_field='currency_id'
    )
    payment_amount = fields.Monetary(
        string="Montant retenu",
        compute="_compute_amounts",
        store=False,
        readonly=True,
        currency_field='currency_id',
        help="Montant de la retenue à la source (deduit de la facture)",
    )
    date_reglement = fields.Date(string="Date de règlement", required=True, default=fields.Date.context_today)
    memo = fields.Char(string="Mémo")
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    rs_allowed_payment_journal_ids = fields.Many2many(
        "account.journal",
        compute="_compute_allowed_records",
    )
    rs_allowed_withholding_tax_ids = fields.Many2many(
        "account.tax",
        compute="_compute_allowed_records",
    )
    rs_type_id = fields.Many2one(
        "retenue.source.type",
        string="Type d'opération TEJ",
        related="withholding_tax_id.rs_type_id",
        readonly=True,
    )
    rs_threshold_amount = fields.Monetary(
        string="Seuil RAS",
        currency_field="currency_id",
        compute="_compute_threshold_info",
    )
    rs_below_threshold = fields.Boolean(compute="_compute_threshold_info")

    @api.depends("withholding_base_amount", "invoice_id.company_id", "currency_id")
    def _compute_threshold_info(self):
        for rec in self:
            company = rec.invoice_id.company_id or rec.env.company
            threshold = company.rs_threshold_amount or 0.0
            # Convert company threshold to invoice currency if needed
            if rec.currency_id and company.currency_id and rec.currency_id != company.currency_id and rec.invoice_id:
                threshold = company.currency_id._convert(
                    threshold,
                    rec.currency_id,
                    company,
                    rec.invoice_id.date or fields.Date.context_today(rec),
                )
            rec.rs_threshold_amount = threshold
            rec.rs_below_threshold = bool(threshold and rec.withholding_base_amount < threshold)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        invoice = self.env["account.move"].browse(self.env.context.get("default_invoice_id"))
        if invoice:
            timbre_amount = self._get_timbre_amount(invoice)
            inv_total = abs(invoice.amount_total or 0)
            if invoice.currency_id == invoice.company_id.currency_id:
                base = inv_total - timbre_amount
            else:
                timbre_inv_curr = invoice.company_id.currency_id._convert(
                    timbre_amount, invoice.currency_id, invoice.company_id, invoice.date
                )
                base = inv_total - abs(timbre_inv_curr)
            vals.update(
                {
                    "invoice_id": invoice.id,
                    "move_type": "sale" if invoice.move_type == "out_invoice" else "purchase",
                    "withholding_base_amount": max(0, base),
                    "currency_id": invoice.currency_id.id,
                }
            )
        return vals

    @api.model
    def _get_timbre_amount(self, invoice):
        """Return stamp-duty amount in company currency."""
        tax_timbre_lines = invoice.line_ids.filtered(
            lambda l: l.tax_line_id and getattr(l.tax_line_id, "rs_is_timbre_fiscal_tax", False)
        )
        amount = sum(abs(l.balance) for l in tax_timbre_lines)
        codes = ("TIMBRE_FISCAL", "AKREM_TF", "TF")
        product_lines = invoice.line_ids.filtered(
            lambda l: l.product_id
            and l.product_id.default_code in codes
            and l.display_type == "product"
        )
        amount += sum(abs(l.balance) for l in product_lines)
        return amount

    @api.depends("move_type")
    def _compute_allowed_records(self):
        Journal = self.env["account.journal"]
        Tax = self.env["account.tax"]
        for rec in self:
            if rec.move_type == "sale":
                rec.rs_allowed_payment_journal_ids = Journal.search([("rs_withholding_sales", "=", True)])
                rec.rs_allowed_withholding_tax_ids = Tax.search(
                    [("type_tax_use", "=", "sale"), ("rs_retenu_tax", "=", True), ("active", "=", True)]
                )
            elif rec.move_type == "purchase":
                rec.rs_allowed_payment_journal_ids = Journal.search([("rs_withholding_purchases", "=", True)])
                rec.rs_allowed_withholding_tax_ids = Tax.search(
                    [("type_tax_use", "=", "purchase"), ("rs_retenu_tax", "=", True), ("active", "=", True)]
                )
            else:
                rec.rs_allowed_payment_journal_ids = Journal.browse()
                rec.rs_allowed_withholding_tax_ids = Tax.browse()

    @api.onchange("move_type")
    def _onchange_move_type(self):
        self.payment_journal_id = False
        self.withholding_tax_id = False

    @api.onchange("payment_journal_id")
    def _onchange_payment_journal_id(self):
        self.withholding_tax_id = False

    @api.depends("withholding_base_amount", "withholding_tax_id.amount", "withholding_tax_id.amount_type")
    def _compute_amounts(self):
        for rec in self:
            tax_amount = 0.0
            if rec.withholding_tax_id and rec.withholding_tax_id.amount_type == "percent":
                tax_amount = rec.withholding_base_amount * rec.withholding_tax_id.amount / 100.0
            rec.withholding_tax_amount = tax_amount
            rec.payment_amount = tax_amount

    def _check_cdc_controls(self):
        """Phase 1 CDC controls: exemption, VAT, threshold."""
        self.ensure_one()
        invoice = self.invoice_id
        partner = invoice.partner_id.commercial_partner_id
        company = invoice.company_id

        if partner.rs_retenue_exempt:
            raise ValidationError(
                _("Le partenaire %s est exonéré de RAS%s.")
                % (partner.display_name, (" (%s)" % partner.rs_retenue_exempt_reason) if partner.rs_retenue_exempt_reason else "")
            )

        if company.rs_require_partner_vat and not (partner.vat or "").strip():
            raise ValidationError(
                _("Matricule fiscal (VAT) manquant pour le partenaire %s.") % partner.display_name
            )

        if company.rs_enforce_threshold and self.rs_below_threshold:
            raise ValidationError(
                _(
                    "Base RAS %(base).3f sous le seuil %(seuil).3f %(currency)s.\n"
                    "Desactivez 'Bloquer sous seuil' dans Parametres > Comptabilite si besoin."
                )
                % {
                    "base": self.withholding_base_amount,
                    "seuil": self.rs_threshold_amount,
                    "currency": self.currency_id.name or "",
                }
            )

        if self.withholding_tax_id and not self.withholding_tax_id.rs_type_id:
            raise ValidationError(
                _("Associez un type d'opération TEJ sur la taxe '%s'.") % self.withholding_tax_id.display_name
            )

    def action_create_retenu_record(self):
        self.ensure_one()
        invoice = self.invoice_id
        if invoice.payment_state == "paid":
            raise ValidationError(_("La facture est déjà payee."))
        if self.withholding_tax_amount <= 0.0:
            raise ValidationError(_("Le montant de la retenue doit etre supérieur a zero."))

        self._check_cdc_controls()

        # Create the retenu record in draft first
        record = self.env["retenue.source.record"].create(
            {
                "company_id": invoice.company_id.id,
                "currency_id": self.currency_id.id,
                "move_type": self.move_type,
                "invoice_id": invoice.id,
                "payment_journal_id": self.payment_journal_id.id,
                "date_reglement": self.date_reglement,
                "memo": self.memo,
                "withholding_tax_id": self.withholding_tax_id.id,
                "withholding_number": self.withholding_number,
                "withholding_base_amount": self.withholding_base_amount,
                "state": "draft",
            }
        )

        # Create and post the withholding journal entry
        rs_withholding_move = self._create_rs_withholding_move(invoice)
        record.rs_account_move_id = rs_withholding_move.id

        # Mark the retenu record as posted now that the journal entry is confirmed
        record.action_post()

        return {
            "name": _("Retenue à la source"),
            "type": "ir.actions.act_window",
            "res_model": "retenue.source.record",
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_rs_invoice_partner_line(self, invoice):
        if self.move_type == "sale":
            line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == "asset_receivable" and not l.reconciled
            )[:1]
        else:
            line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == "liability_payable" and not l.reconciled
            )[:1]
        if not line:
            raise UserError(_("Aucune ligne client/fournisseur ouverte trouvée sur la facture."))
        return line

    def _create_rs_withholding_move(self, invoice):
        """Create a separate journal entry (écriture) for retenue à la source in the chosen journal."""
        self.ensure_one()
        partner_line = self._get_rs_invoice_partner_line(invoice)
        journal = self.payment_journal_id
        journal_account = journal.default_account_id
        if not journal_account:
            raise UserError(
                _("Configurez un compte par défaut sur le journal %s pour comptabiliser la RAS.") % journal.display_name
            )

        company = invoice.company_id
        company_currency = company.currency_id
        amount_currency = self.withholding_tax_amount
        amount_company = self.currency_id._convert(amount_currency, company_currency, company, self.date_reglement)

        if abs(amount_company) < 10 ** (-company.currency_id.decimal_places - 1):
            raise UserError(_("Le montant de la retenue est nul dans la devise société."))

        if self.move_type == "sale":
            partner_debit = 0.0
            partner_credit = amount_company
            journal_debit = amount_company
            journal_credit = 0.0
            partner_amount_currency = -amount_currency
            journal_amount_currency = amount_currency
        else:
            partner_debit = amount_company
            partner_credit = 0.0
            journal_debit = 0.0
            journal_credit = amount_company
            partner_amount_currency = amount_currency
            journal_amount_currency = -amount_currency

        line_currency = self.currency_id if self.currency_id != company_currency else company_currency

        move_vals = {
            "move_type": "entry",
            "journal_id": journal.id,
            "date": self.date_reglement,
            "ref": "%s - %s" % (invoice.name or invoice.ref or invoice.display_name, self.withholding_number),
            "company_id": company.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": _("Retenue à la source %s") % (invoice.name or invoice.ref or ""),
                        "partner_id": invoice.partner_id.id,
                        "account_id": partner_line.account_id.id,
                        "debit": partner_debit,
                        "credit": partner_credit,
                        "currency_id": line_currency.id,
                        "amount_currency": partner_amount_currency,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": _("Retenue à la source %s") % self.withholding_number,
                        "partner_id": invoice.partner_id.id,
                        "account_id": journal_account.id,
                        "debit": journal_debit,
                        "credit": journal_credit,
                        "currency_id": line_currency.id,
                        "amount_currency": journal_amount_currency,
                    },
                ),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()

        retenue_partner_line = move.line_ids.filtered(
            lambda l: l.account_id == partner_line.account_id and not l.reconciled
        )[:1]
        (partner_line + retenue_partner_line).reconcile()
        return move
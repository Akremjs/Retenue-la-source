# -*- coding: utf-8 -*-
import calendar
from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RetenueSourceDeclaration(models.Model):
    _name = "retenue.source.declaration"
    _description = "Déclaration mensuelle RAS / TEJ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, month desc, id desc"

    name = fields.Char(string="Référence", required=True, copy=False, default="/")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    year = fields.Integer(string="Année", required=True, default=lambda self: fields.Date.context_today(self).year)
    month = fields.Selection(
        [(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
        string="Mois",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month).zfill(2),
    )
    acte_depot = fields.Selection(
        [
            ("0", "Initial (0)"),
            ("1", "Rectificatif (1)"),
        ],
        string="Acte de dépôt",
        required=True,
        default="0",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("confirmed", "Validée"),
            ("deposited", "Déposée"),
            ("paid", "Payée"),
        ],
        string="État",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many("retenue.source.declaration.line", "declaration_id", string="Lignes")
    record_ids = fields.Many2many(
        "retenue.source.record",
        string="Documents RAS",
        compute="_compute_record_ids",
    )
    deadline_date = fields.Date(string="Échéance TEJ", compute="_compute_deadline", store=True)
    total_base = fields.Monetary(compute="_compute_totals", store=True, currency_field="currency_id")
    total_rs = fields.Monetary(compute="_compute_totals", store=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    xml_filename = fields.Char(compute="_compute_xml_filename")
    xml_attachment_id = fields.Many2one("ir.attachment", string="Fichier XML", copy=False)
    notes = fields.Text()

    _sql_constraints = [
        (
            "uniq_company_period_acte",
            "unique(company_id, year, month, acte_depot)",
            "Une déclaration existe déjà pour cette société / période / acte.",
        ),
    ]

    @api.depends("line_ids.record_id")
    def _compute_record_ids(self):
        for decl in self:
            decl.record_ids = decl.line_ids.mapped("record_id")

    @api.depends("year", "month")
    def _compute_deadline(self):
        for decl in self:
            if not decl.year or not decl.month:
                decl.deadline_date = False
                continue
            month = int(decl.month)
            year = decl.year
            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1
            last_day = calendar.monthrange(next_year, next_month)[1]
            decl.deadline_date = date(next_year, next_month, last_day)

    @api.depends("line_ids.amount_base", "line_ids.amount_rs")
    def _compute_totals(self):
        for decl in self:
            decl.total_base = sum(decl.line_ids.mapped("amount_base"))
            decl.total_rs = sum(decl.line_ids.mapped("amount_rs"))

    @api.depends("company_id.vat", "year", "month", "acte_depot")
    def _compute_xml_filename(self):
        for decl in self:
            matricule = (decl.company_id.vat or "MATRICULE").replace(" ", "").upper()
            decl.xml_filename = "%s-%s-%s-%s.xml" % (
                matricule,
                decl.year or "YYYY",
                decl.month or "MM",
                decl.acte_depot or "0",
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("retenue.source.declaration") or "DECL"
        return super().create(vals_list)

    def action_load_records(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Rechargez les lignes uniquement en brouillon."))
        self.line_ids.unlink()
        date_from = date(self.year, int(self.month), 1)
        last = calendar.monthrange(self.year, int(self.month))[1]
        date_to = date(self.year, int(self.month), last)
        records = self.env["retenue.source.record"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("date_reglement", ">=", date_from),
                ("date_reglement", "<=", date_to),
            ]
        )
        already = self.env["retenue.source.declaration.line"].search(
            [
                ("record_id", "in", records.ids),
                ("declaration_id.state", "!=", "draft"),
                ("declaration_id", "!=", self.id),
            ]
        ).mapped("record_id")
        records = records - already
        lines = []
        for rec in records:
            lines.append(
                (
                    0,
                    0,
                    {
                        "record_id": rec.id,
                        "partner_id": rec.partner_id.id,
                        "rs_type_id": rec.rs_type_id.id,
                        "amount_base": rec.withholding_base_amount,
                        "amount_rs": rec.withholding_tax_amount,
                    },
                )
            )
        self.line_ids = lines
        return True

    def action_confirm(self):
        for decl in self:
            if decl.state != "draft":
                raise UserError(_("Seule une déclaration brouillon peut être validée."))
            if not decl.line_ids:
                raise UserError(_("Chargez au moins une ligne RAS avant de valider."))
            for line in decl.line_ids:
                if not line.record_id.certificate_number:
                    line.record_id._ensure_certificate_number()
                if not line.record_id.rs_type_id or not line.record_id.rs_type_id.tej_code:
                    raise ValidationError(
                        _("Type TEJ manquant sur %s.") % line.record_id.display_name
                    )
            decl.state = "confirmed"

    def action_set_deposited(self):
        for decl in self:
            if decl.state != "confirmed":
                raise UserError(_("Validez la déclaration avant de la marquer déposée."))
            decl.state = "deposited"

    def action_set_paid(self):
        for decl in self:
            if decl.state not in ("confirmed", "deposited"):
                raise UserError(_("Passage en payée impossible depuis cet état."))
            decl.state = "paid"

    def action_reset_draft(self):
        for decl in self:
            if decl.state == "paid":
                raise UserError(_("Une déclaration payée ne peut pas revenir en brouillon."))
            decl.state = "draft"

    def action_export_xml(self):
        self.ensure_one()
        if self.state == "draft":
            raise UserError(_("Validez la déclaration avant d'exporter le XML TEJ."))
        xml_bytes = self.env["retenue.source.tej.xml"].generate_xml(self)
        attachment = self.env["ir.attachment"].create(
            {
                "name": self.xml_filename,
                "type": "binary",
                "datas": xml_bytes,
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )
        self.xml_attachment_id = attachment.id
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    @api.model
    def _cron_deadline_reminders(self):
        """Create activities J-7 and J-1 before TEJ deadline."""
        today = fields.Date.context_today(self)
        Activity = self.env["mail.activity"]
        users = self.env.ref("account.group_account_manager").users
        if not users:
            users = self.env.ref("account.group_account_invoice").users
        for offset, summary in ((7, "Échéance TEJ J-7"), (1, "Échéance TEJ J-1")):
            target = today + timedelta(days=offset)
            decls = self.search(
                [
                    ("deadline_date", "=", target),
                    ("state", "in", ("draft", "confirmed")),
                ]
            )
            for decl in decls:
                for user in users[:3]:
                    exists = Activity.search(
                        [
                            ("res_model", "=", self._name),
                            ("res_id", "=", decl.id),
                            ("user_id", "=", user.id),
                            ("summary", "=", summary),
                        ],
                        limit=1,
                    )
                    if exists:
                        continue
                    decl.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=user.id,
                        summary=summary,
                        note=_(
                            "Déclaration RAS %(name)s — échéance TEJ le %(date)s. "
                            "Dépôt sur https://tej.finances.gov.tn"
                        )
                        % {"name": decl.name, "date": decl.deadline_date},
                    )


class RetenueSourceDeclarationLine(models.Model):
    _name = "retenue.source.declaration.line"
    _description = "Ligne déclaration RAS mensuelle"

    declaration_id = fields.Many2one(
        "retenue.source.declaration",
        required=True,
        ondelete="cascade",
    )
    record_id = fields.Many2one(
        "retenue.source.record",
        string="Document RAS",
        required=True,
        ondelete="restrict",
    )
    partner_id = fields.Many2one("res.partner", string="Partenaire", required=True)
    rs_type_id = fields.Many2one("retenue.source.type", string="Type TEJ")
    date_reglement = fields.Date(related="record_id.date_reglement", store=True)
    certificate_number = fields.Char(related="record_id.certificate_number")
    amount_base = fields.Monetary(string="Base", currency_field="currency_id")
    amount_rs = fields.Monetary(string="Montant RAS", currency_field="currency_id")
    currency_id = fields.Many2one(related="declaration_id.currency_id")

    _sql_constraints = [
        (
            "uniq_record_per_declaration",
            "unique(declaration_id, record_id)",
            "Un document RAS ne peut apparaître qu'une fois dans la déclaration.",
        ),
    ]

# -*- coding: utf-8 -*-
import base64
import logging
import os
from xml.etree import ElementTree as ET

from odoo import _, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)


class RetenueSourceTejXml(models.AbstractModel):
    _name = "retenue.source.tej.xml"
    _description = "Générateur XML TEJ DeclarationsRS"

    def _clean_matricule(self, value):
        return (value or "").replace(" ", "").upper()

    def _category_code(self, category):
        # TEJ: often PM / PP — keep simple mapping
        return "PM" if category == "pm" else "PP"

    def _add_declarant(self, parent, company):
        declarant = ET.SubElement(parent, "Declarant")
        ET.SubElement(declarant, "TypeIdentifiant").text = company.rs_tej_id_type or "1"
        ET.SubElement(declarant, "Identifiant").text = self._clean_matricule(company.vat)
        ET.SubElement(declarant, "CategorieContribuable").text = self._category_code(
            company.rs_tej_category or "pm"
        )

    def _add_reference(self, parent, declaration):
        ref = ET.SubElement(parent, "ReferenceDeclaration")
        ET.SubElement(ref, "ActeDepot").text = declaration.acte_depot or "0"
        ET.SubElement(ref, "AnneeDepot").text = str(declaration.year)
        ET.SubElement(ref, "MoisDepot").text = declaration.month

    def _add_beneficiary(self, parent, partner):
        benef = ET.SubElement(parent, "Beneficiaire")
        id_taxpayer = ET.SubElement(benef, "IdTaxpayer")
        id_type = partner.rs_tej_id_type or "1"
        if id_type == "1":
            node = ET.SubElement(id_taxpayer, "MatriculeFiscal")
            ET.SubElement(node, "TypeIdentifiant").text = "1"
            ET.SubElement(node, "Identifiant").text = self._clean_matricule(partner.vat)
            ET.SubElement(node, "CategorieContribuable").text = self._category_code(
                partner.rs_tej_category or "pm"
            )
        elif id_type == "2":
            node = ET.SubElement(id_taxpayer, "CIN")
            ET.SubElement(node, "TypeIdentifiant").text = "2"
            ET.SubElement(node, "Identifiant").text = self._clean_matricule(partner.vat or partner.ref)
            if partner.rs_tej_birth_date:
                ET.SubElement(node, "DateNaissance").text = fields_date(partner.rs_tej_birth_date)
            ET.SubElement(node, "CategorieContribuable").text = self._category_code(
                partner.rs_tej_category or "pp"
            )
        elif id_type == "3":
            node = ET.SubElement(id_taxpayer, "Passeport")
            ET.SubElement(node, "TypeIdentifiant").text = "3"
            ET.SubElement(node, "Identifiant").text = self._clean_matricule(partner.vat or partner.ref)
            if partner.rs_tej_birth_date:
                ET.SubElement(node, "DateNaissance").text = fields_date(partner.rs_tej_birth_date)
            ET.SubElement(node, "Pays").text = (partner.rs_tej_id_country_id.code or "TN")
            ET.SubElement(node, "CategorieContribuable").text = self._category_code(
                partner.rs_tej_category or "pp"
            )
        else:
            node = ET.SubElement(id_taxpayer, "AutreIdentifiantFiscal")
            ET.SubElement(node, "TypeIdentifiant").text = id_type
            ET.SubElement(node, "Identifiant").text = self._clean_matricule(partner.vat or partner.ref)
            ET.SubElement(node, "Pays").text = (partner.rs_tej_id_country_id.code or "TN")
            ET.SubElement(node, "CategorieContribuable").text = self._category_code(
                partner.rs_tej_category or "pm"
            )

        ET.SubElement(benef, "Resident").text = "true" if partner.rs_tej_resident else "false"
        ET.SubElement(benef, "NomPrenomOuRaisonSociale").text = partner.name or ""
        address_parts = [
            partner.street or "",
            partner.street2 or "",
            " ".join(x for x in [partner.zip or "", partner.city or ""] if x),
            partner.country_id.name if partner.country_id else "",
        ]
        ET.SubElement(benef, "Adresse").text = ", ".join(p for p in address_parts if p).strip()
        if partner.rs_tej_activity:
            ET.SubElement(benef, "Activite").text = partner.rs_tej_activity
        if partner.email or partner.phone or partner.mobile:
            contact = ET.SubElement(benef, "InfoContact")
            if partner.email:
                ET.SubElement(contact, "AdresseMail").text = partner.email
            if partner.phone or partner.mobile:
                ET.SubElement(contact, "NumTel").text = partner.phone or partner.mobile

    def _add_operation(self, parent, record):
        op = ET.SubElement(parent, "Operation")
        tej_code = record.rs_type_id.tej_code if record.rs_type_id else ""
        op.set("IdTypeOperation", tej_code or "")
        ET.SubElement(op, "AnneeFacturation").text = record.invoice_year or str(record.date_reglement.year)
        ET.SubElement(op, "MontantHT").text = "%.3f" % (record.amount_untaxed or 0.0)
        ET.SubElement(op, "TauxRS").text = "%.3f" % (record.tax_rate or 0.0)
        # Approximate VAT rate from amounts
        vat_rate = 0.0
        if record.amount_untaxed:
            vat_rate = (record.amount_tax or 0.0) * 100.0 / record.amount_untaxed
        ET.SubElement(op, "TauxTVA").text = "%.3f" % vat_rate
        ET.SubElement(op, "MontantTVA").text = "%.3f" % (record.amount_tax or 0.0)
        ET.SubElement(op, "MontantTTC").text = "%.3f" % (record.amount_total or 0.0)
        ET.SubElement(op, "MontantRS").text = "%.3f" % (record.withholding_tax_amount or 0.0)
        ET.SubElement(op, "MontantNetServi").text = "%.3f" % (record.amount_net_served or 0.0)
        devise = ET.SubElement(op, "Devise")
        ET.SubElement(devise, "CodeDevise").text = record.currency_id.name or "TND"
        ET.SubElement(devise, "TauxChange").text = "1"
        ET.SubElement(devise, "MontantRSDevise").text = "%.3f" % (record.withholding_tax_amount or 0.0)
        ET.SubElement(devise, "MontantTTCDevise").text = "%.3f" % (record.amount_total or 0.0)
        ET.SubElement(devise, "MontantNetServiDevise").text = "%.3f" % (record.amount_net_served or 0.0)

    def _add_certificate(self, parent, record):
        cert = ET.SubElement(parent, "Certificat")
        partner = record.partner_id.commercial_partner_id
        self._add_beneficiary(cert, partner)
        ET.SubElement(cert, "DatePayement").text = fields_date(record.date_reglement)
        ET.SubElement(cert, "Ref_certif_chez_declarant").text = record.certificate_number or record.name
        ops = ET.SubElement(cert, "ListeOperations")
        self._add_operation(ops, record)
        totals = ET.SubElement(cert, "TotalPayement")
        ET.SubElement(totals, "TotalMontantHT").text = "%.3f" % (record.amount_untaxed or 0.0)
        ET.SubElement(totals, "TotalMontantTVA").text = "%.3f" % (record.amount_tax or 0.0)
        ET.SubElement(totals, "TotalMontantTTC").text = "%.3f" % (record.amount_total or 0.0)
        ET.SubElement(totals, "TotalMontantRS").text = "%.3f" % (record.withholding_tax_amount or 0.0)
        ET.SubElement(totals, "TotalTaxes").text = "0.000"
        ET.SubElement(totals, "TotalMontantNetServi").text = "%.3f" % (record.amount_net_served or 0.0)

    def _validate_required(self, declaration):
        company = declaration.company_id
        if not self._clean_matricule(company.vat):
            raise UserError(_("Renseignez le matricule fiscal (VAT) de la société déclarante."))
        for line in declaration.line_ids:
            rec = line.record_id
            partner = rec.partner_id.commercial_partner_id
            if not self._clean_matricule(partner.vat or partner.ref):
                raise UserError(
                    _("Identifiant fiscal manquant pour le bénéficiaire %s.") % partner.display_name
                )
            if not rec.rs_type_id or not rec.rs_type_id.tej_code:
                raise UserError(_("Code TEJ manquant sur %s.") % rec.display_name)

    def _maybe_validate_xsd(self, xml_string):
        module_path = get_module_path("retenue_source_tn")
        xsd_path = os.path.join(module_path, "data", "tej", "TEJDeclarationRS_v1.0.xsd")
        if not os.path.isfile(xsd_path):
            return
        try:
            from lxml import etree
        except ImportError:
            _logger.info("lxml unavailable — skip XSD validation")
            return
        try:
            schema = etree.XMLSchema(etree.parse(xsd_path))
            doc = etree.fromstring(xml_string.encode("utf-8"))
            if not schema.validate(doc):
                raise UserError(
                    _("XML non conforme au XSD TEJ:\n%s") % schema.error_log.filter_from_errors()
                )
        except UserError:
            raise
        except Exception as exc:
            _logger.warning("XSD validation skipped: %s", exc)

    def generate_xml(self, declaration):
        self._validate_required(declaration)
        root = ET.Element("DeclarationsRS")
        root.set("VersionSchema", declaration.company_id.rs_tej_schema_version or "1.0")
        self._add_declarant(root, declaration.company_id)
        self._add_reference(root, declaration)

        # Acte 0 = Ajouter, acte 1 = Modifier (rectificatif)
        if declaration.acte_depot == "1":
            block = ET.SubElement(root, "ModifierCertificats")
        else:
            block = ET.SubElement(root, "AjouterCertificats")

        for line in declaration.line_ids:
            self._add_certificate(block, line.record_id)

        xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            root, encoding="unicode"
        )
        self._maybe_validate_xsd(xml_string)
        return base64.b64encode(xml_string.encode("utf-8"))


def fields_date(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d")

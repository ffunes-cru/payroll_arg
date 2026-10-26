"""@file
Parámetros legales de la compañía para la nómina: alícuotas de aportes y contribuciones, coeficientes,
detracción, tope imponible, ART, seguros de vida y datos del último pago de Seguridad Social (recibo).

Son valores únicos sin fecha de vigencia: al cambiarlos, los recibos que se recalculen usan el valor
nuevo (ver T8 en docs/revision.md).
"""
from odoo import fields, models, api
from odoo.exceptions import ValidationError

from .hr_contract import HOURLY_STRUCT_CODES, MONTHLY_STRUCT_CODES


class ResCompany(models.Model):
    """Compañía con CUIT y parámetros de liquidación argentina.

    @bug C12 (docs/revision.md): `art_fixed_fee` (cuota fija ART por trabajador) no la usa ninguna regla.
    @bug T7: `ss_contrib_rate` no se usa y `afip_company_type` no cambia las alícuotas (sólo se informa).
    """

    _inherit = "res.company"

    cuit = fields.Char(string="CUIT Empleador", size=11, help="11 dígitos numéricos sin guiones")
    last_ss_bank_id = fields.Many2one("res.bank", string="Banco Último Pago Seg. Social")
    last_ss_month = fields.Integer(string="Mes Último Pago Seg. Social")
    last_ss_year = fields.Integer(string="Año Último Pago Seg. Social")
    last_ss_payment_date = fields.Date(string="Fecha de Pago Último F.931")
    afip_company_type = fields.Selection(
        [
            ("1", "Tipo 1 (Art. 2 Inc. a Dec. 814/01 - Servicios / Comercio 20.4%)"),
            ("2", "Tipo 2 (Art. 2 Inc. b Dec. 814/01 - Pymes / Industria 18.0%)"),
        ],
        string="Tipo de Empresa AFIP",
        default="2",
        help="Tipo de empleador según legislación de aportes y contribuciones",
    )
    ss_contrib_rate = fields.Float(
        string="Contribuciones Seg. Social Patronal (%)",
        default=18.0,
        help="Alícuota patronal de Seguridad Social F.931 (Decreto 814/01: 18% o 20.4%).",
    )
    jubilacion_patronal_rate = fields.Float(
        string="% Jubilación Patronal SIPA",
        default=10.77,
        help="Alícuota de contribución patronal al SIPA (10.77% según Ley 27.541).",
    )
    aaff_patronal_rate = fields.Float(
        string="% Asignaciones Familiares Patronal AAFF",
        default=4.70,
        help="Alícuota de contribución patronal al régimen de Asignaciones Familiares (4.70%).",
    )
    fne_patronal_rate = fields.Float(
        string="% Fondo Nacional de Empleo FNE",
        default=0.94,
        help="Alícuota de contribución patronal al Fondo Nacional de Empleo (0.94%).",
    )
    detraccion_sipa = fields.Float(
        string="Detracción Ley 27.541 SIPA ($)",
        default=7003.68,
        help="Importe de detracción mensual de la base imponible de Seguridad Social (Art. 4 Ley 27.541).",
    )
    os_patronal_rate = fields.Float(
        string="Contribución Obra Social Patronal (%)",
        default=6.0,
        help="Contribución obligatoria del empleador al régimen de Obras Sociales (6%).",
    )
    coef_contrib_ss = fields.Float(
        string="Coef. Contrib. Seg. Social",
        default=0.10,
        digits=(16, 4),
        help="Coeficiente efectivo sobre Jubilación, Ley 19.032, AAFF y FNE patronales "
             "(1 = alícuota plena; 0.10 = 10% por régimen especial). Se propaga a lotes y recibos, donde puede modificarse.",
    )
    coef_contrib_os = fields.Float(
        string="Coef. Contrib. Obra Social",
        default=0.15,
        digits=(16, 4),
        help="Coeficiente efectivo sobre la contribución patronal de Obra Social "
             "(1 = alícuota plena; 0.15 = 15% por régimen especial). Se propaga a lotes y recibos, donde puede modificarse.",
    )
    art_variable_rate = fields.Float(
        string="Alícuota Variable ART (%)",
        default=5.82,
        help="Porcentaje variable de la Aseguradora de Riesgos del Trabajo sobre la masa salarial.",
    )
    art_fixed_fee = fields.Float(
        string="Cuota Fija ART ($)",
        default=1300.0,
        help="Cuota fija por trabajador para el Fondo Fiduciario de Enfermedades Profesionales (FFEP).",
    )
    jubilacion_contrib_rate = fields.Float(
        string="Retención Jubilación SIPA (%)",
        default=11.0,
        help="Retención al trabajador para el Sistema Integrado Previsional Argentino (11%).",
    )
    inssjp_contrib_rate = fields.Float(
        string="Retención INSSJyP Ley 19.032 (%)",
        default=3.0,
        help="Retención al trabajador para PAMI / Ley 19.032 (3%).",
    )
    os_worker_rate = fields.Float(
        string="Retención Obra Social Trabajador (%)",
        default=3.0,
        help="Retención al trabajador para su Obra Social sindical o elegida (3%).",
    )
    inssjp_patronal_rate = fields.Float(
        string="Contribución Patronal INSSJyP (%)",
        default=1.59,
        help="Contribución del empleador al INSSJyP / PAMI (1.59%).",
    )
    life_insurance_fee = fields.Float(
        string="Seguro Colectivo de Vida Obligatorio ($)",
        default=424.62,
        help="Monto fijo por trabajador del Seguro Colectivo de Vida Obligatorio (Decreto 1567/74).",
    )
    uom_life_insurance_fee = fields.Float(
        string="Seguro de Vida UOM ($)",
        default=8045.65,
        help="Cuota fija mensual patronal para el Seguro de Vida y Sepelio CCT UOM 260/75. Se liquida en la 2° Quincena o liquidaciones mensuales.",
    )
    uom_life_insurance_employee_fee = fields.Float(
        string="Seguro de Vida UOM Trabajador ($)",
        default=8045.65,
        help="Aporte fijo mensual del trabajador al Seguro de Vida y Sepelio CCT UOM 260/75. "
             "Se descuenta en la 2° Quincena o liquidaciones mensuales.",
    )
    tope_imponible_max_retencion = fields.Float(
        string="Tope Imponible Máximo Retenciones ($)",
        default=4250000.0,
        help="Base imponible máxima mensual para el cálculo de aportes del trabajador a la Seguridad Social (Art. 9 Ley 24.241).",
    )


    @api.model_create_multi
    def create(self, vals_list):
        """Crea compañías con su copia de las estructuras salariales argentinas.

        @param vals_list Lista de diccionarios de valores.
        @return Compañías creadas.
        """
        companies = super().create(vals_list)
        companies._payroll_arg_crear_estructuras()
        return companies

    def _payroll_arg_crear_estructuras(self):
        """Copia a cada compañía las estructuras argentinas que le falten (por código).

        `payroll` (OCA) exige compañía en la estructura y sólo deja elegir las de la compañía del empleado;
        las reglas salariales y sus categorías son compartidas. Se llama al crear una compañía y al
        actualizar el módulo (data/salary_structure_jornal_data.xml), para las compañías que ya existían.
        """
        Structure = self.env["hr.payroll.structure"].sudo()
        codes = HOURLY_STRUCT_CODES + MONTHLY_STRUCT_CODES
        modelo = Structure.search([("code", "in", codes)], order="id")
        for company in self:
            existentes = set(Structure.search([("code", "in", codes), ("company_id", "=", company.id)]).mapped("code"))
            for code in codes:
                origen = modelo.filtered(lambda s: s.code == code)[:1]
                if origen and code not in existentes:
                    # copy() de OCA agrega "(copy)" al código: se restablece después de copiar
                    origen.copy({"company_id": company.id}).write({"code": code, "name": origen.name})

    @api.model
    def _payroll_arg_crear_estructuras_todas(self):
        """Copia las estructuras argentinas a todas las compañías que no las tienen (lo llama la
        actualización del módulo desde data/salary_structure_jornal_data.xml)."""
        self.sudo().search([])._payroll_arg_crear_estructuras()

    @api.constrains("cuit")
    def _check_cuit(self):
        """El CUIT del empleador debe tener 11 dígitos (no valida el dígito verificador).

        @throws ValidationError CUIT con otro largo o con letras.
        """
        for company in self:
            if company.cuit:
                cuit_clean = company.cuit.replace("-", "").strip()
                if len(cuit_clean) != 11 or not cuit_clean.isdigit():
                    raise ValidationError("El CUIT de la empresa debe tener exactamente 11 dígitos numéricos.")

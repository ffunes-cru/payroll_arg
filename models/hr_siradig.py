import re
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrSiradigF572(models.Model):
    _name = "hr.siradig.f572"
    _description = "Declaración Jurada SIRADIG F.572 (AFIP / ARCA)"
    _order = "periodo_fiscal desc, fecha_presentacion desc, nro_presentacion desc, id desc"
    _rec_name = "display_name"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        index=True,
        ondelete="cascade",
        help="Empleado titular del formulario F.572 Web.",
    )
    cuit_empleado = fields.Char(
        string="CUIT / CUIL Empleado",
        required=True,
        index=True,
        help="Clave Única de Identificación Tributaria/Laboral informada en el F.572.",
    )
    periodo_fiscal = fields.Integer(
        string="Año Fiscal (Período)",
        required=True,
        default=lambda self: fields.Date.today().year,
        index=True,
        help="Año fiscal al que corresponden las deducciones declaradas (ej: 2026).",
    )
    nro_presentacion = fields.Integer(
        string="N° de Presentación (Envío)",
        default=1,
        required=True,
        help="Número correlativo de presentación en AFIP (rectificativas incrementan este número).",
    )
    fecha_presentacion = fields.Date(
        string="Fecha de Presentación en AFIP",
        default=fields.Date.today,
        help="Fecha en que el trabajador transmitió el F.572 Web a la AFIP.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Importado / Sin Aplicar"),
            ("applied", "Aplicado a la Ficha del Empleado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        help="Indica si los datos de esta declaración ya fueron trasladados a la ficha del empleado.",
    )
    date_applied = fields.Datetime(
        string="Fecha de Aplicación",
        readonly=True,
        help="Momento en que se aplicaron estas deducciones al empleado.",
    )
    xml_filename = fields.Char(string="Nombre Archivo XML", help="Nombre del archivo XML de origen.")
    xml_raw_content = fields.Text(string="XML Original (AFIP)", help="Contenido XML íntegro para auditoría o fiscalización.")

    # ── Cargas de Familia ──
    cargas_familia_ids = fields.One2many(
        "hr.siradig.carga.familia",
        "f572_id",
        string="Cargas de Familia",
        copy=True,
    )
    tiene_conyuge = fields.Boolean(
        string="Declara Cónyuge / Conviviente",
        compute="_compute_resumen_cargas",
        store=True,
        help="Indica si declara cónyuge o unión convivencial a cargo según Art. 30 inc. b.",
    )
    cant_hijos = fields.Integer(
        string="Cantidad de Hijos a Cargo",
        compute="_compute_resumen_cargas",
        store=True,
        help="Cantidad de hijos/hijastros menores de 18 años declarados a cargo.",
    )
    cant_hijos_incapacitados = fields.Integer(
        string="Hijos Incapacitados a Cargo",
        compute="_compute_resumen_cargas",
        store=True,
        help="Cantidad de hijos/hijastros con incapacidad para el trabajo a cargo.",
    )
    cargas_resumen = fields.Char(
        string="Resumen de Cargas",
        compute="_compute_resumen_cargas",
        store=True,
    )

    # ── Deducciones Generales ──
    deduccion_ids = fields.One2many(
        "hr.siradig.deduccion",
        "f572_id",
        string="Deducciones Generales",
        copy=True,
    )
    total_deducciones_anual = fields.Float(
        string="Total Deducciones Anuales ($)",
        compute="_compute_totales",
        store=True,
        help="Suma total de los montos anuales declarados en deducciones generales.",
    )
    deduccion_mensual_estimada = fields.Float(
        string="Deducción Mensual Estimada ($)",
        compute="_compute_totales",
        store=True,
        help="Promedio mensual de deducciones (Total Anual / 12 meses) a computar en cada liquidación mensual.",
    )

    # ── Pagos a Cuenta / Percepciones ──
    pago_cuenta_ids = fields.One2many(
        "hr.siradig.pago.cuenta",
        "f572_id",
        string="Pagos a Cuenta / Percepciones",
        copy=True,
    )
    total_pagos_cuenta = fields.Float(
        string="Total Pagos a Cuenta ($)",
        compute="_compute_totales",
        store=True,
        help="Percepciones computables contra el impuesto determinado.",
    )

    # ── Pluriempleo (Otros Empleadores) ──
    otro_empleador_ids = fields.One2many(
        "hr.siradig.otro.empleador",
        "f572_id",
        string="Otros Empleadores (Pluriempleo)",
        copy=True,
    )
    total_otros_empleadores_rem = fields.Float(
        string="Remuneración Bruta Otros Empleadores ($)",
        compute="_compute_totales",
        store=True,
    )

    display_name = fields.Char(string="Descripción", compute="_compute_display_name", store=True)

    @api.depends("employee_id", "periodo_fiscal", "nro_presentacion")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or rec.cuit_empleado or "Sin Empleado"
            rec.display_name = f"F.572 - {emp} ({rec.periodo_fiscal} - Envío #{rec.nro_presentacion})"

    @api.depends("cargas_familia_ids", "cargas_familia_ids.parentesco", "cargas_familia_ids.porcentaje_deduccion")
    def _compute_resumen_cargas(self):
        for rec in self:
            conyuge = False
            hijos = 0
            hijos_incap = 0
            partes = []

            for c in rec.cargas_familia_ids:
                if c.parentesco == "1":
                    conyuge = True
                elif c.parentesco == "3":
                    hijos += 1
                elif c.parentesco == "31":
                    hijos_incap += 1

            rec.tiene_conyuge = conyuge
            rec.cant_hijos = hijos
            rec.cant_hijos_incapacitados = hijos_incap

            if conyuge:
                partes.append("Cónyuge")
            if hijos > 0:
                partes.append(f"{hijos} Hijo{'s' if hijos > 1 else ''}")
            if hijos_incap > 0:
                partes.append(f"{hijos_incap} Hijo{'s' if hijos_incap > 1 else ''} Incap.")

            rec.cargas_resumen = ", ".join(partes) if partes else "Sin cargas declaradas"

    @api.depends("deduccion_ids", "deduccion_ids.monto_total", "pago_cuenta_ids", "pago_cuenta_ids.monto_total", "otro_empleador_ids", "otro_empleador_ids.ganancia_bruta")
    def _compute_totales(self):
        for rec in self:
            tot_ded = sum(d.monto_total for d in rec.deduccion_ids)
            rec.total_deducciones_anual = round(tot_ded, 2)
            rec.deduccion_mensual_estimada = round(tot_ded / 12.0, 2)
            rec.total_pagos_cuenta = round(sum(p.monto_total for p in rec.pago_cuenta_ids), 2)
            rec.total_otros_empleadores_rem = round(sum(o.ganancia_bruta for o in rec.otro_empleador_ids), 2)

    def action_apply_to_employee(self):
        """Traslada las deducciones del F.572 a los campos fiscales del empleado."""
        self.ensure_one()
        emp = self.employee_id
        if not emp:
            raise UserError("Esta declaración no está vinculada a un empleado válido.")

        emp.write({
            "ganancias_conyuge": self.tiene_conyuge,
            "ganancias_hijos": self.cant_hijos,
            "ganancias_hijos_incapacitados": self.cant_hijos_incapacitados,
            "ganancias_otras_deducciones_mensual": self.deduccion_mensual_estimada,
        })
        self.write({
            "state": "applied",
            "date_applied": fields.Datetime.now(),
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "SIRADIG F.572 Aplicado",
                "message": (
                    f"Se actualizaron las deducciones de '{emp.name}':\n"
                    f"• Cónyuge: {'Sí' if self.tiene_conyuge else 'No'}\n"
                    f"• Hijos: {self.cant_hijos} | Incapacitados: {self.cant_hijos_incapacitados}\n"
                    f"• Deducción mensual estimada: $ {self.deduccion_mensual_estimada:,.2f}"
                ),
                "type": "success",
                "sticky": False,
            },
        }


class HrSiradigCargaFamilia(models.Model):
    _name = "hr.siradig.carga.familia"
    _description = "Carga de Familia Declarada en F.572"
    _order = "parentesco, id"

    f572_id = fields.Many2one("hr.siradig.f572", string="Declaración F.572", required=True, ondelete="cascade", index=True)
    parentesco = fields.Selection(
        [
            ("1", "Cónyuge / Unión Convivencial"),
            ("3", "Hijo / Hijastro menor de 18 años"),
            ("31", "Hijo / Hijastro Incapacitado para el Trabajo"),
            ("99", "Otro Familiar"),
        ],
        string="Vínculo / Parentesco",
        required=True,
        default="3",
        help="Tipo de carga de familia reconocida por el Art. 30 inc. b de la Ley de Ganancias.",
    )
    tipo_doc = fields.Char(string="Tipo Doc", default="80", help="80 = CUIT / CUIL, 96 = DNI")
    nro_doc = fields.Char(string="N° Documento / CUIL", help="Número de documento o CUIL de la carga de familia.")
    apellido = fields.Char(string="Apellido")
    nombre = fields.Char(string="Nombre")
    nombre_completo = fields.Char(string="Nombre Completo", compute="_compute_nombre_completo", store=True)
    fecha_nac = fields.Date(string="Fecha de Nacimiento")
    mes_desde = fields.Integer(string="Mes Desde", default=1, help="Mes inicial de vigencia (1 a 12).")
    mes_hasta = fields.Integer(string="Mes Hasta", default=12, help="Mes final de vigencia (1 a 12).")
    porcentaje_deduccion = fields.Float(
        string="% Deducción Computable",
        default=100.0,
        help="100% si lo deduce íntegramente este progenitor; 50% si se comparte con el otro progenitor (RG 4003).",
    )

    @api.depends("apellido", "nombre", "nro_doc")
    def _compute_nombre_completo(self):
        for rec in self:
            ap = (rec.apellido or "").strip()
            nom = (rec.nombre or "").strip()
            full = f"{ap} {nom}".strip()
            rec.nombre_completo = full or rec.nro_doc or "Sin Nombre"


class HrSiradigDeduccion(models.Model):
    _name = "hr.siradig.deduccion"
    _description = "Deducción General Declarada en F.572"
    _order = "tipo_nombre, monto_total desc"

    f572_id = fields.Many2one("hr.siradig.f572", string="Declaración F.572", required=True, ondelete="cascade", index=True)
    tipo_codigo = fields.Char(string="Código AFIP", help="Código numérico de la deducción en el esquema F.572 de AFIP.")
    tipo_nombre = fields.Selection(
        [
            ("prepaga", "Cuotas Médico-Asistenciales (Prepagas)"),
            ("seguro_vida", "Seguros de Vida / Retiro"),
            ("donaciones", "Donaciones a Instituciones"),
            ("interes_hipotecario", "Intereses Préstamos Hipotecarios"),
            ("sepelio", "Gastos de Sepelio"),
            ("alquiler", "Alquiler Inmueble (Casa Habitación)"),
            ("servicio_domestico", "Personal de Casas Particulares (Serv. Doméstico)"),
            ("gastos_medicos", "Honorarios Médicos y Paramédicos"),
            ("gastos_educacion", "Servicios y Herramientas Educativas"),
            ("viaticos", "Gastos de Movilidad y Viáticos"),
            ("indumentaria", "Indumentaria y Equipamiento Laboral"),
            ("otro", "Otras Deducciones Generales"),
        ],
        string="Concepto de Deducción",
        default="otro",
        required=True,
    )
    descripcion = fields.Char(string="Prestador / Detalle", help="Entidad, prestador o descripción informada en el F.572.")
    cuit_prestador = fields.Char(string="CUIT Prestador / Locador", help="CUIT de la entidad receptora del pago.")
    monto_total = fields.Float(string="Monto Total Declarado ($)", required=True, default=0.0, help="Importe total anual cargado por el trabajador.")
    monto_mensual_estimado = fields.Float(string="Estimado Mensual ($)", compute="_compute_monto_mensual", store=True)
    periodo_detalle = fields.Char(string="Período / Meses", help="Meses en los que aplica esta deducción.")
    tope_legal_info = fields.Char(string="Tope Legal AFIP", compute="_compute_tope_legal")

    @api.depends("monto_total")
    def _compute_monto_mensual(self):
        for rec in self:
            rec.monto_mensual_estimado = round(rec.monto_total / 12.0, 2)

    @api.depends("tipo_nombre")
    def _compute_tope_legal(self):
        topes = {
            "prepaga": "Hasta 5% de la Ganancia Neta Anual",
            "donaciones": "Hasta 5% de la Ganancia Neta Anual",
            "interes_hipotecario": "Tope legal anual de $ 20.000 (o actualizado)",
            "sepelio": "Tope legal anual de $ 996,23",
            "alquiler": "Hasta 40% del monto pagado y hasta el MNI",
            "servicio_domestico": "Hasta el monto de Ganancia No Imponible anual",
            "gastos_educacion": "Hasta 40% de la Ganancia No Imponible anual",
            "seguro_vida": "Tope anual fijado por ley",
        }
        for rec in self:
            rec.tope_legal_info = topes.get(rec.tipo_nombre, "Sin tope específico o deducible 100%")


class HrSiradigPagoCuenta(models.Model):
    _name = "hr.siradig.pago.cuenta"
    _description = "Pago a Cuenta / Percepción Declarada en F.572"
    _order = "id"

    f572_id = fields.Many2one("hr.siradig.f572", string="Declaración F.572", required=True, ondelete="cascade", index=True)
    tipo = fields.Char(string="Régimen / Código AFIP", default="Percepción RG")
    descripcion = fields.Char(string="Concepto / Agente de Percepción")
    monto_total = fields.Float(string="Monto Computable ($)", required=True, default=0.0)


class HrSiradigOtroEmpleador(models.Model):
    _name = "hr.siradig.otro.empleador"
    _description = "Datos de Pluriempleo (Otro Empleador) F.572"
    _order = "mes, id"

    f572_id = fields.Many2one("hr.siradig.f572", string="Declaración F.572", required=True, ondelete="cascade", index=True)
    cuit = fields.Char(string="CUIT Otro Empleador")
    razon_social = fields.Char(string="Razón Social")
    mes = fields.Integer(string="Mes (1-12)", default=1)
    ganancia_bruta = fields.Float(string="Ganancia Bruta ($)", default=0.0)
    retenciones_ley = fields.Float(string="Aportes de Ley ($)", default=0.0)
    retencion_ganancias = fields.Float(string="Retención Ganancias ($)", default=0.0)

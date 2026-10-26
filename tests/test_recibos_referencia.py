from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRecibosReferencia(TransactionCase):
    """Recibos de referencia UOM, basados en recibos reales (valor hora $6.675,34, 6 años de
    antigüedad). Las bases de contribuciones se cargan a mano: son el bruto del último mes
    declarado."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        cls.env.company.write({
            "coef_contrib_ss": 0.10,
            "coef_contrib_os": 0.15,
            "detraccion_sipa": 7003.68,
            "life_insurance_fee": 424.62,
            "uom_life_insurance_fee": 8045.65,
            "uom_life_insurance_employee_fee": 8045.65,
            "tope_imponible_max_retencion": 4250000.0,
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Operario UOM",
            "cuil": "20301234563",
            "cct_id": ref("payroll_arg.afip_cct_uom").id,
            "contract_date_start": "2020-01-01",
            "date_version": "2020-01-01",
            "is_convencionado": True,
            "resource_calendar_id": ref("payroll_arg.resource_calendar_jornal_44h").id,
            "wage": 6675.34,
            "wage_type": "hourly",
            "schedule_pay": "bi-weekly",
            "struct_id": ref("payroll_arg.structure_jornal_quincenal_arg").id,
        })

    def _compute(self, tipo, date_start, date_end, inputs, contrib_base):
        run = self.env["hr.payslip.run"].create({
            "name": tipo, "tipo_liquidacion": tipo, "date_start": date_start, "date_end": date_end,
        })
        run._onchange_tipo_liquidacion()
        ctx = {"active_id": run.id, "active_model": "hr.payslip.run"}
        self.env["hr.payslip.employees"].with_context(**ctx).create(
            {"employee_ids": [(6, 0, self.employee.ids)]}
        ).compute_sheet()
        slip = run.slip_ids
        slip.prev_month_gross_manual = contrib_base
        slip._set_input_amounts(inputs)
        slip.compute_sheet()
        return slip

    def _assert_lines(self, slip, expected):
        totals = {line.code: round(abs(line.total), 2) for line in slip.line_ids if line.total}
        for code, amount in expected.items():
            self.assertAlmostEqual(totals.get(code, 0.0), amount, places=2, msg=code)

    def test_primera_quincena(self):
        slip = self._compute(
            "1° Quincena", "2026-09-01", "2026-09-15",
            {"HS_NORM": 88, "PREMIO_PROD": 502985},
            contrib_base=2251856.26,
        )
        self._assert_lines(slip, {
            "BASIC_HORAS": 587429.92,
            "ADIC_ANTIG": 35245.80,
            "PREMIO_PROD": 502985.00,
            "RET_JUB": 123822.68,
            "RET_INSSJP": 33769.82,
            "RET_OS": 33769.82,
            "RET_SIND": 28141.52,
            "COMP_ART": 131058.03,
            "COMP_JUB": 24177.06,
            "COMP_OS": 20266.71,
            "COMP_AAFF": 10583.72,
            "COMP_FNE": 2116.74,
            "COMP_INSSJP": 3569.32,
            "COMP_SCVO": 424.62,
            "COMP_UOM_VIDA": 0.0,
            "RET_UOM_VIDA": 0.0,
        })
        self.assertAlmostEqual(slip.total_remunerativo, 1125660.72, places=2)
        self.assertAlmostEqual(slip.total_retenciones, 219503.84, places=2)
        self.assertAlmostEqual(slip.neto_liquidacion, 906156.88, places=2)
        self.assertAlmostEqual(slip.total_contribuciones, 192196.21, places=2)
        self.assertAlmostEqual(slip.costo_total_empleador, 1317856.92, places=2)

    def test_segunda_quincena(self):
        slip = self._compute(
            "2° Quincena", "2026-08-16", "2026-08-31",
            {"HS_NORM": 88, "FERIADO": 9, "PRESENTISMO": 394150.85,
             "GRATIF_NO_REM": 30000, "COMPENS_NO_REM": 70000},
            contrib_base=3945490.21,
        )
        self._assert_lines(slip, {
            "BASIC_HORAS": 587429.92,
            "ADIC_ANTIG": 38850.48,
            "FERIADO": 60078.06,
            "PRESENTISMO": 394150.85,
            "GRATIF_NO_REM": 30000.00,
            "COMPENS_NO_REM": 70000.00,
            "RET_JUB": 118856.02,
            "RET_INSSJP": 32415.28,
            "RET_OS": 35415.28,
            "RET_SIND": 29512.73,
            "RET_UOM_VIDA": 8045.65,
            "COMP_ART": 229627.53,
            "COMP_JUB": 42417.50,
            "COMP_OS": 35509.41,
            "COMP_AAFF": 18543.80,
            "COMP_FNE": 3708.76,
            "COMP_INSSJP": 6262.19,
            "COMP_SCVO": 424.62,
            "COMP_UOM_VIDA": 8045.65,
        })
        self.assertAlmostEqual(slip.total_remunerativo, 1080509.31, places=2)
        self.assertAlmostEqual(slip.total_no_remunerativo, 100000.00, places=2)
        self.assertAlmostEqual(slip.total_retenciones, 224244.97, places=2)
        self.assertAlmostEqual(slip.neto_liquidacion, 956264.34, places=2)
        self.assertAlmostEqual(slip.total_contribuciones, 344539.47, places=2)
        self.assertAlmostEqual(slip.costo_total_empleador, 1525048.78, places=2)

    def test_contrib_base_from_last_viable_month(self):
        """Sin bruto manual, la base es el remunerativo del último mes con recibos."""
        june = self._compute("1° Quincena", "2026-06-01", "2026-06-15", {"HS_NORM": 88}, contrib_base=0)
        june_2 = self._compute("2° Quincena", "2026-06-16", "2026-06-30", {"HS_NORM": 80}, contrib_base=0)
        expected = june.total_remunerativo + june_2.total_remunerativo
        # julio sin recibos: agosto toma junio como último mes viable
        august = self._compute("1° Quincena", "2026-08-01", "2026-08-15", {"HS_NORM": 88}, contrib_base=0)
        art = august.line_ids.filtered(lambda l: l.code == "COMP_ART")
        self.assertAlmostEqual(art.amount, expected, places=2)

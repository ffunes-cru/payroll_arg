import base64

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNovedades(TransactionCase):
    """Las novedades viven sólo en hr.payslip.input. Los importes esperados son los del
    motor anterior para los mismos datos (14/10/2026), salvo dos correcciones posteriores:
    el aporte del trabajador al Seguro de Vida UOM y el redondeo del básico mensual."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref
        cls.company = cls.env.company
        cls.company.write({"coef_contrib_ss": 0.10, "coef_contrib_os": 0.15})
        common = {
            "company_id": cls.company.id,
            "cct_id": ref("payroll_arg.afip_cct_uom").id,
            "contract_date_start": "2024-01-01",
            "date_version": "2024-01-01",
            "is_convencionado": True,
        }
        cls.jornal = cls.env["hr.employee"].create({
            **common,
            "name": "Operario Test",
            "cuil": "20301234563",
            "legajo": 9001,
            "resource_calendar_id": ref("payroll_arg.resource_calendar_jornal_44h").id,
            "wage": 4500.0,
            "wage_type": "hourly",
            "schedule_pay": "bi-weekly",
            "struct_id": ref("payroll_arg.structure_jornal_quincenal_arg").id,
        })
        cls.jornal_2 = cls.env["hr.employee"].create({
            **common,
            "name": "Operario Test Dos",
            "cuil": "20354128919",
            "legajo": 9002,
            "resource_calendar_id": ref("payroll_arg.resource_calendar_jornal_44h").id,
            "wage": 3800.0,
            "wage_type": "hourly",
            "schedule_pay": "bi-weekly",
            "struct_id": ref("payroll_arg.structure_jornal_quincenal_arg").id,
        })
        cls.mensual = cls.env["hr.employee"].create({
            **common,
            "name": "Administrativo Test",
            "cuil": "20321234569",
            "legajo": 9003,
            "contract_date_start": "2023-01-01",
            "date_version": "2023-01-01",
            "resource_calendar_id": ref("payroll_arg.resource_calendar_mensual_40h").id,
            "wage": 1250000.0,
            "wage_type": "monthly",
            "schedule_pay": "monthly",
            "struct_id": ref("payroll_arg.structure_mensual_arg").id,
        })

    # ── helpers ──

    def _rule_input(self, code):
        return self.env["hr.rule.input"].search([("code", "=", code)], limit=1)

    def _create_run(self, tipo, date_start, date_end, employees, novelties=None):
        run = self.env["hr.payslip.run"].create({
            "name": f"Test {tipo}", "tipo_liquidacion": tipo, "date_start": date_start, "date_end": date_end,
        })
        run._onchange_tipo_liquidacion()
        for code, amount in (novelties or {}).items():
            self.env["hr.payslip.run.novelty"].create({
                "run_id": run.id, "input_id": self._rule_input(code).id, "amount": amount,
            })
        ctx = {"active_id": run.id, "active_model": "hr.payslip.run"}
        wizard = self.env["hr.payslip.employees"].with_context(**ctx).create({"employee_ids": [(6, 0, employees.ids)]})
        wizard.with_context(**ctx).compute_sheet()
        return run

    @staticmethod
    def _slip(run, employee):
        return run.slip_ids.filtered(lambda s: s.employee_id == employee)

    @staticmethod
    def _inp(slip, code):
        return slip.input_line_ids.filtered(lambda i: i.code == code).amount

    @staticmethod
    def _totals(slip):
        return {line.code: round(line.total, 2) for line in slip.line_ids}

    def _set(self, slip, code, amount):
        slip._set_input_amounts({code: amount})

    # ── tests ──

    def test_batch_generation_loads_period_and_lote_values(self):
        run = self._create_run(
            "2° Quincena", "2026-09-16", "2026-09-30", self.jornal | self.jornal_2,
            novelties={"PRESENTISMO": 30000, "PRECIO_VIANDA": 2500, "GRATIF_NO_REM": 20000, "FERIADO": 8.8},
        )
        slip = self._slip(run, self.jornal)
        self.assertEqual(slip.struct_id, self.env.ref("payroll_arg.structure_jornal_quincenal_arg"))
        self.assertEqual(self._inp(slip, "HS_NORM"), 88.0, "Horas del calendario 44 hs × 2 semanas")
        self.assertEqual(self._inp(slip, "FERIADO"), 8.8, "El valor del lote gana sobre el calendario")
        self.assertEqual(self._inp(slip, "PRESENTISMO"), 30000)
        self.assertEqual(self._inp(slip, "PRECIO_VIANDA"), 2500)
        self.assertEqual(self._inp(slip, "PREMIO_PROD"), 0.0)
        codes = slip.input_line_ids.mapped("code")
        self.assertEqual(len(codes), len(set(codes)), "Una sola línea por código")
        self.assertEqual(run.input_line_ids, (run.slip_ids.input_line_ids), "La matriz del lote ve todas las entradas")

    def test_q2_jornal_matches_previous_engine(self):
        run = self._create_run(
            "2° Quincena", "2026-09-16", "2026-09-30", self.jornal | self.jornal_2,
            novelties={"PRESENTISMO": 30000, "PRECIO_VIANDA": 2500, "GRATIF_NO_REM": 20000, "FERIADO": 8.8},
        )
        perez, rossi = self._slip(run, self.jornal), self._slip(run, self.jornal_2)
        perez._set_input_amounts({"PREMIO_PROD": 50000, "CANT_VIANDAS": 10})
        rossi._set_input_amounts({"CANT_VIANDAS": 8})
        run.action_compute_payslips()

        t = self._totals(perez)
        self.assertEqual(t["BASIC_HORAS"], 396000.0)
        self.assertEqual(t["FERIADO"], 39600.0)
        self.assertEqual(t["ADIC_ANTIG"], 8712.0)
        self.assertEqual(t["PREMIO_PROD"], 50000.0)
        self.assertEqual(t["PRESENTISMO"], 30000.0)
        self.assertEqual(t["GROSS"], 524312.0)
        self.assertEqual(t["GRATIF_NO_REM"], 20000.0)
        self.assertEqual(t["RET_JUB"], -57674.32)
        self.assertEqual(t["RET_OS"], -16329.36)
        self.assertEqual(t["RET_SIND"], -13607.8)
        self.assertEqual(t["DESC_VIANDAS"], -25000.0)
        self.assertEqual(t["RET_UOM_VIDA"], -8045.65)
        self.assertEqual(t["NET"], 407925.51)
        self.assertEqual(t["COMP_JUB"], 5571.41)
        self.assertEqual(t["COMP_OS"], 4718.81)
        self.assertEqual(t["COMP_UOM_VIDA"], 8045.65)

        t = self._totals(rossi)
        self.assertNotIn("PREMIO_PROD", t)
        self.assertEqual(t["DESC_VIANDAS"], -20000.0)
        self.assertEqual(t["NET"], 317037.77)

    def test_compute_never_touches_inputs(self):
        run = self._create_run("1° Quincena", "2026-09-01", "2026-09-15", self.jornal)
        slip = self._slip(run, self.jornal)
        self._set(slip, "HS_NORM", 80.0)
        self._set(slip, "HS_EXT50", 0.0)
        before = {i.code: i.amount for i in slip.input_line_ids}
        slip.compute_sheet()
        slip.compute_sheet()
        self.assertEqual({i.code: i.amount for i in slip.input_line_ids}, before)
        self.assertEqual(self._totals(slip)["BASIC_HORAS"], 360000.0)

    def test_q1_jornal_extras_match_previous_engine(self):
        run = self._create_run("1° Quincena", "2026-09-01", "2026-09-15", self.jornal)
        slip = self._slip(run, self.jornal)
        slip._set_input_amounts({"HS_NORM": 88.0, "HS_EXT50": 10.0, "HS_EXT100": 4.0})
        slip.compute_sheet()
        t = self._totals(slip)
        self.assertEqual(t["HS_EXT_50"], 67500.0)
        self.assertEqual(t["HS_EXT_100"], 36000.0)
        self.assertNotIn("COMP_UOM_VIDA", {c for c, v in t.items() if v}, "UOM vida no se liquida en 1° Quincena")

    def test_apply_lote_value_and_reload_period(self):
        run = self._create_run(
            "2° Quincena", "2026-09-16", "2026-09-30", self.jornal | self.jornal_2,
            novelties={"PRESENTISMO": 30000},
        )
        perez, rossi = self._slip(run, self.jornal), self._slip(run, self.jornal_2)
        self._set(rossi, "PRESENTISMO", 0.0)  # Rossi no cobra presentismo
        self._set(perez, "HS_NORM", 70.0)

        novelty = run.novelty_ids.filtered(lambda n: n.code == "PRESENTISMO")
        novelty.amount = 35000
        novelty.action_apply()
        self.assertEqual(self._inp(perez, "PRESENTISMO"), 35000)
        self.assertEqual(self._inp(rossi, "PRESENTISMO"), 35000, "Aplicar pisa el código en todo el lote")
        self.assertEqual(self._inp(perez, "HS_NORM"), 70.0, "Aplicar sólo toca su código")

        run.action_reload_period_inputs()
        self.assertEqual(self._inp(perez, "HS_NORM"), 88.0, "Recargar repone las horas del calendario")
        self.assertEqual(self._inp(perez, "PRESENTISMO"), 35000, "Recargar no pisa valores del lote")

    def test_aporte_adicional_only_q2_and_mensual(self):
        self.jornal.aporte_adicional_ss_monto = 5000
        q1 = self._create_run("1° Quincena", "2026-09-01", "2026-09-15", self.jornal)
        q2 = self._create_run("2° Quincena", "2026-09-16", "2026-09-30", self.jornal)
        self.assertEqual(self._inp(self._slip(q1, self.jornal), "APORTE_ADIC_SS"), 0.0)
        slip = self._slip(q2, self.jornal)
        self.assertEqual(self._inp(slip, "APORTE_ADIC_SS"), 5000)
        slip.compute_sheet()
        self.assertEqual(self._totals(slip)["APORTE_ADIC_SS"], -5000.0)

    def test_mensual_with_vacation_matches_previous_engine(self):
        run = self._create_run("Mensual", "2026-09-01", "2026-09-30", self.mensual)
        slip = self._slip(run, self.mensual)
        self.assertEqual(slip.struct_id, self.env.ref("payroll_arg.structure_mensual_arg"))
        self._set(slip, "VAC_DIAS", 14.0)
        slip.compute_sheet()
        t = self._totals(slip)
        self.assertEqual(t["BASIC_MENSUAL"], 666666.67)
        self.assertEqual(t["VACACIONES_MENSUAL"], 700000.0)
        self.assertEqual(t["ADIC_ANTIG"], 41000.0)

    def test_mensual_full_month_pays_exact_wage(self):
        run = self._create_run("Mensual", "2026-09-01", "2026-09-30", self.mensual)
        slip = self._slip(run, self.mensual)
        slip.compute_sheet()
        self.assertEqual(self._totals(slip)["BASIC_MENSUAL"], 1250000.0)

    def test_csv_import(self):
        run = self._create_run("1° Quincena", "2026-09-01", "2026-09-15", self.jornal | self.jornal_2)
        csv_content = "legajo;HS_NORM;horas_extras_50;PRESENTISMO\n9001;80;3,5;30000\n9002;88;;\n9999;1;1;1\n"
        wizard = self.env["hr.payslip.run.input.import"].create({
            "payslip_run_id": run.id,
            "csv_file": base64.b64encode(csv_content.encode()),
        })
        action = wizard.action_import()
        self.assertEqual(action["params"]["type"], "warning", "Legajo 9999 no está en el lote")
        perez, rossi = self._slip(run, self.jornal), self._slip(run, self.jornal_2)
        self.assertEqual(self._inp(perez, "HS_NORM"), 80.0)
        self.assertEqual(self._inp(perez, "HS_EXT50"), 3.5)
        self.assertEqual(self._inp(perez, "PRESENTISMO"), 30000)
        self.assertEqual(self._inp(rossi, "HS_NORM"), 88.0)

    def test_specialized_run_uses_specialized_structure_and_inputs(self):
        run = self._create_run("SAC", "2026-06-01", "2026-06-30", self.jornal)
        slip = self._slip(run, self.jornal)
        self.assertEqual(slip.struct_id, self.env.ref("payroll_arg.structure_sac_jornal_arg"))
        self.assertEqual(set(slip.input_line_ids.mapped("code")), {"SAC_BASE", "SAC_DIAS", "DED_SIRADIG"})

    def test_payslip_form_onchange_prefills_inputs(self):
        with Form(self.env["hr.payslip"]) as form:
            form.employee_id = self.jornal
            form.date_from = "2026-09-01"
            form.date_to = "2026-09-15"
        slip = form.record
        self.assertEqual(self._inp(slip, "HS_NORM"), 88.0)

    def test_calendar_has_only_module_attendances(self):
        cal = self.env.ref("payroll_arg.resource_calendar_jornal_44h")
        self.assertEqual(len(cal.attendance_ids), 10)
        self.assertAlmostEqual(cal.hours_per_day, 8.8, places=2)
        self.assertAlmostEqual(cal.hours_per_week, 44.0, places=2)

    def test_specialized_structures_charge_rate_contributions(self):
        run = self._create_run("SAC", "2026-06-01", "2026-06-30", self.jornal)
        slip = self._slip(run, self.jornal)
        slip._set_input_amounts({"SAC_BASE": 1000000, "SAC_DIAS": 180})
        slip.compute_sheet()
        t = self._totals(slip)
        self.assertEqual(t["SAC_JORNAL"], 500000.0)
        self.assertEqual(t["COMP_ART"], 29100.0, "SAC contribuye sobre su propio remunerativo")
        for code in ("COMP_JUB", "COMP_OS", "COMP_AAFF", "COMP_FNE", "COMP_INSSJP"):
            self.assertIn(code, t)
        self.assertNotIn("COMP_SCVO", t, "Las cuotas fijas mensuales no se repiten en el SAC")

    def test_category_change_keeps_negotiated_wage(self):
        contract = self.jornal.version_id
        other = self.env.ref("payroll_arg.afip_cat_uom_medio_oficial")
        contract.wage = 9999.0
        contract.labor_category_id = other
        self.assertEqual(contract.wage, 9999.0)

    def test_sac_jornal_estimate_uses_calendar_weekly_hours(self):
        run = self._create_run("SAC", "2026-06-01", "2026-06-30", self.jornal)
        slip = self._slip(run, self.jornal)
        slip._set_input_amounts({"SAC_DIAS": 180})
        slip.compute_sheet()
        # 4.500 $/h × 44 hs/sem × 4,333 sem/mes × 50%
        self.assertAlmostEqual(self._totals(slip)["SAC_JORNAL"], 4500 * 44 * 4.333 * 0.5, places=2)

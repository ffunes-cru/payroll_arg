"""@file
Escenarios de prueba para la guía de usuario (docs/usuario/): empleados ficticios, licencias, feriado,
F.572 e historial de Ganancias, y los ejercicios de la guía hechos por código.

Tres usos, todos con las mismas funciones:

1. **Instancia de prueba.** El administrador carga los datos maestros y el empleado hace los ejercicios a
   mano siguiendo docs/usuario/escenarios.md:

       .venv/bin/python odoo-bin shell -d <base> --no-http <<< "from odoo.addons.payroll_arg.tools.escenarios import cargar; cargar(env); env.cr.commit()"

2. **Solución.** `ejecutar(env)` hace los ejercicios (lotes, novedades, cálculo) igual que la guía. Usarlo
   en otra base para comparar, no en la que usa el empleado (duplicaría los lotes).

3. **Resultados esperados.** `escribir_resultados(env)` carga, ejecuta y escribe
   docs/usuario/resultados.md. tests/test_escenarios.py falla si ese archivo no coincide con el cálculo
   actual: un cambio de comportamiento obliga a regenerarlo y se ve en pesos en el PR.

       .venv/bin/python odoo-bin shell -d <base_de_prueba> --no-http <<< "from odoo.addons.payroll_arg.tools.escenarios import escribir_resultados; escribir_resultados(env)"

   (no hace commit: los datos se descartan al salir).

Todas las fechas son de 2026 y no dependen del día en que se corre.
"""
from datetime import date, datetime, timedelta
from pathlib import Path

from odoo.exceptions import UserError

## Módulo de los xmlid de los registros de los escenarios (no es un módulo instalable).
MODULO_XMLID = 'payroll_arg_escenarios'
## Archivo de resultados esperados generado.
ARCHIVO_RESULTADOS = Path(__file__).resolve().parent.parent / 'docs' / 'usuario' / 'resultados.md'

## Parámetros de la compañía con los que se calcularon los resultados esperados (los valores por
## defecto del módulo).
PARAMETROS_COMPANIA = {
    'coef_contrib_ss': 0.10,
    'coef_contrib_os': 0.15,
    'detraccion_sipa': 7003.68,
    'tope_imponible_max_retencion': 4250000.0,
    'jubilacion_contrib_rate': 11.0,
    'inssjp_contrib_rate': 3.0,
    'os_worker_rate': 3.0,
    'jubilacion_patronal_rate': 10.77,
    'inssjp_patronal_rate': 1.59,
    'aaff_patronal_rate': 4.70,
    'fne_patronal_rate': 0.94,
    'os_patronal_rate': 6.0,
    'art_variable_rate': 5.82,
    'life_insurance_fee': 424.62,
    'uom_life_insurance_fee': 8045.65,
    'uom_life_insurance_employee_fee': 8045.65,
}

## Calendarios del módulo que usan los escenarios; se les fija la zona horaria de Córdoba (ver C24 en
## docs/revision.md: sin zona horaria, un feriado cuenta dos días).
CALENDARIOS = ('payroll_arg.resource_calendar_jornal_44h', 'payroll_arg.resource_calendar_mensual_40h')
## Zona horaria de la planta.
ZONA_HORARIA = 'America/Argentina/Cordoba'

## Empleados ficticios: clave → valores de `hr.employee` (más `categoria` y `jornal` para resolver
## xmlids). Los CUIL son ficticios con dígito verificador válido.
EMPLEADOS = {
    'a': dict(name='Prueba A - Juan Pérez', legajo=9101, cuil='20301112220', jornal=True, wage=6675.34,
              categoria='afip_cat_uom_oficial', ingreso='2020-03-01'),
    'b': dict(name='Prueba B - Lucas Gómez', legajo=9102, cuil='20402223333', jornal=True, wage=4900.0,
              categoria='afip_cat_uom_medio_oficial', ingreso='2024-05-02'),
    'c': dict(name='Prueba C - Martín Sosa', legajo=9103, cuil='20384445552', jornal=True, wage=4500.0,
              categoria='afip_cat_uom_operario', ingreso='2023-02-01'),
    'd': dict(name='Prueba D - Carla Díaz', legajo=9104, cuil='27335556661', jornal=False, wage=1250000.0,
              categoria='afip_cat_uom_admin_2', ingreso='2015-04-01'),
    'e': dict(name='Prueba E - Roberto Fernández', legajo=9105, cuil='20256667771', jornal=False, wage=6500000.0,
              categoria=False, ingreso='2012-06-01', convencionado=False, conyuge=True, hijos=2),
    'f': dict(name='Prueba F - Diego Molina', legajo=9106, cuil='20357778884', jornal=True, wage=4500.0,
              categoria='afip_cat_uom_operario', ingreso='2021-02-01', egreso='2026-09-15'),
}

## Bruto remunerativo de julio de 2026 (del "sistema anterior"): base de contribuciones de las
## quincenas de agosto de los jornalizados (campo *Bruto Mes Anterior Manual*).
BRUTO_JULIO = {'a': 3945490.21, 'b': 1020000.0, 'c': 930000.0, 'f': 880000.0}

## Vacaciones aprobadas: clave del empleado → (desde, hasta).
VACACIONES = {'c': ('2026-09-07', '2026-09-20'), 'd': ('2026-09-21', '2026-09-25')}

## Feriados del período de los escenarios: fecha → nombre.
FERIADOS = {'2026-08-17': 'Paso a la Inmortalidad del Gral. San Martín'}

## Sueldo mensual de E de enero a julio (historial de Ganancias del sistema anterior).
HISTORIAL_GANANCIAS_E = 6500000.0


def _ref(env, nombre):
    """Registro de un escenario por su nombre corto (xmlid `payroll_arg_escenarios.<nombre>`).

    @param env Entorno de Odoo.
    @param nombre Nombre corto, p. ej. 'emp_a'.
    @return Registro, o None si no existe.
    """
    return env.ref(f'{MODULO_XMLID}.{nombre}', raise_if_not_found=False)


def _registrar(env, nombre, registro):
    """Le pone un xmlid de escenario a un registro (para encontrarlo y para no cargar dos veces).

    @param env Entorno de Odoo.
    @param nombre Nombre corto.
    @param registro Registro.
    """
    env['ir.model.data']._update_xmlids([
        {'xml_id': f'{MODULO_XMLID}.{nombre}', 'record': registro, 'noupdate': True}])


def _empleado(env, clave):
    """Empleado de un escenario.

    @param env Entorno de Odoo.
    @param clave Clave del empleado ('a' a 'f').
    @return hr.employee.
    """
    return _ref(env, f'emp_{clave}')


# =============================================================================
#  Datos maestros
# =============================================================================

def cargar(env):
    """Carga los datos maestros de los escenarios: parámetros de la compañía, zona horaria de los
    calendarios, feriado, empleados con su contrato, vacaciones aprobadas, F.572 de E e historial de
    Ganancias de E (enero a julio).

    @param env Entorno de Odoo (el llamador hace el commit).
    @throws UserError Si los escenarios ya están cargados.
    """
    if _empleado(env, 'a'):
        raise UserError('Los escenarios de prueba ya están cargados en esta base.')
    env.company.write(PARAMETROS_COMPANIA)
    for calendario in CALENDARIOS:
        env.ref(calendario).tz = ZONA_HORARIA
    calendario_jornal = env.ref('payroll_arg.resource_calendar_jornal_44h')
    for dia, nombre in FERIADOS.items():
        fecha = date.fromisoformat(dia)
        # 00:00 a 23:59 hora de Córdoba (UTC-3). Se escriben después de crear porque `create` corre las
        # fechas de la zona horaria del usuario a la del calendario.
        desde = datetime(fecha.year, fecha.month, fecha.day, 3, 0, 0)
        feriado = env['resource.calendar.leaves'].create({
            'name': nombre, 'calendar_id': calendario_jornal.id, 'date_from': desde, 'date_to': desde + timedelta(hours=1),
        })
        feriado.write({'date_from': desde, 'date_to': desde + timedelta(hours=23, minutes=59, seconds=59)})
        _registrar(env, f'feriado_{dia}', feriado)
    for clave in EMPLEADOS:
        _registrar(env, f'emp_{clave}', _crear_empleado(env, EMPLEADOS[clave]))
    tipo_vacaciones = env.ref('payroll_arg.holiday_status_vacaciones_lct')
    for clave, (desde, hasta) in VACACIONES.items():
        licencia = env['hr.leave'].with_context(leave_skip_state_check=True, mail_create_nolog=True).create({
            'employee_id': _empleado(env, clave).id,
            'holiday_status_id': tipo_vacaciones.id,
            'request_date_from': desde,
            'request_date_to': hasta,
        })
        if licencia.state != 'validate':
            licencia.action_approve()
        if licencia.state != 'validate':
            licencia.action_validate()
        _registrar(env, f'vacaciones_{clave}', licencia)
    _cargar_siradig_e(env)
    _cargar_historial_ganancias_e(env)


def _crear_empleado(env, datos):
    """Crea un empleado ficticio con su contrato (versión) argentino.

    @param env Entorno de Odoo.
    @param datos Diccionario de `EMPLEADOS`.
    @return hr.employee.
    """
    ref = env.ref
    jornal = datos['jornal']
    convencionado = datos.get('convencionado', True)
    valores = {
        'name': datos['name'],
        'legajo': datos['legajo'],
        'cuil': datos['cuil'],
        'cbu': f"0110{datos['legajo']:04d}30000000000000"[:22],
        'payment_type': '3',
        'health_insurance_id': ref('payroll_arg.afip_os_osuomra' if convencionado else 'payroll_arg.afip_os_osde').id,
        'contract_date_start': datos['ingreso'],
        'date_version': datos['ingreso'],
        'wage_type': 'hourly' if jornal else 'monthly',
        'schedule_pay': 'bi-weekly' if jornal else 'monthly',
        'struct_id': ref('payroll_arg.structure_jornal_quincenal_arg' if jornal else 'payroll_arg.structure_mensual_arg').id,
        'resource_calendar_id': ref('payroll_arg.resource_calendar_jornal_44h' if jornal else 'payroll_arg.resource_calendar_mensual_40h').id,
        'tz': 'America/Argentina/Cordoba',
        'is_convencionado': convencionado,
        'cct_id': ref('payroll_arg.afip_cct_uom').id if convencionado else False,
        'labor_category_id': ref(f"payroll_arg.{datos['categoria']}").id if datos['categoria'] else False,
        'wage': datos['wage'],
        'afip_contract_type_id': ref('payroll_arg.afip_contract_type_001').id,
        'afip_situation_id': ref('payroll_arg.afip_situation_01').id,
        'afip_condition_id': ref('payroll_arg.afip_condition_01').id,
        'afip_activity_id': ref('payroll_arg.afip_activity_001').id,
        'afip_zone_id': ref('payroll_arg.afip_zone_18').id,
        'afip_siniestrado_id': ref('payroll_arg.afip_siniestrado_00').id,
        'ganancias_conyuge': datos.get('conyuge', False),
        'ganancias_hijos': datos.get('hijos', 0),
    }
    if datos.get('egreso'):
        valores['contract_date_end'] = datos['egreso']
    return env['hr.employee'].create(valores)


def _cargar_siradig_e(env):
    """F.572 de E: cónyuge, dos hijos, prepaga y alquiler (1.800.000 anuales = 150.000 por mes). Se
    aplica a la ficha, como haría el asistente de importación.

    @param env Entorno de Odoo.
    """
    empleado = _empleado(env, 'e')
    f572 = env['hr.siradig.f572'].create({
        'employee_id': empleado.id,
        'cuit_empleado': empleado.cuil,
        'periodo_fiscal': 2026,
        'nro_presentacion': 1,
        'fecha_presentacion': '2026-03-10',
        'cargas_familia_ids': [
            (0, 0, {'parentesco': '1', 'apellido': 'Fernández', 'nombre': 'Laura'}),
            (0, 0, {'parentesco': '3', 'apellido': 'Fernández', 'nombre': 'Tomás'}),
            (0, 0, {'parentesco': '3', 'apellido': 'Fernández', 'nombre': 'Sofía'}),
        ],
        'deduccion_ids': [
            (0, 0, {'tipo_nombre': 'prepaga', 'descripcion': 'Prepaga', 'monto_total': 1200000.0}),
            (0, 0, {'tipo_nombre': 'alquiler', 'descripcion': 'Alquiler de vivienda', 'monto_total': 600000.0}),
        ],
    })
    f572.action_apply_to_employee()
    _registrar(env, 'f572_e', f572)


def _cargar_historial_ganancias_e(env):
    """Acumuladores de Ganancias de E de enero a julio de 2026, como si vinieran del sistema anterior
    (al empezar a liquidar con Odoo a mitad de año hay que cargarlos). Se calculan con la misma fórmula
    que `hr.payslip._calculate_ganancias_from_rules()`.

    Aportes por mes: 11% + 3% + 3% sobre el tope (4.250.000) = 722.500. SIRADIG: 150.000.

    @param env Entorno de Odoo.
    """
    empleado = _empleado(env, 'e')
    tope = PARAMETROS_COMPANIA['tope_imponible_max_retencion']
    aportes = round(tope * 0.17, 2)
    siradig = empleado.ganancias_otras_deducciones_mensual
    acumulado_bruto = acumulado_deducciones = retenido = 0.0
    for mes in range(1, 8):
        escala = env['hr.ganancias.scale'].get_scale_for_date(date(2026, mes, 28), empleado.company_id)
        acumulado_bruto += HISTORIAL_GANANCIAS_E
        acumulado_deducciones += aportes + siradig
        personales = (escala.deduccion_ganancia_no_imponible + escala.deduccion_especial + escala.deduccion_conyuge
                      + escala.deduccion_hijo * empleado.ganancias_hijos) * mes / 12.0
        neta = max(0.0, acumulado_bruto - acumulado_deducciones - personales)
        impuesto = escala.calculate_annual_bracket(neta, mes)
        retencion = max(0.0, round(impuesto - retenido, 2))
        acumulador = env['hr.ganancias.accumulator'].create({
            'employee_id': empleado.id, 'year': 2026, 'month': mes,
            'gross_rem': HISTORIAL_GANANCIAS_E, 'deductions_employee': aportes, 'other_deductions': siradig,
            'accumulated_gross': acumulado_bruto, 'accumulated_deductions': acumulado_deducciones,
            'personal_deductions': personales, 'accumulated_net_taxable': neta, 'accumulated_tax': impuesto,
            'accumulated_retained': retenido, 'retention_calculated': retencion, 'retention_applied': retencion,
            'notes': 'Historial del sistema anterior (escenario de prueba).',
        })
        _registrar(env, f'ganancias_e_{mes:02d}', acumulador)
        retenido += retencion


# =============================================================================
#  Ejercicios de la guía
# =============================================================================

def _lote(env, nombre, tipo, desde, hasta, pago, claves, valores_lote=None):
    """Crea un lote, fija sus valores de lote y genera los recibos de los empleados indicados (pasos 1 a
    3 de cada ejercicio de la guía).

    @param env Entorno de Odoo.
    @param nombre Nombre del lote.
    @param tipo Tipo de liquidación.
    @param desde Inicio del período (AAAA-MM-DD).
    @param hasta Fin del período.
    @param pago Fecha de pago.
    @param claves Claves de los empleados.
    @param valores_lote dict {código: valor} de *Valores del Lote*.
    @return hr.payslip.run.
    """
    lote = env['hr.payslip.run'].create({
        'name': nombre, 'tipo_liquidacion': tipo, 'date_start': desde, 'date_end': hasta,
    })
    lote._onchange_tipo_liquidacion()
    lote.payment_date = pago
    for codigo, valor in (valores_lote or {}).items():
        entrada = env['hr.rule.input'].search([('code', '=', codigo)], limit=1)
        env['hr.payslip.run.novelty'].create({'run_id': lote.id, 'input_id': entrada.id, 'amount': valor})
    empleados = env['hr.employee'].browse([_empleado(env, clave).id for clave in claves])
    contexto = {'active_id': lote.id, 'active_model': 'hr.payslip.run'}
    env['hr.payslip.employees'].with_context(**contexto).create(
        {'employee_ids': [(6, 0, empleados.ids)]}).compute_sheet()
    return lote


def _recibo(lote, clave):
    """Recibo de un empleado de escenario en un lote.

    @param lote hr.payslip.run.
    @param clave Clave del empleado.
    @return hr.payslip.
    """
    empleado = _empleado(lote.env, clave)
    return lote.slip_ids.filtered(lambda s: s.employee_id == empleado)


def _novedades(lote, por_empleado):
    """Carga novedades por empleado (la matriz del lote) y campos del recibo.

    @param lote hr.payslip.run.
    @param por_empleado dict {clave: {código o campo del recibo: valor}}; los campos del recibo se
           reconocen porque existen en `hr.payslip`.
    """
    for clave, valores in por_empleado.items():
        recibo = _recibo(lote, clave)
        campos = {k: v for k, v in valores.items() if k in recibo._fields}
        recibo.write(campos)
        recibo._set_input_amounts({k: v for k, v in valores.items() if k not in campos})


def _bruto_mes(env, clave, desde, hasta):
    """Remunerativo de un empleado en los recibos de escenario de un período (para la base del SAC y de
    las indemnizaciones, que la guía calcula a mano).

    @param env Entorno de Odoo.
    @param clave Clave del empleado.
    @param desde Primer día.
    @param hasta Último día.
    @return Importe en pesos.
    """
    recibos = env['hr.payslip'].search([
        ('employee_id', '=', _empleado(env, clave).id), ('date_from', '>=', desde), ('date_to', '<=', hasta),
        ('state', 'in', ('verify', 'done'))])
    return round(sum(recibos.mapped('total_remunerativo')), 2)


def ejecutar(env):
    """Hace los ocho ejercicios de docs/usuario/escenarios.md, en orden, y calcula todos los lotes.

    @param env Entorno de Odoo con los datos maestros cargados (`cargar()`).
    @return Lista de (número de ejercicio, lote).
    """
    lotes = []

    # 1. 1° Quincena de agosto: jornalizados, viandas, base de contribuciones de julio a mano.
    q1_ago = _lote(env, 'Prueba - 1° Quincena Agosto 2026', '1° Quincena', '2026-08-01', '2026-08-15',
                   '2026-08-19', 'abcf', {'PRECIO_VIANDA': 2500.0})
    _novedades(q1_ago, {
        'a': {'PREMIO_PROD': 548671.23},
        'b': {'CANT_VIANDAS': 10},
        'c': {'CANT_VIANDAS': 8},
        'f': {'CANT_VIANDAS': 9},
    })
    _novedades(q1_ago, {clave: {'prev_month_gross_manual': bruto} for clave, bruto in BRUTO_JULIO.items()})
    lotes.append((1, q1_ago))

    # 2. 2° Quincena de agosto: feriado del 17, presentismo, extras, no remunerativos.
    q2_ago = _lote(env, 'Prueba - 2° Quincena Agosto 2026', '2° Quincena', '2026-08-16', '2026-08-31',
                   '2026-09-04', 'abcf', {'PRECIO_VIANDA': 2500.0, 'PRESENTISMO': 120000.0})
    _novedades(q2_ago, {
        'a': {'FERIADO': 9, 'PRESENTISMO': 394150.85, 'GRATIF_NO_REM': 30000.0, 'COMPENS_NO_REM': 70000.0},
        'b': {'HS_EXT50': 10, 'HS_EXT100': 4, 'CANT_VIANDAS': 11},
        'c': {'CANT_VIANDAS': 9},
        'f': {'CANT_VIANDAS': 10},
    })
    _novedades(q2_ago, {clave: {'prev_month_gross_manual': bruto} for clave, bruto in BRUTO_JULIO.items()})
    lotes.append((2, q2_ago))

    # 3. Mensual de agosto: mensualizados; E con tope y Ganancias.
    lotes.append((3, _lote(env, 'Prueba - Mensual Agosto 2026', 'Mensual', '2026-08-01', '2026-08-31',
                           '2026-09-04', 'de')))

    # 4. Vacaciones de C, pagadas al salir.
    lotes.append((4, _lote(env, 'Prueba - Vacaciones Septiembre 2026', 'Vacaciones', '2026-09-07',
                           '2026-09-20', '2026-09-04', 'c')))

    # 5. 1° Quincena de septiembre: base de contribuciones tomada de agosto; C de vacaciones.
    q1_sep = _lote(env, 'Prueba - 1° Quincena Septiembre 2026', '1° Quincena', '2026-09-01', '2026-09-15',
                   '2026-09-18', 'abc')
    _novedades(q1_sep, {'a': {'PREMIO_PROD': 502985.0}})
    lotes.append((5, q1_sep))

    # 6. Mensual de septiembre: D con 5 días de vacaciones dentro del mes.
    lotes.append((6, _lote(env, 'Prueba - Mensual Septiembre 2026', 'Mensual', '2026-09-01', '2026-09-30',
                           '2026-10-05', 'de')))

    # 7. Liquidación final de F (despido sin causa el 15/09).
    for _numero, lote in lotes:
        lote.slip_ids.compute_sheet()
    base_f = max(BRUTO_JULIO['f'], _bruto_mes(env, 'f', date(2026, 8, 1), date(2026, 8, 31)))
    final = _lote(env, 'Prueba - Liquidación Final Diego Molina', 'Liquidación Final', '2026-09-01',
                  '2026-09-15', '2026-09-18', 'f')
    _novedades(final, {'f': {
        'VAC_NO_GOZ': 15,
        'SAC_BASE': base_f,
        'SAC_DIAS': 77,
        'INDEM_ANTIG': round(base_f * 6, 2),
        'INDEM_PREAV': round(base_f * 2, 2),
        'INTEG_MES': round(base_f / 30 * 15, 2),
    }})
    lotes.append((7, final))

    # 8. SAC del segundo semestre (mejor mes del semestre en el sistema: agosto).
    sac = _lote(env, 'Prueba - SAC 2° Semestre 2026', 'SAC', '2026-07-01', '2026-12-31', '2026-12-18', 'abcd')
    _novedades(sac, {clave: {'SAC_BASE': _bruto_mes(env, clave, date(2026, 8, 1), date(2026, 8, 31))}
                     for clave in 'abcd'})
    lotes.append((8, sac))

    for _numero, lote in lotes:
        lote.slip_ids.compute_sheet()
    return lotes


# =============================================================================
#  Resultados esperados
# =============================================================================

def _pesos(importe):
    """Importe con formato argentino: 1234567.8 → '1.234.567,80'.

    @param importe Número.
    @return Texto.
    """
    return f'{importe:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def _cantidad(valor):
    """Cantidad con formato argentino sin ceros de más: 88.0 → '88', 8.8 → '8,8'.

    @param valor Número.
    @return Texto.
    """
    texto = f'{valor:,.4f}'.rstrip('0').rstrip('.')
    return texto.replace(',', '_').replace('.', ',').replace('_', '.')


def generar_resultados(env, lotes):
    """Markdown con el resultado de cada recibo de los ejercicios: novedades, líneas y totales.

    @param env Entorno de Odoo.
    @param lotes Lista de (número de ejercicio, lote) de `ejecutar()`.
    @return Texto Markdown.
    """
    partes = [
        '# Resultados esperados de los escenarios',
        '> Archivo generado por `tools/escenarios.py` (`escribir_resultados`): no editar a mano. '
        'Son los importes que calcula el módulo hoy, incluidos los problemas conocidos que la '
        '[guía](escenarios.md) señala en cada ejercicio. Cuando un arreglo cambia un importe, este '
        'archivo cambia en el mismo PR.',
        'Línea: *Cant.* = horas, días, unidades o coeficiente; *Base* = valor unitario (valor hora, '
        'base imponible, monto); *Importe* = lo que suma o resta en el recibo.',
    ]
    for numero, lote in lotes:
        partes.append(f'## Ejercicio {numero}: {lote.name}')
        partes.append(f'Tipo {lote.tipo_liquidacion}, del {lote.date_start:%d/%m/%Y} al '
                      f'{lote.date_end:%d/%m/%Y}, pago {lote.payment_date:%d/%m/%Y}.')
        for recibo in lote.slip_ids.sorted(lambda s: s.employee_id.legajo):
            partes.append(_tabla_recibo(recibo))
    partes.append('## Acumuladores de Ganancias de E')
    partes.append(_tabla_ganancias(env))
    return '\n\n'.join(partes) + '\n'


def _tabla_recibo(recibo):
    """Sección Markdown de un recibo: novedades distintas de 0, líneas con importe y totales.

    @param recibo hr.payslip calculado.
    @return Texto Markdown.
    """
    novedades = ', '.join(f'`{i.code}` {_cantidad(i.amount)}'
                          for i in recibo.input_line_ids.sorted('code') if i.amount)
    filas = [f'| `{l.code}` | {l.name} | {_cantidad(l.quantity)} | {_pesos(abs(l.amount))} '
             f'| {_cantidad(l.rate)} | {_pesos(l.total)} |'
             for l in recibo.line_ids.sorted(lambda l: (l.sequence, l.code)) if l.total]
    return '\n'.join([
        f'### {recibo.employee_id.name} (legajo {recibo.employee_id.legajo})', '',
        f'Novedades: {novedades or "ninguna"}.', '',
        '| Código | Concepto | Cant. | Base | % | Importe |', '|---|---|---|---|---|---|', *filas, '',
        f'**Remunerativo** {_pesos(recibo.total_remunerativo)} · **No remunerativo** '
        f'{_pesos(recibo.total_no_remunerativo)} · **Retenciones** {_pesos(recibo.total_retenciones)} · '
        f'**Neto** {_pesos(recibo.neto_liquidacion)} · **Contribuciones** {_pesos(recibo.total_contribuciones)} · '
        f'**Costo** {_pesos(recibo.costo_total_empleador)}',
    ])


def _tabla_ganancias(env):
    """Tabla de los acumuladores de Ganancias de E al final de los ejercicios.

    @param env Entorno de Odoo.
    @return Tabla Markdown.
    """
    acumuladores = env['hr.ganancias.accumulator'].search(
        [('employee_id', '=', _empleado(env, 'e').id)]).sorted(lambda a: (a.year, a.month))
    filas = [f'| {a.month:02d}/{a.year} | {_pesos(a.gross_rem)} | {_pesos(a.deductions_employee)} '
             f'| {_pesos(a.other_deductions)} | {_pesos(a.accumulated_net_taxable)} | {_pesos(a.accumulated_tax)} '
             f'| {_pesos(a.retention_applied)} |' for a in acumuladores]
    return '\n'.join(['| Mes | Bruto | Aportes | SIRADIG | Ganancia neta acum. | Impuesto acum. | Retención |',
                      '|---|---|---|---|---|---|---|', *filas])


def escribir_resultados(env):
    """Carga los escenarios, hace los ejercicios y escribe docs/usuario/resultados.md. No hace commit.

    @param env Entorno de Odoo de una base de prueba.
    @return Path del archivo escrito.
    """
    cargar(env)
    ARCHIVO_RESULTADOS.write_text(generar_resultados(env, ejecutar(env)), encoding='utf-8')
    return ARCHIVO_RESULTADOS

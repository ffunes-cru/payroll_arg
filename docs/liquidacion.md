# Liquidación: cómo se calcula cada concepto

Qué hace cada regla salarial, de dónde salen sus datos y en qué norma se apoya. El código exacto de cada
regla está en la [referencia generada](referencia.md#reglas-salariales); los problemas conocidos, con su
id (C1, C2…), en la [revisión](revision.md).

## Cómo se evalúa un recibo

1. Las reglas de la estructura se ejecutan en orden de **secuencia**. Cada una devuelve
   `result × result_qty × result_rate / 100`.
2. `categories.REM`, `categories.NOREM`, `categories.DED` suman lo calculado **hasta esa regla**: el
   orden importa (p. ej. la antigüedad, secuencia 20, no ve las vacaciones jornal, secuencia 40).
3. Las reglas leen las novedades con `inp('CÓDIGO')` y los parámetros con `payroll.<clave>`:

| Parámetro | Valor | Fuente |
|---|---|---|
| `payroll.tope` | Tope imponible del recibo; la mitad en quincenas | `hr.payslip._get_tope_imponible()` |
| `payroll.prev_gross` | Remunerativo del último mes con recibos (sólo quincenas) | `hr.payslip._get_prev_month_gross()` |
| `payroll.coef_ss`, `payroll.coef_os` | Coeficientes de contribución del lote (o de la compañía) | `hr.payslip._get_contrib_coefs()` |
| `payroll.detraccion_sipa` | Detracción mensual | compañía |
| `payroll.is_q1`, `payroll.is_q2` | Tipo de quincena | lote |

4. Los totales (`total_remunerativo`, `total_no_remunerativo`, `total_retenciones`,
   `total_contribuciones`, neto y costo) se arman por **tipo de concepto AFIP** de la regla, no por
   categoría (`hr.payslip._compute_totals_arg()`).

## Haberes de jornalizados (`JORNAL_QUINC_ARG`)

| Regla | Fórmula | Novedad | Norma / origen |
|---|---|---|---|
| `BASIC_HORAS` | horas × valor hora | `HS_NORM` (calendario: 88 por quincena; o fichadas) | Contrato por hora. Ver C13, C15. |
| `FERIADO` | horas × valor hora | `FERIADO` (feriados en días laborables × horas por día) | Art. 166 LCT. Ver C14. |
| `ADIC_ANTIG` | 1% × años × (normales + feriado + extras 50% × 1,5 + extras 100% × 2) × valor hora | `antiguedad_anios` del recibo | CCT UOM 260/75. Premios y presentismo afuera (confirmado). Ver C16. |
| `HS_EXT_50` | horas × valor hora × 1,5 | `HS_EXT50` | Art. 201 LCT (días hábiles). |
| `HS_EXT_100` | horas × valor hora × 2 | `HS_EXT100` | Art. 201 LCT (sábado desde las 13, domingo, feriado). |
| `OBJETIVOS`, `PREMIO_PROD`, `PRESENTISMO`, `PORTITULO` | importe | misma | Remunerativos de empresa o convenio. Ver E2. |
| `VACACIONES` | días × valor hora × horas por día × 1,20 | `VAC_DIAS` (licencias aprobadas) | Art. 155 LCT. Ver C1, C16, C17. |

## Haberes de mensualizados (`MENSUAL_ARG`)

| Regla | Fórmula | Novedad | Norma / origen |
|---|---|---|---|
| `BASIC_MENSUAL` | (30 − días de vacaciones) × sueldo / 30 | `VAC_DIAS` | Mes comercial de 30 días. Valor día con 4 decimales. |
| `VACACIONES_MENSUAL` | días × sueldo / divisor del CCT (25) | `VAC_DIAS` | Art. 155 inc. a LCT. Ver C1, C16. |
| `ADIC_ANTIG` | 1% × años × remunerativo calculado hasta acá (básico + vacaciones) | — | CCT. |

## No remunerativos (las dos estructuras)

`ASIG_NO_REM`, `GRATIF_NO_REM`, `COMPENS_NO_REM`: el importe de la novedad. No pagan jubilación ni
INSSJP ni contribuciones de Seguridad Social. Sí pagan aporte de Obra Social y cuota sindical
(confirmado). La contribución de Obra Social no los incluye hoy (C8). Están gravados en Ganancias y hoy
no se gravan (C3).

## Retenciones al trabajador

| Regla | Base | Alícuota | Cuándo |
|---|---|---|---|
| `RET_JUB` | remunerativo con tope | 11% (compañía) | siempre |
| `RET_INSSJP` | remunerativo con tope | 3% | siempre |
| `RET_OS` | remunerativo con tope + no remunerativo | 3% | siempre (ver C7 en liquidación final) |
| `RET_SIND` | remunerativo + no remunerativo | alícuota del CCT (UOM 2,5%) | convencionados (ver C19) |
| `RET_GANANCIAS` | método acumulativo (abajo) | escala Art. 94 LIG | siempre; 0 si no alcanza |
| `RET_UOM_VIDA` | cuota fija mensual | — | UOM, salvo 1° Quincena (ver C18) |
| `APORTE_ADIC_SS` | monto fijo de la ficha | — | 2° Quincena y Mensual |
| `DESC_VIANDAS` | cantidad × precio | — | si hay viandas |

**Tope.** `payroll.tope` es el de la compañía, o la mitad en quincenas: cada quincena se topea por
separado (decisión confirmada). Se puede pisar por recibo con *Tope Imponible Retenciones*.
`base_imponible_seg_social` e `is_tope_applied` muestran si se aplicó.

## Contribuciones del empleador

**Base.**
- Jornalizados en quincena: el remunerativo de **todas** las liquidaciones del último mes con recibos
  en espera o hechos. Es el cuadro "Costo Total Empleado" de los recibos de referencia, que repite el último
  mes declarado. Se puede fijar a mano con *Bruto Mes Anterior Manual*.
- El resto (mensualizados y lotes de SAC, vacaciones y final): el remunerativo del propio recibo.

| Regla | Fórmula |
|---|---|
| `COMP_ART` | base × alícuota ART variable (falta la cuota fija, C12) |
| `COMP_JUB` | (base − detracción) × 10,77% × coef. SS |
| `COMP_INSSJP` | (base − detracción) × 1,59% × coef. SS |
| `COMP_AAFF` | base × 4,70% × coef. SS (sin detracción, C11) |
| `COMP_FNE` | base × 0,94% × coef. SS (sin detracción, C11) |
| `COMP_OS` | base × 6% × coef. OS (sin no remunerativo, C8) |
| `COMP_SCVO` | prima fija del Seguro Colectivo de Vida Obligatorio |
| `COMP_UOM_VIDA` | cuota fija UOM, salvo 1° Quincena |

Las dos quincenas calculan las contribuciones del mes completo (C20).

## Ganancias (4ta categoría)

`hr.payslip._calculate_ganancias_from_rules()`, llamado por la regla `RET_GANANCIAS`:

```
bruto acumulado      = brutos de los meses anteriores del año + remunerativo de este recibo
deducciones          = aportes acumulados (categoría DED hasta la regla) + SIRADIG del mes y anteriores
deducciones Art. 30  = (no imponible + especial + cónyuge + hijos × importe + hijos incap. × importe) × mes / 12
ganancia neta        = bruto − deducciones − deducciones Art. 30   (mínimo 0)
impuesto acumulado   = escala Art. 94 con tramos y cuota fija × mes / 12
retención del mes    = impuesto acumulado − retenciones de los meses anteriores   (mínimo 0)
```

El resultado se guarda en `hr.ganancias.accumulator` (uno por empleado y mes). Con *Override Retención
Ganancias* se retiene el importe manual. Problemas conocidos: C2 (dos liquidaciones en el mes), C3 (no
remunerativos), C4 (deducciones), C5 (escala), C6 (F.572 incompleto), T2 (se graba en borrador).

## SAC (lote SAC)

`SAC_MENSUAL` / `SAC_JORNAL`: `SAC_BASE × 50% × min(1, SAC_DIAS / 180)`.

- `SAC_BASE` es la mayor remuneración mensual del semestre. Hoy **se carga a mano**. Si falta, se usa
  el sueldo actual o `valor hora × horas semanales × 4,333` (C10).
- `SAC_DIAS` son los días trabajados en el semestre. Vacío = 180 (semestre completo).
- Lleva aportes con el tope mensual (C9), Ganancias y contribuciones sobre su propio remunerativo, con
  la detracción completa (C11).

## Vacaciones (lote Vacaciones)

Estructuras `VACACIONES_*_ARG`: sólo la regla de vacaciones más aportes, Ganancias y contribuciones.
`VAC_DIAS` sale de las licencias aprobadas de tipo vacaciones dentro de las fechas del lote (días
corridos). Para no pagarlas dos veces, la quincena o el mes que contiene esos días tiene que tener
`VAC_DIAS` en 0 o sin la regla de vacaciones (C1).

## Liquidación final (lote Liquidación Final)

Estructuras `FINAL_*_ARG`:
- Básico de los días u horas del último período.
- Vacaciones no gozadas (`VAC_NO_GOZ`, Art. 156 LCT).
- SAC proporcional (`SAC_BASE`, `SAC_DIAS`).
- Indemnizaciones por antigüedad (Art. 245), sustitutiva de preaviso (Art. 232) e integración del mes
  (Art. 233). Los importes se calculan fuera del sistema y se cargan como novedad.

Ver C7, C21 y C22.

## Recibos de referencia

`tests/test_recibos_referencia.py`, basado en recibos de referencia, reproduce al centavo la 1° Quincena de septiembre y la 2° Quincena de
agosto de 2026 de un operario UOM. Si una regla cambia y esos tests fallan, el cambio rompe un recibo
real: revisarlo con el liquidador antes de ajustar el test.

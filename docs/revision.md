# Revisión de código y de cumplimiento legal — octubre de 2026

Revisión de `payroll_arg` y `payroll_arg_attendance` (rama `refactor/novedades-inputs`, `ea240c5` /
`982acbf`) contra la LCT, la normativa de Seguridad Social y Ganancias y el CCT UOM 260/75, para
jornalizados (quincenales) y mensualizados. Las respuestas de negocio ya dadas en
[Pendientes](pendientes.md) se toman como decisiones (p. ej. medio tope por quincena, antigüedad sobre
las horas extras).

**Qué no se cambió:** esta revisión sólo documenta. El código no se tocó, salvo comentarios y
docstrings. Cada hallazgo está marcado en el código con `@bug <id>` (lista en el HTML de Doxygen) o
con un comentario `Ver <id>` en la regla salarial.

**Cómo leer la tabla:**

- **Gravedad.** *Alta*: liquida mal sin avisar o genera un archivo legal inválido. *Media*: error en un
  caso plausible o falta de una regla de negocio. *Baja*: detalle o mejora.
- **Estado.** *Confirmado*: reproducido en una base de prueba. *Código*: se ve leyendo el código.
  *Norma*: depende de una interpretación legal, verificar con el estudio contable o el F.931 real.

Los recibos de referencia de referencia (`tests/test_recibos_referencia.py`) siguen dando al centavo: ninguno de
estos casos aparece en ellos (no tienen vacaciones, SAC, horas extras, indemnizaciones ni Ganancias).

## Resumen

| Id | Gravedad | Estado | Tema |
|---|---|---|---|
| [C1](#c1) | alta | Confirmado | Vacaciones pagadas dos veces si se liquidan en un lote de Vacaciones |
| [C2](#c2) | alta | Confirmado | Ganancias: la 2° liquidación del mes pisa el acumulador de la 1° |
| [C3](#c3) | alta | Código | Ganancias: no grava las sumas no remunerativas |
| [C4](#c4) | media | Código | Ganancias: seguro de vida UOM y aporte adicional no se deducen |
| [C5](#c5) | alta | Norma | Ganancias: escala 2026 de ejemplo, no la oficial |
| [C6](#c6) | media | Código | Ganancias: pluriempleo, pagos a cuenta, topes, devoluciones y ajuste anual |
| [C7](#c7) | alta | Código | Indemnizaciones con aporte de Obra Social y cuota sindical |
| [C8](#c8) | media | Código | Contribución de Obra Social sin las sumas no remunerativas |
| [C9](#c9) | media | Norma | Tope imponible del SAC |
| [C10](#c10) | alta | Código | Base del SAC a mano; la estimación deja afuera lo variable |
| [C11](#c11) | media | Norma | Detracción: repetida en SAC / vacaciones / final y sin AAFF ni FNE |
| [C12](#c12) | media | Código | ART: la cuota fija nunca se cobra |
| [C13](#c13) | media | Confirmado | Horas normales: las vacaciones descuentan sábados y domingos |
| [C14](#c14) | baja | Código | Feriado: horas promedio (8,8) en vez de las del día (9) |
| [C15](#c15) | media | Código | Quincena fija de 88 hs sin mirar días hábiles ni ausencias |
| [C16](#c16) | media | Código | Antigüedad y vacaciones: bases inconsistentes |
| [C17](#c17) | baja | Norma | Vacaciones jornal: factor 1,20 sin fuente |
| [C18](#c18) | media | Código | Seguro de vida UOM a convencionados de otros convenios |
| [C19](#c19) | media | Norma | Cuota sindical a todo convencionado (no sólo afiliados) |
| [C20](#c20) | media | Código | Contribuciones repetidas en las dos quincenas |
| [C21](#c21) | media | Código | Liquidación final incompleta |
| [C22](#c22) | alta | Norma | Vacaciones no gozadas con aportes y contribuciones |
| [C23](#c23) | media | Confirmado | Cantidades con 2 decimales: el SAC proporcional paga de más |
| [C24](#c24) | media | Código | Calendarios sin zona horaria fija: el feriado puede contar dos días |
| [E1](#e1) | alta | Código | F.931 por lote y con bases incorrectas |
| [E2](#e2) | media | Código | Libro de Sueldos Digital: códigos de concepto 0 o repetidos |
| [E3](#e3) | alta | Código | Archivos bancarios con CBU / CUIL de relleno |
| [E4](#e4) | media | Código | Recibo y exportaciones con datos inventados |
| [T1](#t1) | alta | Resuelto | `UserError` sin importar en el empleado |
| [T2](#t2) | media | Código | Ganancias se graba al calcular un borrador |
| [T3](#t3) | media | Código | Cambiar las fechas del lote no recarga las novedades |
| [T4](#t4) | baja | Código | Antigüedad guardada sin depender de la fecha de ingreso |
| [T5](#t5) | baja | Código | Validación de licencias aprobadas desactivada de más |
| [T6](#t6) | baja | Código | `name_get` obsoleto en Obras Sociales |
| [T7](#t7) | baja | Código | Campos de compañía sin uso |
| [T8](#t8) | media | Código | Parámetros legales sin fecha de vigencia |
| [T9](#t9) | media | Código | SIRADIG: una presentación vieja pisa la ficha |
| [T10](#t10) | media | Confirmado | "Falta configurar…" de las reglas termina en un error de Python |
| [A1](#a1) | media | Código | Horas extra pendientes o rechazadas pagadas como normales |
| [A2](#a2) | media | Norma | Sábado entero al 100% y feriado trabajado |
| [A3](#a3) | baja | Código | Sin control de topes de horas extra |
| [U1](#u1) | media | Código | Importación CSV acepta códigos inexistentes sin avisar |
| [U2](#u2) | baja | Código | El calendario cambia el tipo de salario por su nombre |
| [U3](#u3) | media | Código | "Recargar novedades" pisa las correcciones manuales sin aviso |
| [U4](#u4) | baja | Código | Botones sin vista: imprimir recibo y confirmar lote |
| [S1–S7](#seguridad) | alta | Resuelto | Permisos: menú, datos sensibles, departamentos, configuración y compañías |
| [G1–G6, F1](#guía-de-usuario) | alta | Resuelto | Errores al seguir la guía de usuario y pestaña de nómina duplicada |

**Prioridad sugerida:**
1. T1 (una línea).
2. C1 y C2: plata mal pagada o retenida.
3. C7 y C22: aportes sobre conceptos exentos en la liquidación final.
4. E3 y C10.
5. E1, si el F.931 se va a presentar desde Odoo.
6. C3 y C5, antes de la primera retención de Ganancias.

---

## Cálculo y cumplimiento legal

### C1

**Vacaciones pagadas dos veces cuando se liquidan en un lote de Vacaciones.** *Alta, confirmado.*

- **Qué pasa.** `_get_period_input_amounts()` carga `VAC_DIAS` con las vacaciones aprobadas en todos
  los lotes salvo SAC, y las estructuras `JORNAL_QUINC_ARG` y `MENSUAL_ARG` tienen las reglas
  `VACACIONES` / `VACACIONES_MENSUAL`. Si las vacaciones se pagaron antes en un lote de tipo
  *Vacaciones* (Art. 155 LCT: se pagan al comenzar; así se hace en enero y febrero), la quincena o el
  mes que contiene esos días las vuelve a pagar.
- **Evidencia.** Licencia del 06 al 12/04/2026, valor hora $30.000: el lote de Vacaciones paga
  `VACACIONES` $2.217.600 y la 1° Quincena de abril paga otra vez $2.217.600.
- **Propuesta.** En los lotes comunes, `VAC_DIAS` sólo para descontar horas o días (`HS_NORM`,
  `BASIC_MENSUAL`). Pagar las vacaciones sólo si no hay un recibo de Vacaciones en espera o hecho
  que cubra esas fechas, o separar la novedad en "días a descontar" y "días a pagar". Test con los dos
  lotes.

### C2

**Ganancias: la segunda liquidación del mes pisa el acumulador de la primera.** *Alta, confirmado.*

- **Qué pasa.** `hr.ganancias.accumulator` es uno por empleado, año y mes, y
  `_calculate_ganancias_from_rules()` lo **reescribe** con los datos del recibo que se calcula. En la
  2° quincena: el bruto de la 1° no entra en el acumulado del mes, la retención de la 1° no se
  descuenta y, al terminar, el acumulador queda sólo con la 2°. Los meses siguientes acumulan la mitad
  del bruto de cada mes. Lo mismo con SAC, vacaciones o liquidación final en el mismo mes que una
  quincena o un mensual.
- **Evidencia.** 1° y 2° quincena de marzo de 2026 ($2.798.400 de remunerativo cada una): queda un solo
  acumulador de marzo con `gross_rem` $2.798.400 (el de la 2°).
- **Efecto.** Retención de menos todo el año para los jornalizados (y para quien cobra SAC), y la
  retención de la 1° quincena no se acredita, así que puede retenerse dos veces.
- **Propuesta.** Un acumulador por recibo (o líneas por recibo dentro del mes). Lo anterior es todo
  recibo del año anterior a este, por fecha de pago y número de liquidación, incluidas las del mismo
  mes. Grabar al confirmar el recibo (ver [T2](#t2)) y borrar o anular la fila si el recibo se cancela.

### C3

**Ganancias no grava las sumas no remunerativas.** *Alta, código.*

- **Qué pasa.** La regla `RET_GANANCIAS` pasa `categories.REM` como bruto. Las sumas no remunerativas
  (`ASIG_NO_REM`, `GRATIF_NO_REM`, `COMPENS_NO_REM`) están gravadas (Art. 82 LIG; confirmado en
  decisión [D5](decisiones.md)).
- **Cuidado.** Las indemnizaciones por despido (`INDEM_ANTIGUEDAD`, `INDEM_PREAVISO`,
  `INTEG_MES_DESPIDO`) también son NOREM y están **exentas** (Art. 26 inc. i LIG), así que no alcanza
  con sumar `categories.NOREM`.
- **Propuesta.** Marca "gravado en Ganancias" en la regla (o categoría propia para las indemnizaciones,
  ver [C7](#c7)) y sumar en el bruto lo gravado.

### C4

**Ganancias no deduce el seguro de vida UOM ni el aporte adicional.** *Media, código.*

- **Qué pasa.** `RET_GANANCIAS` tiene secuencia 150 y deduce `categories.DED` calculado hasta ahí:
  jubilación, INSSJP, Obra Social y sindicato. `RET_UOM_VIDA` (155) y `APORTE_ADIC_SS` (160) se calculan
  después y no se deducen, aunque se había anotado que el seguro de vida UOM estaba incluido. Pregunta [P12](pendientes.md#p12-qué-descuentos-se-deducen-c4).
- **Propuesta.** Definir qué es deducible (los aportes obligatorios y la cuota sindical, sí; el seguro
  de vida, según el tope de primas del Art. 85 inc. b LIG) y pasar las reglas deducibles antes de la
  150, o sumar explícitamente sus códigos.

### C5

**Escala de Ganancias 2026 de ejemplo.** *Alta, norma.*

- **Qué pasa.** `data/ganancias_scale_2026.xml` tiene tramos redondos (1.200.000, 2.400.000…) que no
  coinciden con ninguna tabla publicada por ARCA. Las deducciones (ganancia no imponible 3.091.035,
  especial 14.836.968, cónyuge 2.911.135, hijo 1.468.096) son los importes anuales de 2024 de la
  Ley 27.743. ARCA actualiza los importes dos veces por año.
- **Propuesta.** Cargar la tabla oficial vigente de cada semestre antes de retener. El archivo es
  `noupdate`, así que corregirla en la base no se pierde al actualizar. Agregar un aviso si no hay escala
  para la fecha del recibo (hoy devuelve 0 sin avisar).

### C6

**Ganancias: falta parte del F.572 y del régimen.** *Media, código.*

- Los otros empleadores (pluriempleo) no se leen del XML ni se suman: si la empresa es agente de
  retención, tiene que sumar sus remuneraciones.
- Los pagos a cuenta se guardan pero no se restan del impuesto.
- Deducciones generales = total anual / 12 cada mes: no respeta en qué meses se pagaron ni los topes
  (5% de la ganancia neta para prepaga y donaciones, 40% del alquiler hasta la ganancia no imponible…).
- Cargas de familia: cuenta personas; no aplica meses de vigencia ni el 50% compartido.
- La retención nunca es negativa: no hay devolución si el acumulado baja.
- No hay liquidación anual / final ni el F.1357. El ajuste del año anterior se pidió (decisión D10, alcance en [P13](pendientes.md#p13-ajuste-anual-y-alcance-c6-d10)).

### C7

**Indemnizaciones con aporte de Obra Social y cuota sindical.** *Alta, código.*

- **Qué pasa.** `INDEM_ANTIGUEDAD`, `INDEM_PREAVISO` e `INTEG_MES_DESPIDO` son de categoría NOREM.
  `RET_OS` calcula `base_rem + categories.NOREM` y `RET_SIND` `REM + NOREM`, así que en una liquidación
  final se descuenta 3% de Obra Social y 2,5% sindical sobre las indemnizaciones. Las indemnizaciones
  por despido no son remuneración (Art. 7 Ley 24.241) y no llevan aportes ni cuota sindical.
- **Propuesta.** Categoría propia `INDEM` (tipo de concepto 2 pero fuera de NOREM), o una marca
  "base Obra Social / sindicato" en las reglas no remunerativas de convenio.

### C8

**Contribución de Obra Social sin las sumas no remunerativas.** *Media, código.*

- **Qué pasa.** Decisión [D4](decisiones.md): las sumas no remunerativas entran sólo en la base de
  aportes y contribuciones de Obra Social y sindicato. El aporte (`RET_OS`) las incluye. La contribución
  (`COMP_OS`) usa sólo el remunerativo (o el remunerativo del mes anterior,
  `_get_prev_month_gross()`). El pie del recibo (`_to_recibo_dict()`) sí las incluye, así que pie y
  líneas no coinciden.
- **Propuesta.** Base de `COMP_OS` = remunerativo + no remunerativo de convenio. En jornalizados, sumar
  también `total_no_remunerativo` en `_get_prev_month_gross()`, en una base aparte de la de Seguridad
  Social. Verificar la contribución patronal al sindicato del CCT (hoy `ct_sin` = 0).

### C9

**Tope imponible del SAC.** *Media, norma.*

- **Qué pasa.** `_get_tope_imponible()` usa el tope mensual completo en los lotes de SAC. Para el SAC la
  base máxima se calcula aparte del mes (Art. 9 Ley 24.241); en el SICOSS es el 50% del tope del mes en
  que se paga.
- **Propuesta.** Confirmar con el estudio. Si corresponde: lote SAC → tope / 2. Si el SAC va en la misma
  liquidación que el sueldo, topear cada parte por separado.

### C10

**Base del SAC a mano; la estimación deja afuera lo variable.** *Alta, código.*

- **Qué pasa.** `SAC_BASE` no se calcula: si no se carga, mensualizados usan el sueldo actual y
  jornalizados `valor hora × horas semanales × 4,333`. La Ley 23.041 toma la **mayor remuneración
  mensual devengada** del semestre por todo concepto. Para un jornalizado es la suma de las dos
  quincenas del mejor mes, con extras, feriados, antigüedad, premios y presentismo. La estimación
  paga de menos. Además el proporcional divide por 180 y no por los días reales del semestre.
- **Propuesta.** Novedad automática `SAC_BASE` = máximo, por mes del semestre, del remunerativo de los
  recibos (todas las liquidaciones del mes salvo SAC), y `SAC_DIAS` desde la fecha de ingreso / egreso
  y las licencias sin goce. El usuario sólo revisa.

### C11

**Detracción de la Ley 27.541.** *Media, norma.*

- **Repetida.** Se resta completa en cada liquidación que calcula contribuciones sobre su propio bruto:
  SAC, vacaciones y final (decisión D8; pregunta [P2](pendientes.md#p2-detracción-de-la-ley-27541-c11)). La detracción es mensual por trabajador. En el SAC,
  la práctica de ARCA es aplicar el 50%.
- **Sin AAFF ni FNE.** Se resta en `COMP_JUB` y `COMP_INSSJP`, pero no en `COMP_AAFF` ni `COMP_FNE`. La
  Ley 27.430 (art. 167), que creó el mecanismo, la aplica a las contribuciones de las leyes 19.032,
  24.013, 24.241 y 24.714 (SIPA, INSSJP, FNE y AAFF). Los recibos de referencia no la restan en AAFF / FNE:
  contrastar con un F.931 real antes de cambiar.
- **Proporcional.** En jornadas parciales o meses incompletos la detracción es proporcional; hoy
  siempre es completa.

### C12

**ART: la cuota fija nunca se cobra.** *Media, código.*

`res.company.art_fixed_fee` (cuota fija por trabajador, $1.300 por defecto) se muestra en la compañía
pero ninguna regla la usa: `COMP_ART` es sólo la alícuota variable. Agregarla una vez por mes (como el
seguro de vida UOM, no en la 1° quincena).

### C13

**Horas normales: las vacaciones descuentan días corridos.** *Media, confirmado.*

`HS_NORM = horas de la quincena − VAC_DIAS × horas por día`. `VAC_DIAS` son días corridos (incluye
sábados y domingos). Una semana de vacaciones (lunes a domingo) descuenta 7 × 8,8 = 61,6 hs en lugar de
las 44 que se dejaron de trabajar. En la prueba la quincena quedó en 26,4 hs en lugar de 44. Descontar
las horas del calendario de los días de vacaciones (`resource.calendar.get_work_hours_count`).

### C14

**Feriado: horas promedio en vez de las del día.** *Baja, código.*

`FERIADO = feriados × hours_per_day` (8,8). El calendario UOM tiene 9 hs de lunes a jueves y 8 el
viernes, y el recibo de referencia del 17/08 paga 9 hs. Sumar las horas del calendario de cada feriado.

### C15

**Quincena fija de 88 hs.** *Media, código (convención a confirmar).*

`_get_calendar_hours_for_period()` da 2 × horas semanales para cualquier período de hasta 16 días, sin
mirar si la quincena tiene 10, 11 o 12 días hábiles. Coincide con los recibos de referencia, por eso se dejó.
Sin el módulo de asistencias, tampoco descuenta faltas, licencias sin goce ni enfermedad: el jornalizado
cobra 88 hs aunque haya faltado. Licencias pagas de jornalizados (enfermedad inculpable, Art. 208 LCT;
licencias especiales, Art. 158) no tienen concepto propio. Confirmar si la convención es "88 fijas" u
"horas hábiles reales", y agregar las ausencias.

### C16

**Antigüedad y vacaciones: bases inconsistentes.** *Media, código.*

- Jornalizados: `VACACIONES` (secuencia 40) va después de `ADIC_ANTIG` (20), así que las vacaciones no
  generan antigüedad. Mensualizados: `VACACIONES_MENSUAL` (15) va antes y sí la generan.
- Los lotes de *Vacaciones* y *Liquidación Final* no tienen `ADIC_ANTIG`: las vacaciones pagadas por
  adelantado y el último mes del egreso salen sin antigüedad.
- Art. 155 LCT: el valor del día de vacaciones sale del sueldo que percibe (incluye adicionales fijos
  como la antigüedad), y las reglas usan sólo `contract.wage`.

### C17

**Vacaciones jornal: factor 1,20.** *Baja, norma.*

`VACACIONES` y `VAC_NO_GOZ_JORNAL` pagan `valor hora × horas por día × 1,20`. El Art. 155 inc. b LCT
paga a los jornalizados el jornal del día anterior, sin recargo. El 1,20 iguala el divisor 25 de los
mensualizados (30 / 25). Documentar la fuente (CCT o acuerdo de empresa) o sacarlo.

### C18

**Seguro de vida UOM.** *Media, código.*

- La condición de `RET_UOM_VIDA` y `COMP_UOM_VIDA` es `is_uom or contract.is_convencionado`: cualquier
  convencionado de otro CCT (p. ej. Comercio) paga el seguro de vida UOM. Debería ser sólo UOM.
- `is_uom` mira `cct_id.name or cct_id.code`: si el nombre existe no mira el código.
- Pendientes, punto 6: "hay un seguro de vida de UOM y después uno para todos que lo paga el
  empleador". Hoy hay tres: UOM trabajador, UOM empleador y SCVO. Confirmar si `COMP_UOM_VIDA` existe
  o si era el SCVO. Las dos cuotas UOM tienen el mismo valor por defecto (8.045,65).

### C19

**Cuota sindical a todo convencionado.** *Media, norma.*

`RET_SIND` se descuenta a todo contrato con *Convencionado*. La cuota sindical es de los afiliados; a
los no afiliados sólo corresponde una contribución solidaria si el convenio la establece. Agregar
"Afiliado al sindicato" en el contrato y, si el CCT lo prevé, la contribución solidaria aparte.

### C20

**Contribuciones repetidas en las dos quincenas.** *Media, código.*

Todas las contribuciones (incluido el SCVO, prima mensual) se calculan en la 1° y en la 2° quincena
sobre el remunerativo del mes anterior: replica el cuadro "Costo Total Empleado" de los recibos de referencia,
pero `total_contribuciones` y `costo_total_empleador` de un mes suman el costo dos veces. El comentario
del XML decía "sólo 2° Quincena" (corregido). Decisión D7 ("error en el ejemplo"); pregunta [P10](pendientes.md#p10-costo-del-empleador-en-los-reportes-c20).
Propuesta: el cuadro del recibo sigue mostrando el último mes declarado, como dato informativo y
aparte; las líneas de contribución reales se calculan una vez por mes (2° quincena, sobre Q1 + Q2).

### C21

**Liquidación final incompleta.** *Media, código.*

- Las tres indemnizaciones se cargan a mano: el sistema no calcula la mejor remuneración mensual
  normal y habitual, los años, el tope del convenio ni el piso Vizzoti (67%).
- Falta el SAC sobre la indemnización sustitutiva del preaviso, sobre la integración del mes y sobre
  las vacaciones no gozadas.
- El último mes trabajado sale sin antigüedad ([C16](#c16)).
- Las indemnizaciones pagan Obra Social y cuota sindical ([C7](#c7)).

### C22

**Vacaciones no gozadas con aportes y contribuciones.** *Alta, norma.*

`VAC_NO_GOZ_MENS` y `VAC_NO_GOZ_JORNAL` (y el SAC proporcional que generan) son de tipo remunerativo, así
que pagan jubilación, INSSJP, Obra Social, sindicato y contribuciones. El Art. 7 de la Ley 24.241 excluye
de la remuneración las indemnizaciones por vacaciones no gozadas, igual que las derivadas del despido.
Sí están gravadas en Ganancias. Pasarlas a una categoría no remunerativa sin aportes, con la marca de
gravadas de [C3](#c3).

### C23

**Cantidades con 2 decimales: el SAC proporcional paga de más.** *Media, confirmado (escenario F).*

`hr.payslip.line.quantity` tiene 2 decimales. `SAC_PROP_*` y `SAC_*` usan `result_qty = días / 180`:
77 / 180 = 0,4278 se guarda como 0,43. En el ejercicio 7 la línea paga 496.590 × 0,43 = 213.533,70 en
lugar de 212.430,17 (1.103,53 de más). Las reglas siguientes usan el valor sin redondear: el bruto
(`GROSS`) y la jubilación se calculan sobre 1.321.230,17, pero *Total Remunerativo* suma la línea y da
1.322.333,70. Propuesta: pasar la proporción al importe (`result = base × 50% × días / 180`, cantidad =
días) o dar más decimales a la cantidad.

### C24

**Calendarios sin zona horaria fija: el feriado puede contar dos días.** *Media, código.*

Los calendarios de `data/afip_data.xml` no fijan `tz` y toman la del usuario que instala (UTC en
`claude_pa_fresh`, Buenos Aires en `mydb`). `_get_calendar_public_holidays_count()` lee el feriado en
la zona horaria del calendario. Un feriado guardado como 00:00–23:59 de Argentina (03:00 a 02:59 UTC del
día siguiente) en un calendario en UTC cuenta dos días: 17,6 hs en lugar de 8,8. Pasó al crear el
feriado por código en los escenarios. Desde la interfaz, Odoo corre las fechas de la zona del usuario
a la del calendario, así que hay que verificar si un usuario lo provoca. Las fichadas
(`payroll_arg_attendance`) usan la misma zona horaria. Propuesta: fijar `America/Argentina/Cordoba` en
los calendarios del XML.

## Exportaciones

### E1

**F.931 por lote y con bases incorrectas.** *Alta, código.*

- El F.931 es una declaración **mensual** por CUIL. `_prepare_f931_payload()` arma una por lote: dos
  quincenas dan dos archivos con medio mes cada uno, y el SAC o las vacaciones, otro.
- `_get_afip_info_f931()` pone el remunerativo total en las remuneraciones 1 a 5 y 8 a 10. Pero la
  remuneración 1 (aportes SIPA) y la 5 (INSSJP) van con tope, la 4 y la 8 (Obra Social) incluyen el no
  remunerativo de convenio, y la detracción va en 0.
- Jornalizados: `k_dias` = 0 (el F.931 pide días trabajados), y `k_horas` trunca decimales.
- Si faltan datos completa con valores de relleno (CUIL 20000000000, actividad 049, zona 18, obra social
  126205) sin avisar.
- **Propuesta.** Exportar por mes (todos los lotes del período), sumar por CUIL, calcular cada base
  con su regla y validar antes de generar (sin valores de relleno). Contrastar con el borrador del F.931
  de un mes real.

### E2

**Libro de Sueldos Digital: códigos de concepto.** *Media, código.*

- `OBJETIVOS`, `PREMIO_PROD`, `PRESENTISMO` y `PORTITULO` tienen `afip_code` "0": el LSD rechaza
  conceptos sin código registrado.
- `FERIADO` y `HS_EXT_50` comparten 130000, y las tres sumas no remunerativas 550000. Si cada código
  del empleador apunta a un concepto de ARCA distinto, deben ser distintos.
- `ADIC_ANTIG` tiene unidad "%" pero informa cantidad 1 (la línea guarda los años en `rate`).
- `RET_UOM_VIDA` usa 820002 (registrarlo en la tabla de conceptos, [P6](pendientes.md#p6-seguros-de-vida-c18)).

### E3

**Archivos bancarios con CBU / CUIL de relleno.** *Alta, código.*

`action_generate_report()` arma Galicia y Santander con `cbu or "0000000000000000000000"` y
`cuil or "20000000000"`. Un empleado sin CBU sale en el archivo de pago con una cuenta inválida, y los
recibos con neto 0 o negativo se omiten sin decirlo. Validar antes (CBU de 22 dígitos con sus dígitos
verificadores, CUIL válido) y listar los omitidos.

### E4

**Recibo y exportaciones con datos inventados.** *Media, código.*

`_to_recibo_dict()` y el LSD completan lo que falta con valores ficticios: CUIT del empleador
20123456780, número de calle "100" (usa `street2`, que no es el número), código postal 5000, fecha de
ingreso 2020-01-01, categoría "Operario", banco del último aporte "Banco Nación". El recibo es un
documento legal (Art. 140 LCT). Mejor frenar con la lista de datos faltantes. [P16](pendientes.md#p16-formato-del-recibo-pdf) anota el
nombre ("Nombre: , JOHN DOE") y el importe en letras.

## Técnicos

### T1

**`UserError` sin importar en el empleado.** *Alta (arreglo de una línea), código.*
`models/hr_employee.py` usa `UserError` en `action_reapply_latest_siradig()` pero sólo importa
`ValidationError`. Un empleado sin F.572 termina en `NameError` al tocar el botón.

### T2

**Ganancias se graba al calcular.** *Media, código.*
El acumulador se escribe en cada `compute_sheet()`, también en borrador o en una vista previa, y si el
recibo se borra la fila queda (`payslip_id` pasa a vacío) y sigue sumando en los meses siguientes.
Grabar al confirmar y borrar al cancelar (junto con [C2](#c2)).

### T3

**Cambiar las fechas del lote no recarga las novedades.** *Media, código.*
`hr.payslip.run.write()` copia las fechas a los recibos, pero `HS_NORM`, `FERIADO` y `VAC_DIAS` siguen
siendo los del período viejo hasta que se use *Recargar Novedades del Período*. Recargar sólo los
códigos automáticos que no se tocaron a mano, o avisar.

### T4

**`antiguedad_anios`** es guardado y depende de `contract_id` y `date_to`, no de la fecha de ingreso del
contrato. Corregir la fecha de ingreso no actualiza los recibos en borrador.

### T5

**`hr.leave._check_date_state()`** se desactiva entero si el contexto trae `module`, `install_mode` o
`import_file`. Una importación de licencias aprobadas puede moverles las fechas.

### T6

**`afip.health.insurance.name_get()`** no se usa en Odoo 17+: la obra social se ve sin código. Pasar a
`_compute_display_name`.

### T7

**Campos sin uso.** `ss_contrib_rate` no lo usa nadie. `afip_company_type` (20,4% / 18%) sólo se
informa, no cambia las alícuotas de las cuatro contribuciones. `has_reduction` sólo se informa en el
F.931.

### T8

**Parámetros legales sin fecha de vigencia.** Tope imponible (se actualiza todos los meses por la
movilidad), cuotas de seguros, alícuota ART y escala salarial del convenio son un único valor en la
compañía o la categoría. Recalcular un recibo viejo usa el valor de hoy. Propuesta: tabla de parámetros
con vigencia desde / hasta, o guardar en el recibo los valores usados.

### T9

**SIRADIG.** Con *Aplicar inmediatamente*, importar un F.572 con un número de presentación menor
después de uno mayor pisa la ficha con los datos viejos. Aplicar sólo la última presentación del
período.

### T10

**"Falta configurar…" de las reglas termina en un error de Python.** *Media, confirmado.*

Las reglas avisan los datos que faltan con `raise ValueError("Falta configurar …")`, pero `ValueError`
no existe en el entorno donde Odoo evalúa las reglas (`safe_eval`). El usuario ve *"Wrong python code
defined for salary rule …"* con `NameError: name 'ValueError' is not defined`, en lugar del mensaje.

- Se ve, por ejemplo, con un empleado *Convencionado* sin convenio.
- Propuesta: agregar al contexto de las reglas una función `falta(mensaje)` que levante un `UserError`
  con el nombre del empleado, y que el cálculo muestre sólo ese mensaje.

## Asistencias (`payroll_arg_attendance`)

### A1

**Horas extra pendientes o rechazadas pagadas como normales.** *Media, código.*
`HS_NORM = horas fichadas − extras aprobadas`. Con validación por responsable, una hora extra todavía
sin aprobar (o rechazada) queda dentro de `HS_NORM` y se paga como normal. Si se aprueba después,
el recibo ya está cerrado. Restar todas las extras detectadas de las normales y pagar sólo las aprobadas
como extras, o frenar el cálculo si hay extras pendientes.

### A2

**Recargos.** *Media, norma.*
Sin líneas del motor de horas extras, todo el sábado va al 100%. El Art. 201 LCT paga 100% desde el
sábado a las 13 hs, y el resto del sábado al 50% (verificar el CCT). Un feriado trabajado suma el pago
del feriado (`FERIADO`) más las horas al 100%. El Art. 166 LCT dice "remuneración normal más una
cantidad igual": revisar que no se pague triple.

### A3

**Topes de horas extra.** *Baja.* No hay aviso al pasar los límites del Decreto 484/2000 (3 hs por día,
30 por mes, 200 por año).

## Usabilidad

### U1

**Importación CSV.** Una columna con un código que no existe (`PRESENTISMOO`) se guarda como entrada que
ninguna regla lee, sin avisar. El empleado se busca también por nombre, que puede repetirse. El legajo
con ceros a la izquierda ("007") no coincide con el legajo 7. Validar los encabezados contra las
entradas de la estructura, avisar las filas ambiguas y normalizar el legajo.

### U2

**El calendario cambia el tipo de salario.** Elegir un calendario cuyo nombre diga "admin" o que tenga
40 / 48 hs pasa el contrato a mensualizado y cambia la estructura, sin aviso. Preguntar o limitarse a
los calendarios del módulo.

### U3

**"Recargar novedades" pisa las correcciones.** Recargar vuelve a escribir `HS_NORM`, `FERIADO`,
`VAC_DIAS` y `DED_SIRADIG` aunque el usuario las haya corregido a mano. Marcar las entradas editadas a
mano y no pisarlas (o avisar cuáles cambian).

### U4

**Botones sin vista.** `hr.payslip.action_print_recibo_pdf()` y `hr.payslip.run.action_confirm_payslips()`
no tienen botón (ver la tabla de puntos de entrada de la [referencia](referencia.md)). Agregarlos o
borrarlos.

## Seguridad

Revisión de permisos del 26/10/2026, resuelta en el PR "Seguridad" (detalle en
[Seguridad](seguridad.md)).

| Id | Problema | Estado |
|---|---|---|
| S1 | La app de nómina aparecía a todos los usuarios internos (menú *Nómina Argentina* sin grupo). | Resuelto |
| S2 | RR. HH. sin nómina leía el CBU, las cargas y deducciones de Ganancias, el aporte adicional y el F.572. | Resuelto (D13) |
| S3 | El oficial de nómina está limitado a los recibos de su departamento, pero no a las novedades, líneas, acumuladores ni F.572. | Resuelto |
| S4 | En OCA, cualquier permiso de nómina da *Empleados: Administrador*. | Se mantiene (D14) |
| S5 | Los lotes son sólo para *Haberes: Administrador* (OCA). | Se mantiene: liquidador = Administrador (D14) |
| S6 | El oficial de nómina podía cambiar convenios, categorías, tablas y escalas, y actualizar sueldos en masa. | Resuelto |
| S7 | Sin reglas por compañía en los modelos nuevos; la escala de Ganancias no se elegía por compañía. | Resuelto (D15) |

## Guía de usuario

Validación del 26/10/2026: `tests/test_guia_usuario.py` sigue la [guía](usuario/guia.md) con `Form`, que
reproduce lo que hace la interfaz (onchanges, campos visibles y de sólo lectura). Encontró y corrigió:

| Id | Problema | Estado |
|---|---|---|
| G1 | Un recibo nuevo desde *Liquidaciones del empleado* fallaba siempre (`'hr.employee' object has no attribute 'first_contract_date'`), con o sin contrato. | Resuelto |
| G3 | La plantilla de alta masiva traía CUIL inválidos: importarla fallaba. | Resuelto |
| G4 | Un empleado sin contrato en el lote frenaba la generación a mitad de camino, sin decir dónde corregirlo. | Resuelto |
| G5 | *Bruto Mes Anterior Manual*, el tope y los overrides no se podían editar en recibos *En espera* (como quedan al generar). | Resuelto |
| G6 | El archivo del Galicia fallaba con cualquier empleado (apellido vacío). | Resuelto |
| F1 | El empleado tenía dos pestañas de nómina con sueldo, estructura y horario repetidos; los datos AFIP no estaban en el empleado. | Resuelto: una sola pestaña *Nómina* |

T1 también se corrigió en esta validación.

## Lo que está bien

- Alícuotas por defecto correctas para empleador del sector privado no incluido en el inc. a: 10,77 +
  1,59 + 4,70 + 0,94 = 18% (Ley 27.541); aportes 11 + 3 + 3; Obra Social patronal 6%.
- Tope imponible sólo en los aportes del trabajador (las contribuciones no tienen tope).
- Mensualizados: valor día sueldo / 30 con 4 decimales (30 días dan el sueldo exacto) y vacaciones
  sueldo / 25 (Art. 155 inc. a LCT), divisor configurable por convenio.
- Horas extra al 50% y al 100% sobre el valor hora (Art. 201 LCT). Antigüedad 1% por año (CCT UOM).
- Ganancias por el método acumulativo con escala y deducciones proporcionales al mes (RG 4003).
- Las novedades tienen una sola fuente (las entradas del recibo) y el cálculo nunca las modifica: se
  puede recalcular sin perder datos.
- Los dos recibos de referencia se reproducen al centavo, con tests.

# Preguntas abiertas

Para discutir con el liquidador y el estudio contable. Cada pregunta tiene el contexto, un ejemplo y las
opciones. La respuesta se escribe debajo de **Respuesta** (con fecha y quién respondió); después se pasa a
[Decisiones](decisiones.md) y se implementa en el PR del tema. Los ids entre paréntesis son los de la
[revisión](revision.md).

Para ver cada caso en el sistema, los [escenarios de prueba](usuario/escenarios.md) indican en qué
ejercicio aparece.

## Seguridad social y convenio

### P1. Tope imponible del SAC (C9)

Hoy el lote de SAC topea los aportes con el tope **mensual completo** (4.250.000). Para el SAC, ¿la base
máxima es el 50% del tope del mes de pago (2.125.000)?

- **Ejemplo:** E (6.500.000) cobra SAC 3.250.000. Con tope completo aporta 11% de 3.250.000 = 357.500;
  con medio tope, 11% de 2.125.000 = 233.750.
- **Opciones:** a) 50% del tope; b) tope completo, como hoy; c) otra regla (indicar).

**Respuesta:**

### P2. Detracción de la Ley 27.541 (C11)

**a)** Hoy se resta en jubilación e INSSJP patronales, pero no en AAFF ni FNE. La Ley 27.430 (art. 167)
la aplica a las cuatro. Los recibos reales tampoco la restan en AAFF y FNE. ¿Cómo está en el F.931 real
de la empresa?

**b)** En los lotes de SAC, vacaciones y final se resta otra vez completa (D8: puede haber varios
recibos en el mes). ¿Una sola vez por mes? ¿En el SAC el 50%?

- **Ejemplo:** el SAC de D (693.750) hoy resta 7.003,68 completos de su base de contribuciones, además de
  los que ya restó el recibo mensual.

**Respuesta:**

### P3. Horas de la quincena y ausencias (C15)

D1 fija 88 hs por quincena. Sin el módulo de asistencias, una falta, una licencia sin goce o una
enfermedad no descuentan horas.

- ¿Las faltas se descuentan cargando `HS_NORM` a mano, o el sistema tiene que descontarlas de las
  licencias?
- ¿Cómo se paga la enfermedad inculpable (Art. 208 LCT) y las licencias especiales (matrimonio,
  nacimiento, fallecimiento, examen, Art. 158) a un jornalizado?
- ¿Se van a usar las fichadas (`payroll_arg_attendance`) en producción?

**Respuesta:**

### P4. Antigüedad sobre vacaciones y en la liquidación final (C16)

Hoy las vacaciones de jornalizados no generan antigüedad (sí las de mensualizados), y los lotes de
Vacaciones y Final no tienen antigüedad.

- **Ejemplo:** C, en el ejercicio 4, cobra vacaciones por 665.280 sin el 3% de antigüedad (19.958,40).
- ¿Las vacaciones (adelantadas o dentro del recibo) llevan antigüedad? ¿Y el último período de la
  liquidación final?

**Respuesta:**

### P5. Factor 1,20 en las vacaciones de jornalizados (C17)

Las vacaciones de jornalizados se pagan valor hora × 8,8 × 1,20 por día. La LCT (Art. 155 inc. b) dice
el jornal del día anterior, sin recargo. ¿De dónde sale el 1,20: convenio, acuerdo de empresa,
costumbre? ¿Se usa 8,8 (promedio) o las horas reales del día (9 u 8)?

**Respuesta:**

### P6. Seguros de vida (C18)

Hay tres conceptos:

| Concepto | Quién paga | Importe | Cuándo |
|---|---|---|---|
| Seguro de vida UOM | trabajador | 8.045,65 | 2° quincena y mensual |
| Seguro de vida UOM | empleador | 8.045,65 | 2° quincena y mensual |
| SCVO | empleador | 424,62 | en todas las liquidaciones |

- ¿Existe el UOM patronal o era el SCVO?
- ¿Los importes son los vigentes?
- ¿El UOM trabajador corresponde también a mensualizados UOM?
- ¿El código LSD del UOM trabajador es 820002 (hay que registrarlo en ARCA)?
- Hoy se cobra a cualquier convencionado, aunque su convenio no sea UOM: ¿sólo UOM?

**Respuesta:**

### P7. Cuota sindical (C19)

Hoy se descuenta 2,5% a todo convencionado.
- ¿Todos los convencionados están afiliados?
- Para los no afiliados, ¿corresponde una contribución solidaria del convenio (alícuota)?
- ¿El empleador aporta algo al sindicato (hoy 0 en el pie del recibo, C8)?

**Respuesta:**

### P8. Vacaciones no gozadas al egreso (C22)

Hoy son remunerativas: pagan aportes y contribuciones. El Art. 7 de la Ley 24.241 las excluye de la
remuneración.

- **Ejemplo:** F, en el ejercicio 7: 712.800 de vacaciones no gozadas con 11% + 3% + 3% + 2,5% de aportes
  (139.000 aprox.).
- ¿Se liquidan como no remunerativas (sin aportes, gravadas en Ganancias)?

**Respuesta:**

### P9. Recargos de horas extras (A2)

- Sábado: ¿100% todo el día, o 50% hasta las 13 y 100% después (Art. 201 LCT)? ¿Qué dice el convenio?
- Feriado trabajado: hoy se paga el feriado más las horas al 100%. ¿Es así, o sólo el doble del día
  (Art. 166 LCT)?

**Respuesta:**

### P10. Costo del empleador en los reportes (C20)

D7 deja el cuadro del recibo como está. Para un reporte de costo mensual hay que contar las
contribuciones una sola vez.

**Propuesta:** el cuadro del recibo sigue mostrando el último mes declarado, como dato informativo; las
contribuciones reales se calculan una vez por mes, en la 2° quincena, sobre Q1 + Q2.

¿De acuerdo? ¿Qué quisiste decir con "error en el ejemplo"?

**Respuesta:**

### P11. Base de contribuciones (C8)

- Con D4, la contribución de Obra Social tiene que incluir las sumas no remunerativas. En jornalizados,
  ¿la base del mes anterior suma también el no remunerativo para Obra Social?
- ¿Los mensualizados también deberían contribuir sobre el mes anterior, como los jornalizados, o sobre
  su propio recibo como hoy?
- Para cerrar la verificación de los recibos reales: ¿a qué mes corresponde cada uno (la base de la
  1° quincena es 2.251.856,26 y la de la 2° 3.945.490,21)?

**Respuesta:**

## Ganancias

### P12. Qué descuentos se deducen (C4)

Hoy se deducen jubilación, INSSJP, Obra Social y cuota sindical. No se deducen el seguro de vida UOM ni
el aporte adicional de Seguridad Social, porque se calculan después. ¿Se deducen? (El seguro de vida
tiene tope de primas, Art. 85 inc. b LIG.)

**Respuesta:**

### P13. Ajuste anual y alcance (C6, D10)

Para dimensionar el trabajo:
- ¿Liquidación anual / final con el F.1357 (presentación a ARCA)?
- ¿Devolución de retenciones de más?
- ¿Empleados con otro empleador (pluriempleo)?
- ¿Topes de cada deducción del F.572 (prepaga 5%, alquiler 40%)?
- ¿Meses de vigencia de las cargas de familia?

**Respuesta:**

### P14. Escala oficial (C5)

¿Quién provee las tablas de Ganancias de cada semestre (estudio contable o descarga de ARCA)? ¿Se
liquidó Ganancias en Odoo antes de cargarlas?

**Respuesta:**

## Exportaciones y recibo

### P15. F.931 (E1)

¿El F.931 se va a presentar desde el TXT de Odoo, o se genera en SICOSS / ARCA a partir del Libro de
Sueldos Digital? Si es lo segundo, alcanza con que el LSD esté bien y el TXT del F.931 queda como
control.

**Respuesta:**

### P16. Formato del recibo PDF

- **Antigüedad:** hoy muestra cantidad 6,00 y base 647.507,98 (total); el recibo real muestra 0,06 y
  400,52 (por hora). ¿Cuál se quiere?
- **Nombre:** sale "Nombre: , JOHN DOE". ¿Apellido y nombre separados? Hay que cargarlos así en la ficha.
- **Importe en letras:** dice "punto tres cuatro". ¿"con 34/100"?
- ¿Alguien puede comparar el pie (composición salarial) con un recibo real?

**Respuesta:**

### P17. Indemnizaciones (C21)

¿El sistema tiene que calcular las indemnizaciones (mejor remuneración, años, tope del convenio, piso
Vizzoti) o se siguen cargando calculadas por el estudio?

**Respuesta:**

## Operación

### P18. Aporte adicional de Seguridad Social en mensualizados

Se descuenta en 2° Quincena y en Mensual. La respuesta fue "aparentemente funciona igual, pero hay que
verlo": confirmar con un recibo real de un mensualizado que lo tenga.

**Respuesta:**

### P19. Aumento a mitad de período

Si el contrato cambia a mitad de quincena o de mes (aumento, cambio de categoría), hoy se usa la primera
versión del período. ¿Se liquida proporcional (días con cada valor) o con el valor nuevo desde la
quincena siguiente?

**Respuesta:**

### P20. Parámetros con vigencia (T8)

**Propuesta:** guardar tope, cuotas de seguros, alícuota ART y escalas salariales con fecha desde /
hasta, para que recalcular un recibo viejo use los valores de su período. ¿De acuerdo? ¿Quién los
actualiza cada mes?

**Respuesta:**

## Pendientes técnicos (sin pregunta)

- **Matriz del lote** con muchos empleados y con jornalizados y mensualizados mezclados (filas con
  celdas vacías): probarla en la instancia de prueba.
- **Composición salarial del pie del recibo:** contrastarla con un recibo real (P16).
- **`hours_per_week` vs `full_time_required_hours`:** revisar si `payroll_arg_reportes` usa el segundo
  como horas del calendario (los calendarios del módulo muestran 40 en `full_time_required_hours`
  aunque el jornal tenga 44).
- **Valores fijos que quedan en reglas:** 44 hs semanales, 8 hs por día y 4,333 semanas por mes como
  respaldo en SAC y vacaciones jornal (C10, C17).

## Historial

- **14/10/2026:**
  - la matriz del lote deja editar todas las celdas (todo recibo recibe todas las entradas);
  - la matriz se dividió en cantidades e importes;
  - los datos de ejemplo pasaron a `noupdate`;
  - el PDF muestra la columna Base;
  - el total de contribuciones del PDF usa los totales del recibo.
- **26/10/2026:**
  - revisión completa ([revision.md](revision.md));
  - las respuestas de negocio pasaron a [decisiones.md](decisiones.md);
  - se agregaron la guía de usuario y los escenarios de prueba.

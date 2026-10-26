# Guía de uso de la Nómina Argentina

Para quien liquida sueldos en Odoo. Explica qué hacer en cada pantalla, qué revisar y qué cuidar. Para
practicar con datos ficticios y resultados conocidos, seguir después los [Escenarios](escenarios.md).

> El módulo está en revisión. Los recuadros **Atención** marcan problemas conocidos (con su id de la
> [revisión](../revision.md)) que hay que controlar a mano hasta que se arreglen.

## 1. Dónde está cada cosa

| Quiero… | Menú |
|---|---|
| Liquidar (quincenas, mes, vacaciones, SAC, final) | *Haberes › Procesamiento de liquidaciones* (lotes) |
| Ver o buscar recibos sueltos | *Haberes › Liquidaciones del empleado* |
| Convenios, categorías, obras sociales, tablas AFIP | *Haberes › Nómina Argentina* |
| Ganancias: escalas, acumuladores, F.572 | *Haberes › Nómina Argentina › Ganancias: …* |
| Importar o exportar empleados en Excel | *Haberes › Nómina Argentina › Importar / Exportar Empleados* |
| Empleados y contratos | *Empleados* |
| Vacaciones y licencias | *Ausencias* |
| Fichadas | *Asistencias* |
| Alícuotas, tope, detracción, seguros | *Ajustes › Compañías › (compañía) › pestaña Nómina Argentina* |

Para liquidar hace falta el permiso **Haberes: Administrador**. Qué ve cada perfil está en
[Seguridad](../seguridad.md).

Palabras que se usan en toda la guía:

- **Lote**: una liquidación (p. ej. "1° Quincena Agosto 2026") con un recibo por empleado.
- **Novedad**: un dato variable del período (horas, días, importes) que el recibo usa para calcular.
- **Jornalizado**: cobra por hora; se liquida por quincena.
- **Mensualizado**: cobra un sueldo fijo; se liquida por mes.

Más términos en el [glosario](../conceptos.md#glosario).

## 2. Configuración inicial (una vez, o cuando cambia la norma)

### 2.1 Compañía

*Ajustes › Compañías › pestaña Nómina Argentina (ARCA / AFIP)*:

- **Datos fiscales:** CUIT (11 dígitos) y tipo de empresa.
- **Último pago de Seguridad Social:** banco, mes, año y fecha del último F.931 pagado. Se imprimen en el
  recibo (lo exige el Art. 140 de la LCT). **Actualizarlos todos los meses.**
- **Contribuciones patronales:** jubilación 10,77%, INSSJP 1,59%, AAFF 4,70%, FNE 0,94%, Obra Social 6%;
  coeficientes de contribución; ART; seguros.
- **Retenciones al trabajador:** jubilación 11%, INSSJP 3%, Obra Social 3%.
- **Tope y detracción:** el tope imponible cambia **todos los meses**; cargar el vigente antes de
  liquidar.

> **Atención (T8).** Estos valores no guardan fecha. Si se recalcula un recibo viejo, usa el valor de
> hoy.

### 2.2 Convenios y categorías

- *Convenios Colectivos (CCT)*: cuota sindical (UOM 2,5%) y divisor de vacaciones (25).
- *Categorías Laborales*: el básico vigente de cada categoría (valor hora para jornalizados, sueldo para
  mensualizados). Con una escala nueva del convenio: cargar los básicos y apretar **Actualizar Sueldos
  de Contratos**. Ese botón pisa también los sueldos pactados por encima de la categoría: revisarlos
  después.

### 2.3 Calendarios y feriados

- Jornalizados usan **Jornal Fábrica UOM (44 hs/semana)**: lunes a jueves 9 hs, viernes 8 hs.
  Mensualizados usan **Administración / Mensual (40 hs/semana)**.
- La zona horaria del calendario tiene que ser **America/Argentina/Cordoba** (C24).
- **Feriados:** en el calendario, pestaña de ausencias globales, un renglón por feriado (día completo).
  Sólo cuentan los que caen de lunes a viernes.

### 2.4 Ganancias

- *Ganancias: Escalas y Deducciones Art. 94*: una escala por período con los tramos y las deducciones
  personales **anuales** que publica ARCA.

> **Atención (C5).** La escala 2026 que trae el módulo es de ejemplo: reemplazarla por la oficial antes de
> retener.

- *Importar SIRADIG AFIP*: subir el ZIP o XML del SIRADIG – Empleador con **Aplicar inmediatamente**
  marcado. Actualiza en cada ficha el cónyuge, los hijos y la deducción mensual.

## 3. Empleados y contratos

### 3.1 Alta de un empleado

En *Empleados › Nuevo*:

1. **Nombre** y, en la pestaña de nómina argentina: **CUIL** (se valida), **N° de legajo**, **forma de
   pago** y **CBU** (22 dígitos), **obra social** y adherentes.
2. **Contrato** (pestaña de contrato / versión):
   - **Fecha de inicio:** es la de ingreso; de ella sale la antigüedad.
   - **Categoría laboral:** propone el tipo de salario, el convenio y el básico.
   - **Tipo de salario:** *Jornalizado* (el sueldo es el **valor hora**) o *Mensualizado* (sueldo
     mensual). Al cambiarlo se ajustan solos la estructura, el calendario y la periodicidad.
   - **Convencionado:** marcado si está en convenio (cuota sindical y antigüedad). Desmarcado = fuera
     de convenio.
   - **Datos AFIP:** modalidad de contratación, situación de revista, condición, actividad, zona y
     código de siniestrado (van al F.931 y al Libro de Sueldos).
3. **Ganancias:** cónyuge, hijos e hijos incapacitados (se completan solos con el F.572) y *Aporte
   Adicional Seg. Social* si corresponde.

**Para dar de baja:** cargar la fecha de fin del contrato y hacer la liquidación final (ver 8.3).

### 3.2 Alta masiva

*Importar / Exportar Empleados*:

1. Exportar la **plantilla**.
2. Completarla: legajo, nombre, CUIL, tipo de salario, código de convenio y categoría, sueldo, fecha de
   ingreso, código de obra social, forma de pago, CBU, lugar de trabajo.
3. Importarla. Si el CUIL o el legajo ya existen, actualiza al empleado.
4. El resumen muestra las filas con error.

## 4. Licencias

- **Vacaciones:** *Ausencias › Nueva*, tipo **Licencia por Vacaciones (LCT)**, días corridos. Tiene que
  quedar **aprobada**. Sólo ese tipo se cuenta como vacaciones.
- Otras licencias (enfermedad, especiales) todavía no tienen concepto propio en el recibo de
  jornalizados (C15): cargar las horas a mano.

## 5. Liquidar una quincena (jornalizados)

1. *Procesamiento de liquidaciones › Nuevo*. Completar:
   - **Nombre**, p. ej. "1° Quincena Agosto 2026".
   - **Tipo de Liquidación AFIP:** *1° Quincena* (del 1 al 15) o *2° Quincena* (del 16 al último día).
     Propone el número de liquidación (1 o 2) y la estructura de jornales.
   - **Fechas** del período y **Fecha de Pago**.
   - **Coeficientes de contribución:** vienen de la compañía.
2. Guardar y **Generar nóminas** (*Generate Payslips*): elegir los empleados y **Generar**. Cada recibo
   nace con sus novedades automáticas:
   - **horas normales** (88 por quincena, o las fichadas);
   - **feriados** del período;
   - **días de vacaciones** aprobadas;
   - **deducción SIRADIG**;
   - en la 2° quincena, el **aporte adicional**.
3. **Valores del lote** (pestaña *Novedades*): lo que es igual para todos, p. ej. el precio de la vianda.
   Agregar la novedad, el valor y **Aplicar a todos**.
4. **Novedades por empleado**, en la misma pestaña, en dos tablas: *Horas, Días y Cantidades* e
   *Importes ($)*. Una fila por empleado y una columna por novedad (ver la [tabla de
   novedades](#7-novedades)). También se puede usar **Importar Novedades (CSV)**.
5. **Base de contribuciones del primer mes.** La quincena toma la base del mes anterior de los recibos
   de Odoo. Si es el primer mes en Odoo, cargar en cada recibo *Bruto Mes Anterior Manual* con el bruto
   remunerativo del mes anterior del sistema viejo.
6. **Recalcular Recibos.** Si falta contrato, estructura o básico, el sistema avisa con el nombre del
   empleado.
7. Revisar los recibos (sección 6).
8. Exportar (sección 9) y **Cerrar** el lote. Cerrar confirma todos los recibos.

> **Atención (T3).** Si se cambian las fechas del lote, apretar **Recargar Novedades del Período**: si no,
> quedan las horas y feriados del período anterior.
>
> **Atención (U3).** *Recargar Novedades del Período* vuelve a escribir horas, feriados, vacaciones y
> SIRADIG **aunque se hayan corregido a mano**. Usarlo antes de corregir, no después.

## 6. Revisar un recibo

Abrir el recibo desde la pestaña *Recibos* del lote (botón de la flecha). Mirar, en este orden:

1. **Líneas** (cálculo): cada concepto con cantidad, base e importe.
2. **Resumen de Liquidación Argentina:**
   - **Bases Imponibles y Topes:** si se aplicó el tope (*Tope Aplicado*) y la base del mes anterior.
   - **Antigüedad:** años (se pueden pisar con *Override Antigüedad*).
   - **Ganancias:** estado e importe retenido (se puede pisar con *Override Retención Ganancias*).
   - **Totales:** remunerativo, no remunerativo, retenciones, **neto**, contribuciones, costo.
3. **Contribuciones Patronales:** cada contribución con alícuota, base y total.

### Control rápido a mano (jornalizado)

| Concepto | Cuenta |
|---|---|
| Básico | horas × valor hora |
| Feriado | horas del feriado × valor hora |
| Extras 50% / 100% | horas × valor hora × 1,5 / × 2 |
| Antigüedad | años % × (normales + feriado + extras 50% × 1,5 + extras 100% × 2) × valor hora |
| Jubilación / INSSJP | 11% / 3% del remunerativo (hasta medio tope por quincena) |
| Obra Social | 3% de (remunerativo hasta medio tope + no remunerativo) |
| Cuota sindical | 2,5% de (remunerativo + no remunerativo) |
| Seguro de vida UOM | cuota fija, sólo en la 2° quincena |
| Neto | remunerativo + no remunerativo − retenciones |

Para mensualizados:
- **Básico** = (30 − días de vacaciones) × sueldo / 30.
- **Vacaciones** = días × sueldo / 25.
- **Antigüedad** = años % × (básico + vacaciones).

Las contribuciones en quincena se calculan sobre el remunerativo del **mes anterior completo**, así que
las dos quincenas muestran el costo del mes (C20). Las fórmulas detalladas están en
[Liquidación](../liquidacion.md).

## 7. Novedades

| Código | Qué es | Unidad | Se carga sola |
|---|---|---|---|
| `HS_NORM` | Horas normales trabajadas | horas | sí: 88 por quincena menos vacaciones, o las fichadas |
| `HS_EXT50` / `HS_EXT100` | Horas extras al 50% / 100% | horas | con fichadas |
| `FERIADO` | Horas de feriado pagas | horas | sí: feriados de lunes a viernes × 8,8 |
| `VAC_DIAS` | Días de vacaciones gozadas | días corridos | sí: licencias aprobadas |
| `PRESENTISMO`, `PREMIO_PROD`, `OBJETIVOS`, `PORTITULO` | Adicionales remunerativos | $ | no |
| `ASIG_NO_REM`, `GRATIF_NO_REM`, `COMPENS_NO_REM` | Sumas no remunerativas | $ | no |
| `CANT_VIANDAS` / `PRECIO_VIANDA` | Descuento de comedor | unidades / $ | no (precio: valor del lote) |
| `APORTE_ADIC_SS` | Aporte adicional de Seguridad Social | $ | sí: ficha, 2° quincena y mensual |
| `DED_SIRADIG` | Deducción mensual de Ganancias (F.572) | $ | sí: ficha |
| `SAC_BASE` / `SAC_DIAS` | Mejor sueldo del semestre / días trabajados | $ / días | no |
| `VAC_NO_GOZ` | Días de vacaciones no gozadas (egreso) | días | no |
| `INDEM_ANTIG`, `INDEM_PREAV`, `INTEG_MES` | Indemnizaciones del despido | $ | no |

**Celda vacía o 0:** el concepto no aparece en el recibo.

**Formato del CSV:** una fila por empleado (legajo, CUIL o nombre) y una columna por código. Ver
[Operación](../operacion.md#importar-novedades).

> **Atención (U1).** Una columna del CSV con un código mal escrito se ignora sin aviso. Controlar en la
> matriz que los valores hayan entrado.
>
> **Atención (C14).** El feriado automático vale 8,8 hs (promedio). Un lunes a jueves son 9 hs: corregir
> `FERIADO` a mano.

## 8. Otras liquidaciones

### 8.1 Vacaciones pagadas al salir (enero y febrero)

1. Aprobar la licencia de vacaciones.
2. Lote de tipo **Vacaciones** con las fechas de la licencia. Cada recibo trae los días y paga:
   - jornal: días × valor hora × 8,8 × 1,20;
   - mensual: días × sueldo / 25.
3. Calcular, revisar, exportar y cerrar.

> **Atención (C1).** La quincena o el mes que contiene esos días **vuelve a pagar las vacaciones**. En
> ese lote, poner en 0 el concepto *Adelanto Vacaciones* / *Licencia por Vacaciones*: dejar `VAC_DIAS`
> para que descuente las horas, y controlar el recibo. **Atención (C13).** Además descuenta 8,8 hs por
> cada día corrido de vacaciones, incluidos sábados y domingos: corregir `HS_NORM` con las horas
> realmente trabajadas.

Mensualizados que toman vacaciones dentro del mes sin lote aparte: el recibo mensual ya paga 30 − días
de básico más los días de vacaciones / 25.

### 8.2 SAC (aguinaldo), junio y diciembre

1. Lote de tipo **SAC** con las fechas del semestre (01/01–30/06 o 01/07–31/12).
2. En cada recibo cargar:
   - **`SAC_BASE`** = la mayor remuneración mensual del semestre (para jornalizados, la suma de las dos
     quincenas del mejor mes);
   - **`SAC_DIAS`**, si no trabajó el semestre entero.
3. El SAC es 50% de la base (× días / 180).

> **Atención (C10).** Sin `SAC_BASE` el sistema usa el sueldo actual o una estimación que deja afuera
> extras, premios y antigüedad: cargarla siempre. Para buscar el mejor mes, filtrar *Liquidaciones del
> empleado* por empleado y mes y sumar *Total Remunerativo*.

### 8.3 Liquidación final

1. Cargar la fecha de fin del contrato.
2. Lote de tipo **Liquidación Final** con el período del último mes o quincena trabajada.
3. Cargar:
   - horas o días trabajados del último período;
   - **`VAC_NO_GOZ`**: vacaciones proporcionales = días del año según antigüedad × días trabajados del
     año / 365;
   - **`SAC_BASE`** y **`SAC_DIAS`** (días del semestre hasta el egreso);
   - las indemnizaciones, calculadas aparte:
     - **antigüedad (Art. 245):** mejor remuneración mensual × años, contando como año la fracción de
       más de 3 meses;
     - **preaviso (Art. 232):** 1 mes, o 2 con más de 5 años;
     - **integración del mes (Art. 233):** remuneración / 30 × días que faltan para fin de mes.

> **Atención (C7, C22, C23).**
> - Hoy el recibo descuenta Obra Social y cuota sindical sobre las indemnizaciones.
> - Paga aportes sobre las vacaciones no gozadas.
> - El SAC proporcional se redondea a 2 decimales de proporción.
>
> Controlar con el estudio contable antes de pagar.

### 8.4 Ganancias

La retención se calcula sola en cada recibo, por el método acumulativo del año: lo ganado, menos lo
descontado, menos lo deducido, contra la escala proporcional al mes. Cada recibo deja su mes en
*Ganancias: Acumuladores*.

- **Empezar a mitad de año:** cargar a mano los acumuladores de los meses anteriores con los datos del
  sistema viejo (bruto, aportes, deducciones, retención).
- **Corregir un recibo puntual:** *Override Retención Ganancias*.

> **Atención (C2).** Con dos liquidaciones en el mismo mes (quincenas, o SAC y mes), el acumulador queda
> sólo con la última. **Atención (C3).** Las sumas no remunerativas no se están gravando. Revisar la
> retención de jornalizados a mano.

## 9. Exportar

Botón **Exportar Reportes Argentina** del lote (o *Imprimir Recibo de Sueldo* en un recibo). Se exportan
los recibos **calculados** (en espera o hechos).

| Archivo | Para qué | Cuidado |
|---|---|---|
| Recibos PDF | Entregar y firmar | Diseño 4 = con base y contribuciones. Revisar nombre y datos del empleador (E4). |
| Libro de Sueldos Digital (TXT) | Subir a ARCA | Un archivo por lote. Conceptos sin código LSD (premios, presentismo) serán rechazados (E2). |
| F.931 (TXT) | SICOSS | **No usar todavía**: se arma por lote y no por mes (E1). |
| Galicia / Santander | Acreditar sueldos | Empleados sin CBU salen con ceros: revisar el archivo (E3). |

## 10. Confirmar, cerrar y corregir

- **Cerrar** el lote confirma los recibos: ya no se recalculan ni se les cargan novedades.
- **Corregir un recibo confirmado:** cancelarlo y volverlo a borrador desde el recibo (según
  permisos), corregir, recalcular y volver a confirmar. Revisar el acumulador de Ganancias de ese mes
  (T2).
- **Pago fuera de término o rectificación:** lote de tipo **Ajustes**.

## 11. Problemas frecuentes

Ver la tabla de [Operación](../operacion.md#problemas-comunes). Los más habituales:

- El recibo no tiene **contrato vigente**.
- **Sueldo en 0.**
- Falta una **alícuota** en la compañía.
- Un empleado **no aparece en la matriz**: *Recargar Novedades del Período* agrega las celdas que
  faltan.

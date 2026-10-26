# Escenarios de prueba

Ocho ejercicios con empleados ficticios para aprender el sistema y controlar que liquide bien. Cubren el
mes de un liquidador:

- dos quincenas de jornalizados y dos meses de mensualizados;
- vacaciones pagadas al salir;
- una liquidación final;
- un SAC;
- Ganancias.

Cada ejercicio dice qué cargar, qué controlar y qué problema conocido se va a ver. Los importes de
todos los recibos, línea por línea, están en [Resultados esperados](resultados.md).

Antes de empezar: la instancia tiene que estar preparada ([Preparar una instancia](preparar-instancia.md))
y conviene haber leído la [Guía de uso](guia.md).

## Los empleados

| Legajo | Empleado | Tipo | Básico | Ingreso | Particularidad |
|---|---|---|---|---|---|
| 9101 | Prueba A - Juan Pérez | Jornal UOM, Oficial | 6.675,34 / h | 01/03/2020 (6 años) | Reproduce los dos **recibos de referencia**. |
| 9102 | Prueba B - Lucas Gómez | Jornal UOM, Medio Oficial | 4.900 / h | 02/05/2024 (2 años) | Horas extras y viandas. |
| 9103 | Prueba C - Martín Sosa | Jornal UOM, Operario | 4.500 / h | 01/02/2023 (3 años) | Vacaciones 07 al 20/09 (14 días). |
| 9104 | Prueba D - Carla Díaz | Mensual UOM, Administrativa 2ª | 1.250.000 | 01/04/2015 (11 años) | Vacaciones 21 al 25/09 (5 días) dentro del mes. |
| 9105 | Prueba E - Roberto Fernández | Mensual, fuera de convenio | 6.500.000 | 01/06/2012 | Supera el tope; **Ganancias** con cónyuge, 2 hijos y F.572. |
| 9106 | Prueba F - Diego Molina | Jornal UOM, Operario | 4.500 / h | 01/02/2021 (5 años) | Despido sin causa el 15/09. |

Bruto remunerativo de julio, del "sistema anterior" (base de contribuciones de agosto):

| A | B | C | F |
|---|---|---|---|
| 3.945.490,21 | 1.020.000 | 930.000 | 880.000 |

## Cómo anotar lo que se encuentra

Por cada diferencia, anotar:

```
Ejercicio / empleado:
Concepto (código):
Esperaba:          (importe y de dónde sale: resultados.md, cuenta a mano, recibo del sistema viejo)
El sistema dio:
¿Coincide con un problema conocido? (id de la revisión, o "no")
Comentario:
```

Las diferencias con los [Resultados esperados](resultados.md) son errores de carga o del sistema. Las
dudas sobre si el resultado esperado es correcto según la ley o el convenio van a
[Preguntas abiertas](../pendientes.md).

---

## Ejercicio 1: 1° Quincena de agosto 2026

**Practica:** crear un lote, generar recibos, valores del lote, matriz de novedades, base de
contribuciones del primer mes.

1. *Procesamiento de liquidaciones › Nuevo*:
   - nombre "Prueba - 1° Quincena Agosto 2026";
   - tipo *1° Quincena*;
   - del 01/08/2026 al 15/08/2026;
   - fecha de pago 19/08/2026.
2. **Generar nóminas** para A, B, C y F.
3. *Novedades › Valores del Lote*: `PRECIO_VIANDA` = 2.500 y **Aplicar a todos**.
4. Matriz:

   | Empleado | Novedad |
   |---|---|
   | A | `PREMIO_PROD` = 548.671,23 |
   | B | `CANT_VIANDAS` = 10 |
   | C | `CANT_VIANDAS` = 8 |
   | F | `CANT_VIANDAS` = 9 |

5. En cada recibo, *Bruto Mes Anterior Manual* = el bruto de julio (tabla de arriba): es el primer mes
   en Odoo.
6. **Recalcular Recibos.**

**Controlar:**
- `HS_NORM` = 88 en todos.
- A: antigüedad 6% de 587.429,92 = 35.245,80; remunerativo **1.171.346,95**.
- B: descuento de viandas 10 × 2.500 = 25.000; neto **329.058,32**.
- Las contribuciones de A se calculan sobre 3.945.490,21 (ART 229.627,53).

## Ejercicio 2: 2° Quincena de agosto 2026

**Practica:** feriado, presentismo como valor del lote, horas extras, no remunerativos, seguro de vida
UOM.

1. Lote *2° Quincena*, del 16/08 al 31/08/2026, pago 04/09/2026, para A, B, C y F.
2. Valores del lote: `PRECIO_VIANDA` = 2.500 y `PRESENTISMO` = 120.000, **Aplicar a todos**.
3. Matriz:

   | Empleado | Novedades |
   |---|---|
   | A | `FERIADO` = 9, `PRESENTISMO` = 394.150,85, `GRATIF_NO_REM` = 30.000, `COMPENS_NO_REM` = 70.000 |
   | B | `HS_EXT50` = 10, `HS_EXT100` = 4, `CANT_VIANDAS` = 11 |
   | C | `CANT_VIANDAS` = 9 |
   | F | `CANT_VIANDAS` = 10 |

4. *Bruto Mes Anterior Manual* otra vez con el bruto de julio.
5. **Recalcular Recibos.**

**Controlar:**
- **A es un recibo de referencia:** remunerativo **1.080.509,31**, retenciones 224.244,97, neto **956.264,34**,
  contribuciones 344.539,47.
- B: antigüedad 2% × (88 + 8,8 + 10 × 1,5 + 4 × 2) × 4.900 = 2% × 587.020 = 11.740,40; extras 73.500 y
  39.200.
- Seguro de vida UOM: −8.045,65 en todos; en la 1° quincena no estaba.

**Problema conocido:**
- **C14.** El feriado automático de B, C y F es 8,8 hs; el 17/08 es lunes y el calendario dice 9. A tiene
  9 porque se corrigió a mano, como en su recibo de referencia.

## Ejercicio 3: Mensual de agosto 2026

**Practica:** mensualizados, tope imponible, Ganancias.

1. Lote *Mensual*, del 01/08 al 31/08/2026, pago 04/09/2026, para D y E.
2. Sin novedades: **Recalcular Recibos.**

**Controlar:**
- D: básico 30 × 41.666,67 = 1.250.000; antigüedad 11% = 137.500; neto **1.108.891,85**.
- E:
  - *Tope Aplicado*: jubilación 11% de 4.250.000 = 467.500, no de 6.500.000;
  - sin cuota sindical ni antigüedad (fuera de convenio);
  - `DED_SIRADIG` = 150.000 (del F.572);
  - Ganancias −1.046.177,88.
- E: en *Ganancias: Acumuladores* aparecen enero a julio (historial) y agosto.

**Problema conocido:**
- **C5.** La escala de Ganancias es de ejemplo: el importe sirve para ver el mecanismo, no como
  retención real.

## Ejercicio 4: Vacaciones de C (pagadas al salir)

**Practica:** lote de vacaciones.

1. Controlar en *Ausencias* que la licencia de C del 07 al 20/09 esté aprobada.
2. Lote *Vacaciones*, del 07/09 al 20/09/2026, pago 04/09/2026, sólo C. **Recalcular.**

**Controlar:**
- `VAC_DIAS` = 14.
- Vacaciones = 14 × 4.500 × 8,8 × 1,20 = 14 × 47.520 = **665.280**.

**Problemas conocidos:**
- **C16.** No tiene antigüedad.
- **C17.** El factor 1,20 está en revisión.

## Ejercicio 5: 1° Quincena de septiembre 2026

**Practica:** base de contribuciones tomada sola del mes anterior; empleado de vacaciones.

1. Lote *1° Quincena*, del 01/09 al 15/09/2026, pago 18/09/2026, para A, B y C.
2. Matriz: A `PREMIO_PROD` = 502.985.
3. Ya **no** hace falta *Bruto Mes Anterior Manual*. **Recalcular.**

**Controlar:**
- **A es el otro recibo de referencia:**
  - la base de contribuciones sale sola de agosto: 1.171.346,95 + 1.080.509,31 = **2.251.856,26**;
  - remunerativo **1.125.660,72**, neto **906.156,88**, contribuciones 192.196,21.
- B: base de contribuciones = su agosto (439.824 + 718.760,40 = 1.158.584,40).

**Problemas conocidos:**
- **C1.** C cobra otra vez 9 días de vacaciones (427.680) que ya cobró en el ejercicio 4. En la vida
  real, poner en 0 *Adelanto Vacaciones* en este recibo.
- **C13.** C tiene `HS_NORM` = 88 − 9 × 8,8 = 8,8 hs. Trabajó del martes 1 al viernes 4: 9 + 9 + 9 +
  8 = 35 hs.

## Ejercicio 6: Mensual de septiembre 2026

**Practica:** vacaciones de un mensualizado dentro del mes.

1. Lote *Mensual*, del 01/09 al 30/09/2026, pago 05/10/2026, para D y E. **Recalcular.**

**Controlar:**
- D tiene `VAC_DIAS` = 5:
  - básico 25 × 41.666,67 = 1.041.666,67;
  - vacaciones 5 × 1.250.000 / 25 = 250.000;
  - antigüedad 11% de 1.291.666,67 = 142.083,33;
  - remunerativo **1.433.750**: más que agosto, porque el día de vacaciones vale sueldo / 25.
- E: Ganancias de septiembre, acumulada con enero a agosto.

## Ejercicio 7: Liquidación final de F

**Practica:** egreso, vacaciones no gozadas, SAC proporcional, indemnizaciones.

Cuentas a mano (mejor remuneración = agosto de F: 415.800 + 577.380 = **993.180**):

| Concepto | Cuenta | Novedad |
|---|---|---|
| Vacaciones no gozadas | 21 días por año (más de 5 años) × 258 días trabajados / 365 = 14,8 → 15 | `VAC_NO_GOZ` = 15 |
| SAC proporcional | 01/07 al 15/09 = 77 días | `SAC_BASE` = 993.180, `SAC_DIAS` = 77 |
| Antigüedad (Art. 245) | 5 años y 7 meses → 6 × 993.180 | `INDEM_ANTIG` = 5.959.080 |
| Preaviso (Art. 232) | más de 5 años → 2 meses | `INDEM_PREAV` = 1.986.360 |
| Integración del mes (Art. 233) | 993.180 / 30 × 15 días | `INTEG_MES` = 496.590 |

1. Lote *Liquidación Final*, del 01/09 al 15/09/2026, pago 18/09/2026, sólo F.
2. Cargar las novedades de la tabla. **Recalcular.**

**Controlar:**
- Básico 88 hs = 396.000.
- Vacaciones no gozadas 15 × 47.520 = 712.800.
- No remunerativo 8.442.030.

**Problemas conocidos:**
- **C23.** SAC proporcional = 496.590 × 0,43 = 213.533,70; con 77 / 180 da 212.430,17. El bruto del
  recibo (1.321.230,17) no coincide con *Total Remunerativo* (1.322.333,70).
- **C7.** Obra Social y cuota sindical se descuentan también sobre las indemnizaciones (base
  9.763.260,17).
- **C22.** Las vacaciones no gozadas pagan aportes.
- **C21.** Falta el SAC sobre preaviso e integración, y el último período sin antigüedad.

## Ejercicio 8: SAC del 2° semestre 2026

**Practica:** lote de SAC y base del aguinaldo.

1. Lote *SAC*, del 01/07 al 31/12/2026, pago 18/12/2026, para A, B, C y D.
2. `SAC_BASE` de cada uno = su mejor mes del semestre en el sistema (agosto). Sumar *Total
   Remunerativo* de sus recibos de agosto:

   | A | B | C | D |
   |---|---|---|---|
   | 2.251.856,26 | 1.158.584,40 | 976.548 | 1.387.500 |

3. **Recalcular.**

**Controlar:**
- SAC = 50% de la base: A 1.125.928,13, B 579.292,20, C 488.274, D 693.750.

**Problema conocido:**
- **C10.** Si `SAC_BASE` queda en 0, el sistema usa una estimación (probarlo en un recibo y comparar).

---

## Para seguir probando

Con los mismos empleados, sin resultados esperados (comparar con una cuenta a mano o con el sistema
anterior):

- **Importación CSV.** Importar la 2° quincena de septiembre de A, B y F desde
  `data/ejemplo_carga_masiva_horas.csv` adaptado (legajos 9101, 9102, 9106).
- **Fichadas.** Con `payroll_arg_attendance`, cargar fichadas de B en *Asistencias* con horas de más
  un sábado, y ver `HS_EXT50` / `HS_EXT100` al recargar (A1, A2).
- **Exportaciones.** Recibos PDF, Libro de Sueldos y bancos de los lotes 1 y 2. Revisar el nombre, el
  CUIT y los códigos de concepto (E2, E3, E4).
- **Recargar.** Cambiar las fechas de un lote en borrador y ver que las horas no cambian hasta
  *Recargar Novedades del Período* (T3).

# Resultados esperados de los escenarios

> Archivo generado por `tools/escenarios.py` (`escribir_resultados`): no editar a mano. Son los importes que calcula el módulo hoy, incluidos los problemas conocidos que la [guía](escenarios.md) señala en cada ejercicio. Cuando un arreglo cambia un importe, este archivo cambia en el mismo PR.

Línea: *Cant.* = horas, días, unidades o coeficiente; *Base* = valor unitario (valor hora, base imponible, monto); *Importe* = lo que suma o resta en el recibo.

## Ejercicio 1: Prueba - 1° Quincena Agosto 2026

Tipo 1° Quincena, del 01/08/2026 al 15/08/2026, pago 19/08/2026.

### Prueba A - Juan Pérez (legajo 9101)

Novedades: `HS_NORM` 88, `PRECIO_VIANDA` 2.500, `PREMIO_PROD` 548.671,23.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 6.675,34 | 100 | 587.429,92 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 587.429,92 | 6 | 35.245,80 |
| `PREMIO_PROD` | Premio Producción | 1 | 548.671,23 | 100 | 548.671,23 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.171.346,95 | 100 | 1.171.346,95 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.171.346,95 | 11 | -128.848,16 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.171.346,95 | 3 | -35.140,41 |
| `RET_OS` | Obra Social (3%) | 1 | 1.171.346,95 | 3 | -35.140,41 |
| `RET_SIND` | Cuota Sindical | 1 | 1.171.346,95 | 2,5 | -29.283,67 |
| `NET` | Sueldo Neto a Cobrar | 1 | 942.934,29 | 100 | 942.934,29 |
| `COMP_ART` | Contribución ART | 1 | 3.945.490,21 | 5,82 | 229.627,53 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 3.938.486,53 | 10,77 | 42.417,50 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 3.945.490,21 | 6 | 35.509,41 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 3.945.490,21 | 4,7 | 18.543,80 |
| `COMP_FNE` | Contribución FNE | 0,1 | 3.945.490,21 | 0,94 | 3.708,76 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 3.938.486,53 | 1,59 | 6.262,19 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 1.171.346,95 · **No remunerativo** 0,00 · **Retenciones** 228.412,65 · **Neto** 942.934,29 · **Contribuciones** 336.493,82 · **Costo** 1.507.840,77

### Prueba B - Lucas Gómez (legajo 9102)

Novedades: `CANT_VIANDAS` 10, `HS_NORM` 88, `PRECIO_VIANDA` 2.500.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.900,00 | 100 | 431.200,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 431.200,00 | 2 | 8.624,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 439.824,00 | 100 | 439.824,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 439.824,00 | 11 | -48.380,64 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 439.824,00 | 3 | -13.194,72 |
| `RET_OS` | Obra Social (3%) | 1 | 439.824,00 | 3 | -13.194,72 |
| `RET_SIND` | Cuota Sindical | 1 | 439.824,00 | 2,5 | -10.995,60 |
| `DESC_VIANDAS` | Descuento Viandas | 10 | 2.500,00 | 100 | -25.000,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 329.058,32 | 100 | 329.058,32 |
| `COMP_ART` | Contribución ART | 1 | 1.020.000,00 | 5,82 | 59.364,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.012.996,32 | 10,77 | 10.909,97 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.020.000,00 | 6 | 9.180,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.020.000,00 | 4,7 | 4.794,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.020.000,00 | 0,94 | 958,80 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.012.996,32 | 1,59 | 1.610,66 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 439.824,00 · **No remunerativo** 0,00 · **Retenciones** 110.765,68 · **Neto** 329.058,32 · **Contribuciones** 87.242,05 · **Costo** 527.066,05

### Prueba C - Martín Sosa (legajo 9103)

Novedades: `CANT_VIANDAS` 8, `HS_NORM` 88, `PRECIO_VIANDA` 2.500.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.500,00 | 100 | 396.000,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 396.000,00 | 3 | 11.880,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 407.880,00 | 100 | 407.880,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 407.880,00 | 11 | -44.866,80 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 407.880,00 | 3 | -12.236,40 |
| `RET_OS` | Obra Social (3%) | 1 | 407.880,00 | 3 | -12.236,40 |
| `RET_SIND` | Cuota Sindical | 1 | 407.880,00 | 2,5 | -10.197,00 |
| `DESC_VIANDAS` | Descuento Viandas | 8 | 2.500,00 | 100 | -20.000,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 308.343,40 | 100 | 308.343,40 |
| `COMP_ART` | Contribución ART | 1 | 930.000,00 | 5,82 | 54.126,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 922.996,32 | 10,77 | 9.940,67 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 930.000,00 | 6 | 8.370,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 930.000,00 | 4,7 | 4.371,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 930.000,00 | 0,94 | 874,20 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 922.996,32 | 1,59 | 1.467,56 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 407.880,00 · **No remunerativo** 0,00 · **Retenciones** 99.536,60 · **Neto** 308.343,40 · **Contribuciones** 79.574,05 · **Costo** 487.454,05

### Prueba F - Diego Molina (legajo 9106)

Novedades: `CANT_VIANDAS` 9, `HS_NORM` 88, `PRECIO_VIANDA` 2.500.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.500,00 | 100 | 396.000,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 396.000,00 | 5 | 19.800,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 415.800,00 | 100 | 415.800,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 415.800,00 | 11 | -45.738,00 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 415.800,00 | 3 | -12.474,00 |
| `RET_OS` | Obra Social (3%) | 1 | 415.800,00 | 3 | -12.474,00 |
| `RET_SIND` | Cuota Sindical | 1 | 415.800,00 | 2,5 | -10.395,00 |
| `DESC_VIANDAS` | Descuento Viandas | 9 | 2.500,00 | 100 | -22.500,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 312.219,00 | 100 | 312.219,00 |
| `COMP_ART` | Contribución ART | 1 | 880.000,00 | 5,82 | 51.216,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 872.996,32 | 10,77 | 9.402,17 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 880.000,00 | 6 | 7.920,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 880.000,00 | 4,7 | 4.136,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 880.000,00 | 0,94 | 827,20 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 872.996,32 | 1,59 | 1.388,06 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 415.800,00 · **No remunerativo** 0,00 · **Retenciones** 103.581,00 · **Neto** 312.219,00 · **Contribuciones** 75.314,05 · **Costo** 491.114,05

## Ejercicio 2: Prueba - 2° Quincena Agosto 2026

Tipo 2° Quincena, del 16/08/2026 al 31/08/2026, pago 04/09/2026.

### Prueba A - Juan Pérez (legajo 9101)

Novedades: `COMPENS_NO_REM` 70.000, `FERIADO` 9, `GRATIF_NO_REM` 30.000, `HS_NORM` 88, `PRECIO_VIANDA` 2.500, `PRESENTISMO` 394.150,85.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 6.675,34 | 100 | 587.429,92 |
| `FERIADO` | Feriados | 9 | 6.675,34 | 100 | 60.078,06 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 647.507,98 | 6 | 38.850,48 |
| `PRESENTISMO` | Presentismo | 1 | 394.150,85 | 100 | 394.150,85 |
| `GRATIF_NO_REM` | Gratif. Extraordinaria No Rem. | 1 | 30.000,00 | 100 | 30.000,00 |
| `COMPENS_NO_REM` | Compens. Extraord. NR | 1 | 70.000,00 | 100 | 70.000,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.080.509,31 | 100 | 1.080.509,31 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.080.509,31 | 11 | -118.856,02 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.080.509,31 | 3 | -32.415,28 |
| `RET_OS` | Obra Social (3%) | 1 | 1.180.509,31 | 3 | -35.415,28 |
| `RET_SIND` | Cuota Sindical | 1 | 1.180.509,31 | 2,5 | -29.512,73 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `NET` | Sueldo Neto a Cobrar | 1 | 956.264,34 | 100 | 956.264,34 |
| `COMP_ART` | Contribución ART | 1 | 3.945.490,21 | 5,82 | 229.627,53 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 3.938.486,53 | 10,77 | 42.417,50 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 3.945.490,21 | 6 | 35.509,41 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 3.945.490,21 | 4,7 | 18.543,80 |
| `COMP_FNE` | Contribución FNE | 0,1 | 3.945.490,21 | 0,94 | 3.708,76 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 3.938.486,53 | 1,59 | 6.262,19 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 1.080.509,31 · **No remunerativo** 100.000,00 · **Retenciones** 224.244,97 · **Neto** 956.264,34 · **Contribuciones** 344.539,47 · **Costo** 1.525.048,78

### Prueba B - Lucas Gómez (legajo 9102)

Novedades: `CANT_VIANDAS` 11, `FERIADO` 8,8, `HS_EXT100` 4, `HS_EXT50` 10, `HS_NORM` 88, `PRECIO_VIANDA` 2.500, `PRESENTISMO` 120.000.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.900,00 | 100 | 431.200,00 |
| `FERIADO` | Feriados | 8,8 | 4.900,00 | 100 | 43.120,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 587.020,00 | 2 | 11.740,40 |
| `HS_EXT_50` | Horas Extras 50% | 10 | 7.350,00 | 100 | 73.500,00 |
| `PRESENTISMO` | Presentismo | 1 | 120.000,00 | 100 | 120.000,00 |
| `HS_EXT_100` | Horas Extras 100% | 4 | 9.800,00 | 100 | 39.200,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 718.760,40 | 100 | 718.760,40 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 718.760,40 | 11 | -79.063,64 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 718.760,40 | 3 | -21.562,81 |
| `RET_OS` | Obra Social (3%) | 1 | 718.760,40 | 3 | -21.562,81 |
| `RET_SIND` | Cuota Sindical | 1 | 718.760,40 | 2,5 | -17.969,01 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `DESC_VIANDAS` | Descuento Viandas | 11 | 2.500,00 | 100 | -27.500,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 543.056,47 | 100 | 543.056,47 |
| `COMP_ART` | Contribución ART | 1 | 1.020.000,00 | 5,82 | 59.364,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.012.996,32 | 10,77 | 10.909,97 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.020.000,00 | 6 | 9.180,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.020.000,00 | 4,7 | 4.794,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.020.000,00 | 0,94 | 958,80 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.012.996,32 | 1,59 | 1.610,66 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 718.760,40 · **No remunerativo** 0,00 · **Retenciones** 175.703,93 · **Neto** 543.056,47 · **Contribuciones** 95.287,70 · **Costo** 814.048,10

### Prueba C - Martín Sosa (legajo 9103)

Novedades: `CANT_VIANDAS` 9, `FERIADO` 8,8, `HS_NORM` 88, `PRECIO_VIANDA` 2.500, `PRESENTISMO` 120.000.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.500,00 | 100 | 396.000,00 |
| `FERIADO` | Feriados | 8,8 | 4.500,00 | 100 | 39.600,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 435.600,00 | 3 | 13.068,00 |
| `PRESENTISMO` | Presentismo | 1 | 120.000,00 | 100 | 120.000,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 568.668,00 | 100 | 568.668,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 568.668,00 | 11 | -62.553,48 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 568.668,00 | 3 | -17.060,04 |
| `RET_OS` | Obra Social (3%) | 1 | 568.668,00 | 3 | -17.060,04 |
| `RET_SIND` | Cuota Sindical | 1 | 568.668,00 | 2,5 | -14.216,70 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `DESC_VIANDAS` | Descuento Viandas | 9 | 2.500,00 | 100 | -22.500,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 427.232,09 | 100 | 427.232,09 |
| `COMP_ART` | Contribución ART | 1 | 930.000,00 | 5,82 | 54.126,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 922.996,32 | 10,77 | 9.940,67 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 930.000,00 | 6 | 8.370,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 930.000,00 | 4,7 | 4.371,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 930.000,00 | 0,94 | 874,20 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 922.996,32 | 1,59 | 1.467,56 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 568.668,00 · **No remunerativo** 0,00 · **Retenciones** 141.435,91 · **Neto** 427.232,09 · **Contribuciones** 87.619,70 · **Costo** 656.287,70

### Prueba F - Diego Molina (legajo 9106)

Novedades: `CANT_VIANDAS` 10, `FERIADO` 8,8, `HS_NORM` 88, `PRECIO_VIANDA` 2.500, `PRESENTISMO` 120.000.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.500,00 | 100 | 396.000,00 |
| `FERIADO` | Feriados | 8,8 | 4.500,00 | 100 | 39.600,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 435.600,00 | 5 | 21.780,00 |
| `PRESENTISMO` | Presentismo | 1 | 120.000,00 | 100 | 120.000,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 577.380,00 | 100 | 577.380,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 577.380,00 | 11 | -63.511,80 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 577.380,00 | 3 | -17.321,40 |
| `RET_OS` | Obra Social (3%) | 1 | 577.380,00 | 3 | -17.321,40 |
| `RET_SIND` | Cuota Sindical | 1 | 577.380,00 | 2,5 | -14.434,50 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `DESC_VIANDAS` | Descuento Viandas | 10 | 2.500,00 | 100 | -25.000,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 431.745,25 | 100 | 431.745,25 |
| `COMP_ART` | Contribución ART | 1 | 880.000,00 | 5,82 | 51.216,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 872.996,32 | 10,77 | 9.402,17 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 880.000,00 | 6 | 7.920,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 880.000,00 | 4,7 | 4.136,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 880.000,00 | 0,94 | 827,20 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 872.996,32 | 1,59 | 1.388,06 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 577.380,00 · **No remunerativo** 0,00 · **Retenciones** 145.634,75 · **Neto** 431.745,25 · **Contribuciones** 83.359,70 · **Costo** 660.739,70

## Ejercicio 3: Prueba - Mensual Agosto 2026

Tipo Mensual, del 01/08/2026 al 31/08/2026, pago 04/09/2026.

### Prueba D - Carla Díaz (legajo 9104)

Novedades: ninguna.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_MENSUAL` | Sueldo Básico Mensual | 30 | 41.666,67 | 100 | 1.250.000,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 1.250.000,00 | 11 | 137.500,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.387.500,00 | 100 | 1.387.500,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.387.500,00 | 11 | -152.625,00 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.387.500,00 | 3 | -41.625,00 |
| `RET_OS` | Obra Social (3%) | 1 | 1.387.500,00 | 3 | -41.625,00 |
| `RET_SIND` | Cuota Sindical | 1 | 1.387.500,00 | 2,5 | -34.687,50 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `NET` | Sueldo Neto a Cobrar | 1 | 1.108.891,85 | 100 | 1.108.891,85 |
| `COMP_ART` | Contribución ART | 1 | 1.387.500,00 | 5,82 | 80.752,50 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.380.496,32 | 10,77 | 14.867,95 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.387.500,00 | 6 | 12.487,50 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.387.500,00 | 4,7 | 6.521,25 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.387.500,00 | 0,94 | 1.304,25 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.380.496,32 | 1,59 | 2.194,99 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 1.387.500,00 · **No remunerativo** 0,00 · **Retenciones** 278.608,15 · **Neto** 1.108.891,85 · **Contribuciones** 126.598,70 · **Costo** 1.514.098,71

### Prueba E - Roberto Fernández (legajo 9105)

Novedades: `DED_SIRADIG` 150.000.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_MENSUAL` | Sueldo Básico Mensual | 30 | 216.666,67 | 100 | 6.500.000,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 6.500.000,00 | 100 | 6.500.000,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 4.250.000,00 | 11 | -467.500,00 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 4.250.000,00 | 3 | -127.500,00 |
| `RET_OS` | Obra Social (3%) | 1 | 4.250.000,00 | 3 | -127.500,00 |
| `RET_GANANCIAS` | Retención Ganancias (4ta Cat.) | 1 | 1.046.177,88 | 100 | -1.046.177,88 |
| `NET` | Sueldo Neto a Cobrar | 1 | 4.731.322,12 | 100 | 4.731.322,12 |
| `COMP_ART` | Contribución ART | 1 | 6.500.000,00 | 5,82 | 378.300,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 6.492.996,32 | 10,77 | 69.929,57 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 6.500.000,00 | 6 | 58.500,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 6.500.000,00 | 4,7 | 30.550,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 6.500.000,00 | 0,94 | 6.110,00 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 6.492.996,32 | 1,59 | 10.323,86 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 6.500.000,00 · **No remunerativo** 0,00 · **Retenciones** 1.768.677,88 · **Neto** 4.731.322,12 · **Contribuciones** 554.138,05 · **Costo** 7.054.138,06

## Ejercicio 4: Prueba - Vacaciones Septiembre 2026

Tipo Vacaciones, del 07/09/2026 al 20/09/2026, pago 04/09/2026.

### Prueba C - Martín Sosa (legajo 9103)

Novedades: `VAC_DIAS` 14.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `VACACIONES` | Adelanto Vacaciones | 14 | 47.520,00 | 100 | 665.280,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 665.280,00 | 100 | 665.280,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 665.280,00 | 11 | -73.180,80 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 665.280,00 | 3 | -19.958,40 |
| `RET_OS` | Obra Social (3%) | 1 | 665.280,00 | 3 | -19.958,40 |
| `RET_SIND` | Cuota Sindical | 1 | 665.280,00 | 2,5 | -16.632,00 |
| `NET` | Sueldo Neto a Cobrar | 1 | 535.550,40 | 100 | 535.550,40 |
| `COMP_ART` | Contribución ART | 1 | 665.280,00 | 5,82 | 38.719,30 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 658.276,32 | 10,77 | 7.089,64 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 665.280,00 | 6 | 5.987,52 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 665.280,00 | 4,7 | 3.126,82 |
| `COMP_FNE` | Contribución FNE | 0,1 | 665.280,00 | 0,94 | 625,36 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 658.276,32 | 1,59 | 1.046,66 |

**Remunerativo** 665.280,00 · **No remunerativo** 0,00 · **Retenciones** 129.729,60 · **Neto** 535.550,40 · **Contribuciones** 56.595,29 · **Costo** 721.875,29

## Ejercicio 5: Prueba - 1° Quincena Septiembre 2026

Tipo 1° Quincena, del 01/09/2026 al 15/09/2026, pago 18/09/2026.

### Prueba A - Juan Pérez (legajo 9101)

Novedades: `HS_NORM` 88, `PREMIO_PROD` 502.985.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 6.675,34 | 100 | 587.429,92 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 587.429,92 | 6 | 35.245,80 |
| `PREMIO_PROD` | Premio Producción | 1 | 502.985,00 | 100 | 502.985,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.125.660,72 | 100 | 1.125.660,72 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.125.660,72 | 11 | -123.822,68 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.125.660,72 | 3 | -33.769,82 |
| `RET_OS` | Obra Social (3%) | 1 | 1.125.660,72 | 3 | -33.769,82 |
| `RET_SIND` | Cuota Sindical | 1 | 1.125.660,72 | 2,5 | -28.141,52 |
| `NET` | Sueldo Neto a Cobrar | 1 | 906.156,88 | 100 | 906.156,88 |
| `COMP_ART` | Contribución ART | 1 | 2.251.856,26 | 5,82 | 131.058,03 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 2.244.852,58 | 10,77 | 24.177,06 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 2.251.856,26 | 6 | 20.266,71 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 2.251.856,26 | 4,7 | 10.583,72 |
| `COMP_FNE` | Contribución FNE | 0,1 | 2.251.856,26 | 0,94 | 2.116,74 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 2.244.852,58 | 1,59 | 3.569,32 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 1.125.660,72 · **No remunerativo** 0,00 · **Retenciones** 219.503,84 · **Neto** 906.156,88 · **Contribuciones** 192.196,21 · **Costo** 1.317.856,92

### Prueba B - Lucas Gómez (legajo 9102)

Novedades: `HS_NORM` 88.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.900,00 | 100 | 431.200,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 431.200,00 | 2 | 8.624,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 439.824,00 | 100 | 439.824,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 439.824,00 | 11 | -48.380,64 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 439.824,00 | 3 | -13.194,72 |
| `RET_OS` | Obra Social (3%) | 1 | 439.824,00 | 3 | -13.194,72 |
| `RET_SIND` | Cuota Sindical | 1 | 439.824,00 | 2,5 | -10.995,60 |
| `NET` | Sueldo Neto a Cobrar | 1 | 354.058,32 | 100 | 354.058,32 |
| `COMP_ART` | Contribución ART | 1 | 1.158.584,40 | 5,82 | 67.429,61 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.151.580,72 | 10,77 | 12.402,52 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.158.584,40 | 6 | 10.427,26 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.158.584,40 | 4,7 | 5.445,35 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.158.584,40 | 0,94 | 1.089,07 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.151.580,72 | 1,59 | 1.831,01 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 439.824,00 · **No remunerativo** 0,00 · **Retenciones** 85.765,68 · **Neto** 354.058,32 · **Contribuciones** 99.049,45 · **Costo** 538.873,45

### Prueba C - Martín Sosa (legajo 9103)

Novedades: `HS_NORM` 8,8, `VAC_DIAS` 9.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 8,8 | 4.500,00 | 100 | 39.600,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 39.600,00 | 3 | 1.188,00 |
| `VACACIONES` | Adelanto Vacaciones | 9 | 47.520,00 | 100 | 427.680,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 468.468,00 | 100 | 468.468,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 468.468,00 | 11 | -51.531,48 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 468.468,00 | 3 | -14.054,04 |
| `RET_OS` | Obra Social (3%) | 1 | 468.468,00 | 3 | -14.054,04 |
| `RET_SIND` | Cuota Sindical | 1 | 468.468,00 | 2,5 | -11.711,70 |
| `NET` | Sueldo Neto a Cobrar | 1 | 377.116,74 | 100 | 377.116,74 |
| `COMP_ART` | Contribución ART | 1 | 976.548,00 | 5,82 | 56.835,09 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 969.544,32 | 10,77 | 10.441,99 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 976.548,00 | 6 | 8.788,93 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 976.548,00 | 4,7 | 4.589,78 |
| `COMP_FNE` | Contribución FNE | 0,1 | 976.548,00 | 0,94 | 917,96 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 969.544,32 | 1,59 | 1.541,58 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 468.468,00 · **No remunerativo** 0,00 · **Retenciones** 91.351,26 · **Neto** 377.116,74 · **Contribuciones** 83.539,94 · **Costo** 552.007,94

## Ejercicio 6: Prueba - Mensual Septiembre 2026

Tipo Mensual, del 01/09/2026 al 30/09/2026, pago 05/10/2026.

### Prueba D - Carla Díaz (legajo 9104)

Novedades: `VAC_DIAS` 5.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_MENSUAL` | Sueldo Básico Mensual | 25 | 41.666,67 | 100 | 1.041.666,67 |
| `VACACIONES_MENSUAL` | Licencia por Vacaciones | 5 | 50.000,00 | 100 | 250.000,00 |
| `ADIC_ANTIG` | Adicional Antigüedad | 1 | 1.291.666,67 | 11 | 142.083,33 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.433.750,00 | 100 | 1.433.750,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.433.750,00 | 11 | -157.712,50 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.433.750,00 | 3 | -43.012,50 |
| `RET_OS` | Obra Social (3%) | 1 | 1.433.750,00 | 3 | -43.012,50 |
| `RET_SIND` | Cuota Sindical | 1 | 1.433.750,00 | 2,5 | -35.843,75 |
| `RET_UOM_VIDA` | Seg. de Vida UOM | 1 | 8.045,65 | 100 | -8.045,65 |
| `NET` | Sueldo Neto a Cobrar | 1 | 1.146.123,10 | 100 | 1.146.123,10 |
| `COMP_ART` | Contribución ART | 1 | 1.433.750,00 | 5,82 | 83.444,25 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.426.746,32 | 10,77 | 15.366,06 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.433.750,00 | 6 | 12.903,75 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.433.750,00 | 4,7 | 6.738,63 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.433.750,00 | 0,94 | 1.347,73 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.426.746,32 | 1,59 | 2.268,53 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |
| `COMP_UOM_VIDA` | Contr.Seguro de Vida UOM | 1 | 8.045,65 | 100 | 8.045,65 |

**Remunerativo** 1.433.750,00 · **No remunerativo** 0,00 · **Retenciones** 287.626,90 · **Neto** 1.146.123,10 · **Contribuciones** 130.539,20 · **Costo** 1.564.289,21

### Prueba E - Roberto Fernández (legajo 9105)

Novedades: `DED_SIRADIG` 150.000.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_MENSUAL` | Sueldo Básico Mensual | 30 | 216.666,67 | 100 | 6.500.000,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 6.500.000,00 | 100 | 6.500.000,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 4.250.000,00 | 11 | -467.500,00 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 4.250.000,00 | 3 | -127.500,00 |
| `RET_OS` | Obra Social (3%) | 1 | 4.250.000,00 | 3 | -127.500,00 |
| `RET_GANANCIAS` | Retención Ganancias (4ta Cat.) | 1 | 1.046.177,88 | 100 | -1.046.177,88 |
| `NET` | Sueldo Neto a Cobrar | 1 | 4.731.322,12 | 100 | 4.731.322,12 |
| `COMP_ART` | Contribución ART | 1 | 6.500.000,00 | 5,82 | 378.300,00 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 6.492.996,32 | 10,77 | 69.929,57 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 6.500.000,00 | 6 | 58.500,00 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 6.500.000,00 | 4,7 | 30.550,00 |
| `COMP_FNE` | Contribución FNE | 0,1 | 6.500.000,00 | 0,94 | 6.110,00 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 6.492.996,32 | 1,59 | 10.323,86 |
| `COMP_SCVO` | Contribución SCVO Seg de vida | 1 | 424,62 | 100 | 424,62 |

**Remunerativo** 6.500.000,00 · **No remunerativo** 0,00 · **Retenciones** 1.768.677,88 · **Neto** 4.731.322,12 · **Contribuciones** 554.138,05 · **Costo** 7.054.138,06

## Ejercicio 7: Prueba - Liquidación Final Diego Molina

Tipo Liquidación Final, del 01/09/2026 al 15/09/2026, pago 18/09/2026.

### Prueba F - Diego Molina (legajo 9106)

Novedades: `HS_NORM` 88, `INDEM_ANTIG` 5.959.080, `INDEM_PREAV` 1.986.360, `INTEG_MES` 496.590, `SAC_BASE` 993.180, `SAC_DIAS` 77, `VAC_NO_GOZ` 15.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `BASIC_HORAS` | Básico Horas Trabajadas | 88 | 4.500,00 | 100 | 396.000,00 |
| `VAC_NO_GOZ_JORNAL` | Vacaciones No Gozadas Jornal (Art. 156 LCT) | 15 | 47.520,00 | 100 | 712.800,00 |
| `SAC_PROP_JORNAL` | SAC Proporcional al Egreso Jornal | 0,43 | 496.590,00 | 100 | 213.533,70 |
| `INDEM_ANTIGUEDAD` | Indemnización por Antigüedad (Art. 245 LCT) | 1 | 5.959.080,00 | 100 | 5.959.080,00 |
| `INDEM_PREAVISO` | Indemnización Sustitutiva Preaviso (Art. 232 LCT) | 1 | 1.986.360,00 | 100 | 1.986.360,00 |
| `INTEG_MES_DESPIDO` | Integración Mes de Despido (Art. 233 LCT) | 1 | 496.590,00 | 100 | 496.590,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.321.230,17 | 100 | 1.321.230,17 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.321.230,17 | 11 | -145.335,32 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.321.230,17 | 3 | -39.636,91 |
| `RET_OS` | Obra Social (3%) | 1 | 9.763.260,17 | 3 | -292.897,81 |
| `RET_SIND` | Cuota Sindical | 1 | 9.763.260,17 | 2,5 | -244.081,50 |
| `NET` | Sueldo Neto a Cobrar | 1 | 9.041.308,63 | 100 | 9.041.308,63 |
| `COMP_ART` | Contribución ART | 1 | 1.321.230,17 | 5,82 | 76.895,60 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.314.226,49 | 10,77 | 14.154,22 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.321.230,17 | 6 | 11.891,07 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.321.230,17 | 4,7 | 6.209,78 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.321.230,17 | 0,94 | 1.241,96 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.314.226,49 | 1,59 | 2.089,62 |

**Remunerativo** 1.322.333,70 · **No remunerativo** 8.442.030,00 · **Retenciones** 721.951,53 · **Neto** 9.042.412,17 · **Contribuciones** 112.482,24 · **Costo** 9.876.845,94

## Ejercicio 8: Prueba - SAC 2° Semestre 2026

Tipo SAC, del 01/07/2026 al 31/12/2026, pago 18/12/2026.

### Prueba A - Juan Pérez (legajo 9101)

Novedades: `SAC_BASE` 2.251.856,26.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `SAC_JORNAL` | Sueldo Anual Complementario (SAC) Jornal | 1 | 1.125.928,13 | 100 | 1.125.928,13 |
| `GROSS` | Total Bruto Remunerativo | 1 | 1.125.928,13 | 100 | 1.125.928,13 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 1.125.928,13 | 11 | -123.852,09 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 1.125.928,13 | 3 | -33.777,84 |
| `RET_OS` | Obra Social (3%) | 1 | 1.125.928,13 | 3 | -33.777,84 |
| `RET_SIND` | Cuota Sindical | 1 | 1.125.928,13 | 2,5 | -28.148,20 |
| `NET` | Sueldo Neto a Cobrar | 1 | 906.372,14 | 100 | 906.372,14 |
| `COMP_ART` | Contribución ART | 1 | 1.125.928,13 | 5,82 | 65.529,02 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 1.118.924,45 | 10,77 | 12.050,82 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 1.125.928,13 | 6 | 10.133,35 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 1.125.928,13 | 4,7 | 5.291,86 |
| `COMP_FNE` | Contribución FNE | 0,1 | 1.125.928,13 | 0,94 | 1.058,37 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 1.118.924,45 | 1,59 | 1.779,09 |

**Remunerativo** 1.125.928,13 · **No remunerativo** 0,00 · **Retenciones** 219.555,99 · **Neto** 906.372,14 · **Contribuciones** 95.842,51 · **Costo** 1.221.770,64

### Prueba B - Lucas Gómez (legajo 9102)

Novedades: `SAC_BASE` 1.158.584,4.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `SAC_JORNAL` | Sueldo Anual Complementario (SAC) Jornal | 1 | 579.292,20 | 100 | 579.292,20 |
| `GROSS` | Total Bruto Remunerativo | 1 | 579.292,20 | 100 | 579.292,20 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 579.292,20 | 11 | -63.722,14 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 579.292,20 | 3 | -17.378,77 |
| `RET_OS` | Obra Social (3%) | 1 | 579.292,20 | 3 | -17.378,77 |
| `RET_SIND` | Cuota Sindical | 1 | 579.292,20 | 2,5 | -14.482,31 |
| `NET` | Sueldo Neto a Cobrar | 1 | 466.330,22 | 100 | 466.330,22 |
| `COMP_ART` | Contribución ART | 1 | 579.292,20 | 5,82 | 33.714,81 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 572.288,52 | 10,77 | 6.163,55 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 579.292,20 | 6 | 5.213,63 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 579.292,20 | 4,7 | 2.722,67 |
| `COMP_FNE` | Contribución FNE | 0,1 | 579.292,20 | 0,94 | 544,53 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 572.288,52 | 1,59 | 909,94 |

**Remunerativo** 579.292,20 · **No remunerativo** 0,00 · **Retenciones** 112.961,98 · **Neto** 466.330,22 · **Contribuciones** 49.269,13 · **Costo** 628.561,33

### Prueba C - Martín Sosa (legajo 9103)

Novedades: `SAC_BASE` 976.548.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `SAC_JORNAL` | Sueldo Anual Complementario (SAC) Jornal | 1 | 488.274,00 | 100 | 488.274,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 488.274,00 | 100 | 488.274,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 488.274,00 | 11 | -53.710,14 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 488.274,00 | 3 | -14.648,22 |
| `RET_OS` | Obra Social (3%) | 1 | 488.274,00 | 3 | -14.648,22 |
| `RET_SIND` | Cuota Sindical | 1 | 488.274,00 | 2,5 | -12.206,85 |
| `NET` | Sueldo Neto a Cobrar | 1 | 393.060,57 | 100 | 393.060,57 |
| `COMP_ART` | Contribución ART | 1 | 488.274,00 | 5,82 | 28.417,55 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 481.270,32 | 10,77 | 5.183,28 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 488.274,00 | 6 | 4.394,47 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 488.274,00 | 4,7 | 2.294,89 |
| `COMP_FNE` | Contribución FNE | 0,1 | 488.274,00 | 0,94 | 458,98 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 481.270,32 | 1,59 | 765,22 |

**Remunerativo** 488.274,00 · **No remunerativo** 0,00 · **Retenciones** 95.213,43 · **Neto** 393.060,57 · **Contribuciones** 41.514,38 · **Costo** 529.788,38

### Prueba D - Carla Díaz (legajo 9104)

Novedades: `SAC_BASE` 1.387.500.

| Código | Concepto | Cant. | Base | % | Importe |
|---|---|---|---|---|---|
| `SAC_MENSUAL` | Sueldo Anual Complementario (SAC) | 1 | 693.750,00 | 100 | 693.750,00 |
| `GROSS` | Total Bruto Remunerativo | 1 | 693.750,00 | 100 | 693.750,00 |
| `RET_JUB` | Jubilación (SIPA 11%) | 1 | 693.750,00 | 11 | -76.312,50 |
| `RET_INSSJP` | Ley 19.032 (INSSJyP 3%) | 1 | 693.750,00 | 3 | -20.812,50 |
| `RET_OS` | Obra Social (3%) | 1 | 693.750,00 | 3 | -20.812,50 |
| `RET_SIND` | Cuota Sindical | 1 | 693.750,00 | 2,5 | -17.343,75 |
| `NET` | Sueldo Neto a Cobrar | 1 | 558.468,75 | 100 | 558.468,75 |
| `COMP_ART` | Contribución ART | 1 | 693.750,00 | 5,82 | 40.376,25 |
| `COMP_JUB` | Contribución Jubilación | 0,1 | 686.746,32 | 10,77 | 7.396,26 |
| `COMP_OS` | Contribución Obra Social | 0,15 | 693.750,00 | 6 | 6.243,75 |
| `COMP_AAFF` | Contribución AAFF | 0,1 | 693.750,00 | 4,7 | 3.260,63 |
| `COMP_FNE` | Contribución FNE | 0,1 | 693.750,00 | 0,94 | 652,13 |
| `COMP_INSSJP` | Contribución Ley 19032 | 0,1 | 686.746,32 | 1,59 | 1.091,93 |

**Remunerativo** 693.750,00 · **No remunerativo** 0,00 · **Retenciones** 135.281,25 · **Neto** 558.468,75 · **Contribuciones** 59.020,93 · **Costo** 752.770,93

## Acumuladores de Ganancias de E

| Mes | Bruto | Aportes | SIRADIG | Ganancia neta acum. | Impuesto acum. | Retención |
|---|---|---|---|---|---|---|
| 01/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 3.646.222,50 | 1.046.177,88 | 1.046.177,88 |
| 02/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 7.292.445,00 | 2.092.355,75 | 1.046.177,87 |
| 03/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 10.938.667,50 | 3.138.533,62 | 1.046.177,87 |
| 04/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 14.584.890,00 | 4.184.711,50 | 1.046.177,88 |
| 05/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 18.231.112,50 | 5.230.889,38 | 1.046.177,88 |
| 06/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 21.877.335,00 | 6.277.067,25 | 1.046.177,87 |
| 07/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 25.523.557,50 | 7.323.245,12 | 1.046.177,87 |
| 08/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 29.169.780,00 | 8.369.423,00 | 1.046.177,88 |
| 09/2026 | 6.500.000,00 | 722.500,00 | 150.000,00 | 32.816.002,50 | 9.415.600,88 | 1.046.177,88 |

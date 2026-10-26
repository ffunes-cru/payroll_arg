# Nómina Argentina (Odoo 19)

Liquidación de sueldos argentina sobre el módulo `payroll` de OCA:

- **Jornalizados UOM** (valor hora, quincenas) y **mensualizados**, con estructuras para Vacaciones,
  SAC y Liquidación Final.
- **Novedades** del período cargadas solas: calendario, feriados, vacaciones aprobadas y, con
  `payroll_arg_attendance`, fichadas. Se corrigen en una matriz por lote o por CSV.
- **Aportes y contribuciones** con tope imponible, detracción y coeficientes; ART y seguros de vida.
- **Ganancias 4ta categoría** por el método acumulativo, con escalas e importación del F.572 (SIRADIG).
- **Exportaciones:** recibo PDF, Libro de Sueldos Digital, F.931 (SICOSS), acreditaciones Galicia y
  Santander (librería `py_arg_reports`, submódulo `payroll_arg_reportes`).

**Autor:** Franco Funes · **Licencia:** [AGPL-3](LICENSE) ·
**Depende de:** `payroll` (OCA), `hr_holidays`, `resource`, `web_widget_x2many_2d_matrix` ·
**Complemento:** `payroll_arg_attendance` (horas desde fichadas).

> **Antes de liquidar en producción** leer la [revisión de octubre de 2026](docs/revision.md). Tiene
> problemas de gravedad alta: vacaciones pagadas dos veces, Ganancias en quincenas, indemnizaciones con
> aportes, F.931 y archivos bancarios.

## Documentación

**Sitio web:** <https://ffunes-cru.github.io/payroll_arg/> (se publica solo con cada cambio en `main`).

Leer en este orden. Los diagramas son [Mermaid](https://mermaid.js.org/): GitHub, GitLab, VS Code (con
*Markdown Preview Mermaid Support*) y el HTML de Doxygen los dibujan solos.

| Documento | Para qué |
|---|---|
| [Conceptos](docs/conceptos.md) | El negocio, jornalizados vs. mensualizados, glosario y un recibo de referencia paso a paso. Empezar acá. |
| [Liquidación](docs/liquidacion.md) | Cómo se calcula cada concepto, con su norma: haberes, retenciones, contribuciones, Ganancias, SAC, vacaciones, final. |
| [Flujos](docs/flujos.md) | El mes del liquidador, el lote paso a paso, de dónde sale cada novedad, vacaciones, SAC, final, Ganancias y exportaciones. |
| [Arquitectura](docs/arquitectura.md) | Qué hace cada archivo, cómo se calcula un recibo, decisiones de diseño y puntos de extensión. |
| [Conceptos de Odoo](docs/odoo.md) | Las piezas de Odoo y de `payroll` (OCA) que usa el módulo. |
| [Operación](docs/operacion.md) | Puesta en marcha, parámetros de la compañía, importar novedades, comandos y problemas comunes. |
| [Recetas](docs/recetas.md) | Agregar un concepto, una novedad o un parámetro, cambiar una fórmula y cómo documentar el código. |
| [Revisión](docs/revision.md) | Revisión de código y legal: errores de cálculo, exportaciones y usabilidad, con gravedad y propuesta. |
| [Decisiones](docs/decisiones.md) | Decisiones de negocio confirmadas (D1, D2…). |
| [Preguntas abiertas](docs/pendientes.md) | Lo que falta decidir con el liquidador y el estudio (P1, P2…), con ejemplo y opciones. |
| [Documentación de usuario](docs/usuario/README.md) | Guía de uso, escenarios de prueba con resultados esperados y cómo preparar una instancia de prueba. |
| [Referencia](docs/referencia.md) | **Generada** desde Odoo: estructuras, reglas con su código, novedades, modelos, campos, permisos y quién llama a cada método. |
| Código (Doxygen) | Cada clase y función documentada, con la lista de bugs conocidos. HTML: `doxygen docs/Doxyfile` → `docs/api/html/index.html`. |

## Inicio rápido

```bash
# Clonar con el submódulo de reportes
git clone --recurse-submodules <url> addons/payroll_arg

# Instalar o actualizar (y reiniciar el servidor)
.venv/bin/python odoo-bin -d <base> -u payroll_arg,payroll_arg_attendance --stop-after-init

# Tests, en una base de prueba
.venv/bin/python odoo-bin -d <base_de_prueba> -u payroll_arg,payroll_arg_attendance \
    --test-tags /payroll_arg,/payroll_arg_attendance --stop-after-init --http-port=8092
```

Después de instalar: completar los parámetros de la compañía, convenios, categorías, feriados y la
escala de Ganancias (ver [Operación](docs/operacion.md#puesta-en-marcha)).

## Licencia

Copyright © 2026 Franco Funes. Software libre bajo la [GNU Affero General Public License v3](LICENSE): se
puede usar, estudiar, modificar y redistribuir; las versiones modificadas, incluso las que se ofrecen como
servicio web, tienen que publicar su código con la misma licencia.

La librería `py_arg_reports` (submódulo `payroll_arg_reportes`) es de Artimezoft, bajo licencia MIT
(ver su `LICENSE`); la MIT es compatible con la AGPL.


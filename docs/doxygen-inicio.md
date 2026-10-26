# Nómina Argentina: código {#mainpage}

Documentación del código de `payroll_arg` y `payroll_arg_attendance`, generada de los docstrings: cada
clase, función y parámetro, con la regla de negocio que aplica y la norma en que se apoya. La
documentación funcional y técnica (conceptos, liquidación, flujos, seguridad, guía de usuario) está en el
sitio: <https://ffunes-cru.github.io/payroll_arg/>.

## Cómo navegar

- **Panel izquierdo:** *Clases* (por modelo de Odoo), *Archivos* (por archivo del módulo) y *Espacios de
  nombres* (módulos de Python, con sus constantes y funciones sueltas).
- **Buscar** (arriba a la derecha): por nombre de clase, método o campo, p. ej. `compute_sheet` o
  `_get_period_input_amounts`.
- **Lista de defectos:** cada `@bug` del código, con su id de la
  [revisión](https://ffunes-cru.github.io/payroll_arg/revision/).
- Cada método muestra **a quién llama** y **quién lo llama** (*Referenciado por* / *Hace referencia a*)
  y el **código fuente**.

## Por dónde empezar

| Clase | Modelo | Qué tiene |
|---|---|---|
| @ref payroll_arg::models::hr_payslip::HrPayslip "HrPayslip" | `hr.payslip` | El recibo: novedades automáticas, parámetros de las reglas, Ganancias, datos del F.931, LSD y recibo PDF. |
| @ref payroll_arg::models::hr_payslip_run::HrPayslipRun "HrPayslipRun" | `hr.payslip.run` | El lote: tipo de liquidación, matriz de novedades, exportaciones. |
| @ref payroll_arg::models::hr_contract::HrContract "HrContract" | `hr.version` | El contrato: tipo de salario, convenio, estructura y calendario por defecto. |
| @ref payroll_arg::models::hr_ganancias::HrGananciasScale "HrGananciasScale" | `hr.ganancias.scale` | Escala de Ganancias y cálculo del impuesto acumulado. |
| @ref payroll_arg_attendance::models::hr_payslip::HrPayslip "HrPayslip (asistencias)" | `hr.payslip` | Horas normales y extras desde las fichadas. |

Las fórmulas de cada concepto son reglas salariales en XML (no aparecen acá): ver la
[referencia generada](https://ffunes-cru.github.io/payroll_arg/referencia/#reglas-salariales).

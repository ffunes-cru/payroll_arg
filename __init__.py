"""@file
Punto de entrada del módulo `payroll_arg`: hace importable la librería `py_arg_reports` (submódulo
`payroll_arg_reportes`) y carga modelos y asistentes.

Ver README.md y docs/ para la documentación funcional y técnica.
"""
import sys
from pathlib import Path

# Agregar el directorio del addon y del submodulo al sys.path para que py_arg_reports
# sea importable directamente como 'from py_arg_reports.reporters...'
_addon_dir = str(Path(__file__).parent.resolve())
if _addon_dir not in sys.path:
    sys.path.insert(0, _addon_dir)

_submodule_dir = str(Path(__file__).parent.resolve() / "payroll_arg_reportes")
if _submodule_dir not in sys.path:
    sys.path.insert(0, _submodule_dir)

from . import models
from . import wizard

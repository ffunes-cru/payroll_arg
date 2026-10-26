# -*- coding: utf-8 -*-
"""@file
Licencias (`hr.leave`): relaja la validación de Odoo que impide tocar licencias aprobadas cuando el
cambio viene de un recálculo del sistema (actualización de módulos, asistencias, calendarios).
"""
from odoo import models, api, _
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    """Licencia con la validación de estado relajada para recálculos automáticos."""

    _inherit = 'hr.leave'

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        """Override _check_date_state to prevent blocking background calendar / system

        recomputations during module upgrades or attendance updates.

        Sigue bloqueando el cambio de fechas o de empleado de una licencia aprobada hecho por un usuario.

        @throws ValidationError Cambio de fechas o empleado de una licencia aprobada.

        @bug T5 (docs/revision.md): se desactiva por completo si el contexto trae `module`,
             `install_mode` o `import_file`, no sólo durante la actualización del módulo.
        """
        if (
            self.env.context.get('leave_skip_state_check')
            or self.env.context.get('install_mode')
            or self.env.context.get('module')
            or self.env.context.get('import_file')
        ):
            return

        for holiday in self:
            if holiday.state in ['validate1', 'validate']:
                # If request dates and employee are unchanged, this is a background recompute
                if (
                    holiday._origin
                    and holiday.request_date_from == holiday._origin.request_date_from
                    and holiday.request_date_to == holiday._origin.request_date_to
                    and holiday.employee_id == holiday._origin.employee_id
                ):
                    continue
                # If date_from and date_to didn't change from database
                if (
                    holiday._origin
                    and holiday.date_from == holiday._origin.date_from
                    and holiday.date_to == holiday._origin.date_to
                    and holiday.employee_id == holiday._origin.employee_id
                ):
                    continue
                raise ValidationError(_("This modification is not allowed in the current state."))

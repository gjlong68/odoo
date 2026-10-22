# -*- coding: utf-8 -*-

from odoo import models


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    def _get_analytic_project(self):
        """Return the project used for analytic lines of this unbuild order.

        Mirror the manufacturing flow: prefer the linked manufacturing order's
        project, then fall back to the BoM's project.
        """
        self.ensure_one()
        if self.mo_id.project_id:
            return self.mo_id.project_id
        if self.bom_id.project_id:
            return self.bom_id.project_id
        return self.env['project.project']

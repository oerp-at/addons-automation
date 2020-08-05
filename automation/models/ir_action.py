# -*- coding: utf-8 -*--
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    state = fields.Selection(selection_add=[("automation_task", "Automation Task")])
    automation_task_id = fields.Many2one("automation.task", "Task", ondelete="cascade")

    def run_action_automation_task_multi(self):
        self.automation_task_id._process_task()
        return False

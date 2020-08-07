# -*- coding: utf-8 -*--
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    state = fields.Selection(selection_add=[("task", "Automation Task")])
    task_id = fields.Many2one("automation.task", "Task", ondelete="cascade", readonly=True)

    def run_action_task_multi(self, action, eval_context=None):
        self.task_id._process_task()
        return False

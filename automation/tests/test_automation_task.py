# -*- coding: utf-8 -*--
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase
from odoo.addons.automation.models.automation import TaskLogger


class TestTask(TransactionCase):
    """ Test automation task """

    def test_task_queueing(self):
        task = self.env["automation.task"].create({
            "name": "Test"
        })
        task.action_queue()

        self.assertTrue(task.cron_id, "Check if cron was set")
        self.assertTrue(task.action_id, "Check if action was set")

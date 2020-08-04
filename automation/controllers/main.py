# -*- coding: utf-8 -*-

from odoo import http, SUPERUSER_ID
from odoo.api import Environment
from odoo import registry as registry_get

class TaskLogController(http.Controller):
    """ task log controller """
    
    @http.route(
        ["/automation/log"],
        type="json",
        auth="automation_task",
        methods=["POST"],
    )
    def log(self, db, token, progress=None, **kwargs):
        registry = registry_get(db)        
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            
            # check if progress passed
            # .. modify progress
            if progress:
                try:
                    progress = float(progress)
                    env["automation.task.stage"].browse(int(kwargs["stage_id"])).write(
                        {"progress": progress}
                    )
                except ValueError:
                    pass
            # log
            return env["automation.task.log"].create(kwargs).id
            
    @http.route(
        ["/automation/stage"],
        type="json",
        auth="automation_task",
        methods=["POST"],
    )
    def stage(self, db, token, **kwargs):
        registry = registry_get(db)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            return env["automation.task.stage"].create(kwargs).id

    @http.route(
        ["/automation/progress"],
        type="json",
        auth="automation_task",
        methods=["POST"],
    )
    def progress(self, db, token, stage_id, **kwargs):
        stage_id = int(stage_id)
        registry = registry_get(db)
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            env["automation.task.stage"].browse(stage_id).write(
                kwargs
            )
        return True
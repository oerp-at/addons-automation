# -*- coding: utf-8 -*--
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


def _list_all_models(self):
    """ show all available odoo models """
    self._cr.execute("SELECT model, name FROM ir_model ORDER BY name")
    return self._cr.fetchall()


class TaskLogger:
    """ Tasklogger is a helper class for logging to logger """

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.name = name
        self._status = None
        self._progress = 0
        self._loop_inc = 0.0
        self._loop_progress = 0.0
        self.errors = 0
        self.warnings = 0

    def log(
        self, message, pri="i", obj=None, ref=None, progress=None, code=None, data=None
    ):
        if pri == "i":
            self.logger.info(message)
        elif pri == "e":
            self.errors += 1
            self.logger.error(message)
        elif pri == "w":
            self.warnings += 1
            self.logger.warning(message)
        elif pri == "d":
            self.logger.debug(message)
        elif pri == "x":
            self.logger.fatal(message)
        elif pri == "a":
            self.logger.critical(message)

    def loge(self, message, pri="e", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def logw(self, message, pri="w", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def logd(self, message, pri="d", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def logn(self, message, pri="n", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def loga(self, message, pri="a", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def logx(self, message, pri="x", **kwargs):
        self.log(message, pri=pri, **kwargs)

    def loop_init(self, loopCount, status=None):
        self._loop_progress = 0.0
        if not loopCount:
            self._loop_progress = 100.0
            self._loop_inc = 0.0
        else:
            self._loop_inc = 100.0 / loopCount
            self._loop_progress = 0.0
        self.progress(status, self._loop_progress)

    def loop_next(self, status=None, step=1):
        self._loop_progress += self._loop_inc * step
        self.progress(status, self._loop_progress)

    def progress(self, status, progress):
        progress = min(round(progress), 100)
        if not status:
            status = "Progress"
        if self._status != status or self._progress != progress:
            self._status = status
            self._progress = progress
            self.log("%s: %s" % (self._status, self._progress))

    def stage(self, subject, total=None):
        self.log("= %s" % subject)

    def substage(self, subject, total=None):
        self.log("== %s" % subject)

    def done(self):
        self.progress("Done", 100.0)

    def close(self):
        pass


class AutomationTask(models.Model):    
    _name = "automation.task"
    _description = "Automation Task"
    _order = "id asc"

    name = fields.Char(required=True, readonly=True, states={"draft": [("readonly", False)]})
    state_change = fields.Datetime(
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: self.env["util.time"]._currentDateTime(),
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("run", "Running"),
            ("cancel", "Canceled"),
            ("failed", "Failed"),
            ("done", "Done"),
        ],
        required=True,
        index=True,
        readonly=True,
        default="draft",
        copy=False
    )

    progress = fields.Float(readonly=True, compute="_compute_progress")
    error = fields.Text(readonly=True, copy=False)
    owner_id = fields.Many2one(
        "res.users",        
        required=True,
        default=lambda self: self._uid,
        index=True,
        readonly=True,
    )

    res_model = fields.Char("Resource Model", index=True, readonly=True)
    res_id = fields.Integer("Resource ID", index=True, readonly=True)
    res_ref = fields.Reference(
        _list_all_models, string="Resource", compute="_res_ref", readonly=True
    )
    cron_id = fields.Many2one(
        "ir.cron",
        "Scheduled Job",
        index=True,
        ondelete="set null",
        copy=False,
        readonly=True,
    )

    total_logs = fields.Integer(compute="_total_logs")
    total_stages = fields.Integer(compute="_total_stages")
    total_warnings = fields.Integer(compute="_total_warnings")

    task_id = fields.Many2one("automation.task", "Task", compute="_task_id")

    start_after_task_id = fields.Many2one(
        "automation.task",
        "Start after task",
        help="Start *this* task after the specified task, was set to null after run state is set.",
        readonly=True,
        ondelete="restrict",
    )
    start_after = fields.Datetime(help="Start *this* task after the specified date/time.")
    
    def _task_id(self):
        for obj in self:
            self.task_id = obj
    
    def _compute_progress(self):
        res = dict.fromkeys(self.ids, 0.0)
        cr = self._cr

        # search stages
        cr.execute(
            "SELECT id FROM automation_task_stage WHERE task_id IN %s AND parent_id IS NULL",
            (tuple(self.ids),),
        )

        # get progress
        stage_ids = [r[0] for r in cr.fetchall()]
        for stage in self.env["automation.task.stage"].browse(stage_ids):
            res[stage.task_id.id] = stage.complete_progress

        # assign
        for obj in self:
            obj.progress = res[obj.id]

    @api.one
    def _res_ref(self):
        if self.res_model and self.res_id:
            res = self.env[self.res_model].search_count([("id", "=", self.res_id)])
            if res:
                self.res_ref = "%s,%s" % (self.res_model, self.res_id)
            else:
                self.res_ref = None
        else:
            self.res_ref = None

    @api.multi
    def _total_logs(self):
        res = dict.fromkeys(self.ids, 0)
        cr = self._cr
        cr.execute(
            "SELECT task_id, COUNT(*) FROM automation_task_log WHERE task_id IN %s GROUP BY 1",
            (tuple(self.ids),),
        )
        for task_id, log_count in cr.fetchall():
            res[task_id] = log_count
        for r in self:
            r.total_logs = res[r.id]

    @api.multi
    def _total_warnings(self):
        res = dict.fromkeys(self.ids, 0)
        cr = self._cr
        cr.execute(
            "SELECT task_id, COUNT(*) FROM automation_task_log WHERE pri IN ('a','e','w','x') AND task_id IN %s GROUP BY 1",
            (tuple(self.ids),),
        )
        for task_id, log_count in cr.fetchall():
            res[task_id] = log_count
        for r in self:
            r.total_warnings = res[r.id]

    @api.multi
    def _total_stages(self):
        res = dict.fromkeys(self.ids, 0)
        cr = self._cr
        cr.execute(
            "SELECT task_id, COUNT(*) FROM automation_task_stage WHERE task_id IN %s GROUP BY 1",
            (tuple(self.ids),),
        )
        for task_id, stage_count in cr.fetchall():
            res[task_id] = stage_count
        for r in self:
            r.total_stages = res[r.id]

    @api.one
    def _run(self, taskc):
        """" Test Task """
        for stage in range(1, 10):
            taskc.stage("Stage %s" % stage)

            for proc in range(1, 100, 10):
                taskc.log("Processing %s" % stage)
                taskc.progress("Processing %s" % stage, proc)
                time.sleep(1)

            taskc.done()

    def _stage_count(self):
        self.ensure_one()
        return 10

    def _task_get_list(self):
        self.ensure_one()
        res = []
        task = self
        while task:
            res.append(task.id)
            task = task.after_once_task_id
        return self.browse(res)

    def _task_add_after_last(self, task):
        """ Add task after this """
        if task:
            self.ensure_one()

            last_task = self
            while last_task.after_once_task_id:
                last_task = last_task.after_once_task_id

            last_task.write({"after_once_task_id": task.id})

    def _task_insert_after(self, task):
        """ Insert task after this"""
        if task:
            self.ensure_one()
            task_after = self.after_once_task_id
            self.write({"after_once_task_id": task.id})
            task._add_after_last(task_after)

    def _check_execution_rights(self):
        # check rights
        if self.owner_id.id != self._uid and not self.user_has_groups(
            "automation.group_automation_manager,base.group_system"
        ):
            raise Warning(
                _(
                    "Not allowed to start task. You be the owner or an automation manager"
                )
            )

    @api.multi
    def action_cancel(self):
        for task in self:
            # check rights
            task._check_execution_rights()
            if task.state == "queued":
                task.state = "cancel"
        return True

    @api.multi
    def action_refresh(self):
        return True

    @api.multi
    def action_reset(self):
        return True

    @api.multi
    def action_queue(self):

        for task in self:
            # check rights
            task._check_execution_rights()
            if task.state in ("draft", "cancel", "failed", "done"):
                # sudo task
                sudo_task = task.sudo()

                # add cron entry
                sudo_cron = sudo_task.cron_id
                if not sudo_cron:
                    sudo_cron = (
                        self.env["ir.cron"].sudo().create(sudo_task._get_cron_values())
                    )
                else:
                    sudo_cron.write(sudo_task._get_cron_values())

                # set stages inactive
                self._cr.execute(
                    "DELETE FROM automation_task_stage WHERE task_id=%s",
                    (sudo_task.id,),
                )

                # set queued
                sudo_task.state = "queued"
                sudo_task.error = None
                sudo_task.cron_id = sudo_cron

                # create secret
                sudo_secret = self.env["automation.task.secret"].sudo()
                if not sudo_secret.search([("task_id", "=", sudo_task.id)]):
                    sudo_secret.create({"task_id": sudo_task.id})

        return True

    def _get_cron_values(self):
        self.ensure_one()

        # start after is set
        # use start_after date instead of next call
        nextcall = util.currentDateTime()
        if nextcall < self.start_after:
            nextcall = self.start_after

        # new cron entry
        return {
            "name": "Task: %s" % self.name,
            "user_id": SUPERUSER_ID,
            "interval_type": "minutes",
            "interval_number": 1,
            "nextcall": nextcall,
            "numbercall": 1,
            "model": self._name,
            "function": "_process_task",
            "args": "(%s,)" % self.id,
            "active": True,
            "priority": 1000 + self.id,
            "task_id": self.id,
        }

    @api.model
    def _cleanup_tasks(self):
        # clean up cron tasks
        self._cr.execute("DELETE FROM ir_cron WHERE task_id IS NOT NULL AND NOT active")
        return True

    @api.model
    def _process_task(self, task_id):
        task = self.browse(task_id)
        if task and task.state == "queued":
            try:
                # get options
                if task.res_model and task.res_id:
                    model_obj = self.env[task.res_model]
                    resource = model_obj.browse(task.res_id)
                else:
                    resource = task

                # options

                options = {"stages": 1, "resource": resource}

                # get custom options

                if hasattr(resource, "_run_options"):
                    res_options = getattr(resource, "_run_options")
                    if callable(res_options):
                        res_options = resource._run_options()
                    options.update(res_options)

                stage_count = options["stages"]

                # check if it is a singleton task
                # if already another task run, requeue
                # don't process this task
                if options.get("singleton"):
                    # cleanup
                    self._cr.execute(
                        "DELETE FROM ir_cron WHERE task_id=%s AND id!=%s AND NOT active",
                        (task.id, task.cron_id.id),
                    )
                    # check concurrent
                    self._cr.execute(
                        "SELECT MIN(id) FROM automation_task WHERE res_model=%s AND state IN ('queued','run')",
                        (resource._model._name,),
                    )
                    active_task_id = self._cr.fetchone()[0]
                    if active_task_id and active_task_id < task_id:
                        # requeue
                        task.cron_id = self.env["ir.cron"].create(
                            task._get_cron_values()
                        )
                        return True

                task_after_once = task.after_once_task_id

                # change task state
                # and commit
                task.write(
                    {
                        "state_change": util.currentDateTime(),
                        "state": "run",
                        "error": None,
                    }
                )
                # commit after start
                self._cr.commit()

                # run task
                taskc = TaskStatus(task, stage_count)
                resource._run(taskc)

                # check fail on errors
                if options.get("fail_on_errors"):
                    if taskc.errors:
                        raise Warning("Task finished with errors")

                # close
                taskc.close()

                # update status
                task.write(
                    {
                        "state_change": util.currentDateTime(),
                        "state": "done",
                        "error": None,
                        "after_once_task_id": None,
                    }
                )

                # commit after finish
                self._cr.commit()

                # queue task after
                if task_after_once:
                    task_after_ref = task_after_once.res_ref
                    if task_after_ref:
                        task_after_ref.action_queue()

            except Exception as e:
                # rollback on error
                self._cr.rollback()
                                
                _logger.exception("Task execution failed")
                task = self.browse(task_id) # reload task after rollback

                # securely try to get message
                error = None
                try:
                    error = str(e)
                    if not error and hasattr(e, "message"):
                        error = e.message
                except:
                    _logger.exception("Error parsing failed")
                    pass

                #if there is no message
                if not error:
                    error = "Unexpected error, see logs"

                # write error
                task.write(
                    {
                        "state_change": util.currentDateTime(),
                        "state": "failed",
                        "error": error,
                    }
                )
                self._cr.commit()
        
        return True

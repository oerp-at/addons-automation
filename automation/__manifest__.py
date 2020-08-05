# -*- coding: utf-8 -*--
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Automation',
    'version': '13.0.1.0.0',
    'summary': 'Provide an automation framework',
    'category': 'Generic Modules',
    'author': 'Odoo Community Association (OCA)',
    'maintainers': ['mreisenhofer'],
    'website': 'https://github.com/oerp-at',
    'license': 'LGPL-3',
    'depends': ['util_time'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/task_log.xml',
        'views/stage_view.xml',
        'views/cron_view.xml',
        'views/task_view.xml'
    ],
    'installable': True
}

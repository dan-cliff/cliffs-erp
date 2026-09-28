# Part of Cliffs. See LICENSE file for full copyright and licensing details.

{
    'name': 'Workflow Stages',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Generic multi-path stage workflows, with a visual designer, for any model',
    'description': """
Workflow Stages
================

A generic workflow engine that any module can plug a model into.

Features:
---------
* Define a workflow of Stages and Transitions for any model (via ir.model),
  with a visual drag-and-drop canvas editor for designing the graph.
* Each Stage can restrict which users are considered "allowed" for that
  stage, using the standard Odoo filter builder against the Users model.
* Each Transition can require:
  - A condition on the record (domain filter or Python expression).
  - Whether it may be triggered manually, automatically (e.g. from an
    automation rule / server action), or both.
  - Which users may manually trigger it (any user, the origin stage's
    allowed users, or a custom filter).
* Transitions are directional (Forward / Backward) — the direction is
  shown to the user (as an arrow) whenever they are offered a stage change.
* When several transitions are available at once, all of them are offered
  — multi-path / branching workflows are a first-class citizen, not an
  edge case.
* Any model can adopt this by inheriting the `wkf.stage.mixin` abstract
  model, which adds a `wkf_stage_id` field plus the methods needed to
  list available transitions and apply one — from a manual "Change Stage"
  wizard, or programmatically from a server action / automation rule.
    """,
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/wkf_security.xml',
        'security/ir.model.access.csv',
        'views/wkf_workflow_views.xml',
        'views/wkf_stage_views.xml',
        'views/wkf_transition_views.xml',
        'views/wkf_change_stage_wizard_views.xml',
        'views/wkf_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'workflow_stages/static/src/js/**/*',
            'workflow_stages/static/src/xml/**/*',
            'workflow_stages/static/src/scss/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}

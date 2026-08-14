{
    'name': 'Seeance - Learning Management',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Require Learning Management courses at Seeance Check Points',
    'description': """
Seeance - Learning Management
==============================
Lets a Check Point require workers to have completed one or more Courses
(from the Learning Management app) before signing in.

This module bridges Seeance and Learning Management, so it only installs,
and this feature only appears, once both apps are installed.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['seeance', 'learning_management'],
    'data': [
        'views/seeance_check_point_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}

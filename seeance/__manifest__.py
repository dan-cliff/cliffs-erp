{
    'name': 'Seeance',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Worker check-in/check-out kiosks for company work locations',
    'description': """
Seeance
=======
Manage Check Points: the kiosks where workers sign in and out of a
company's work locations. Each Check Point records the Company and Work
Location it belongs to, and can be provisioned as an installable, offline
capable PWA kiosk secured by a unique PIN.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/seeance_check_point_views.xml',
        'views/seeance_work_location_views.xml',
        'views/seeance_attendance_views.xml',
        'views/seeance_menus.xml',
        'views/seeance_pwa_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

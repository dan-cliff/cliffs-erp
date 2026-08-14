{
    'name': 'Seeance - Employees',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Identify Seeance sign in/out records by Employee',
    'description': """
Seeance - Employees
====================
Records who signed in/out at a Seeance Check Point by Employee instead of
by User.

This module bridges Seeance and Employees, so it only installs, and this
feature only appears, once both apps are installed. Without it, Seeance
falls back to identifying people by their Odoo User.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['seeance', 'hr'],
    'data': [
        'views/seeance_attendance_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}

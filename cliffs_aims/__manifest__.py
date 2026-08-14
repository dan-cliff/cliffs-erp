{
    'name': 'Cliffs AIMS',
    'version': '19.0.1.0.0',
    'category': 'Operations',
    'summary': 'Account Information Management System for tracking client Odoo instances',
    'description': """
Account Information Management System (AIMS)
==============================================
A database of all client Odoo instances, the servers that host them, and the
cloud providers those servers run on. Enables reporting on key account
metrics and toggling of per-instance features.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'sale_subscription'],
    'data': [
        'security/ir.model.access.csv',
        'views/aims_cloud_provider_views.xml',
        'views/aims_server_views.xml',
        'views/aims_account_status_views.xml',
        'views/aims_account_health_views.xml',
        'views/aims_account_package_views.xml',
        'views/aims_instance_type_views.xml',
        'views/aims_instance_views.xml',
        'views/aims_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

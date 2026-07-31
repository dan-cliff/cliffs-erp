{
    'name': 'Cliffs Helpdesk',
    'version': '19.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Manage support queues, agents, and tickets from email or the web',
    'description': """
Helpdesk
========
Track support requests as tickets organized into Queues.

* Allocate Agents to each Queue to control who handles its tickets.
* Give each Queue its own email alias so incoming emails automatically
  create tickets in the right Queue.
* Configure Stages, Priorities, Types, Sources and Tags from the
  Helpdesk > Configuration menu, no code changes required.
* Tickets link to the Contacts app for their Company and Contact.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['mail', 'contacts'],
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_ticket_sequence.xml',
        'data/helpdesk_ticket_stage_data.xml',
        'data/helpdesk_ticket_priority_data.xml',
        'data/helpdesk_ticket_type_data.xml',
        'data/helpdesk_ticket_source_data.xml',
        'views/helpdesk_ticket_stage_views.xml',
        'views/helpdesk_ticket_priority_views.xml',
        'views/helpdesk_ticket_type_views.xml',
        'views/helpdesk_ticket_source_views.xml',
        'views/helpdesk_tag_views.xml',
        'views/helpdesk_queue_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

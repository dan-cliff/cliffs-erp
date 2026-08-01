{
    'name': 'Cliffs Barcode Scanner',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Offline-capable barcode scanning PWA for warehouse operations',
    'description': """
Standalone, installable PWA for processing warehouse operations by barcode scan.

Shows Operation Types, the transfers ready to process for the selected type, and a
scan-driven picking screen (hardware scanner or device camera) that keeps working
offline and syncs queued changes back to Odoo once the connection returns.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['stock', 'web'],
    'data': [
        'data/barcode_scanner_menu.xml',
        'views/barcode_scanner_templates.xml',
    ],
    'assets': {
        # The PWA itself (static/src/pwa/**) is intentionally NOT part of any
        # Odoo asset bundle: it's served as plain static files and loaded via
        # native <script type="module"> tags from views/barcode_scanner_templates.xml,
        # so it has no dependency on the backend's SCSS/asset-bundle pipeline
        # and can't be affected by (or affect) other backend assets.
        'web.assets_backend': [
            'cliffs_barcode_scanner/static/src/launcher/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

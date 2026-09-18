import json
import os

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_path

MANIFEST_ICONS = [
    {"src": "/cliffs_barcode_scanner/static/description/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/cliffs_barcode_scanner/static/description/icon-512.png", "sizes": "512x512", "type": "image/png"},
]


class BarcodeScannerController(http.Controller):

    @http.route('/barcode_scanner', type='http', auth='user', website=False, sitemap=False)
    def barcode_scanner_app(self, **kwargs):
        return request.render('cliffs_barcode_scanner.pwa_page', {})

    @http.route('/barcode_scanner/manifest.webmanifest', type='http', auth='user', website=False, sitemap=False)
    def barcode_scanner_manifest(self, **kwargs):
        manifest = {
            "name": "Cliffs Barcode Scanner",
            "short_name": "Barcode Scanner",
            "start_url": "/barcode_scanner",
            "scope": "/barcode_scanner/",
            "display": "standalone",
            "orientation": "any",
            "background_color": "#ffffff",
            "theme_color": "#714B67",
            "icons": MANIFEST_ICONS,
        }
        return request.make_response(
            json.dumps(manifest),
            headers=[('Content-Type', 'application/manifest+json')],
        )

    @http.route('/barcode_scanner/service_worker.js', type='http', auth='user', website=False, sitemap=False)
    def barcode_scanner_service_worker(self, **kwargs):
        # Served from a /barcode_scanner/ path (rather than the module's own
        # static/ path) so its default max scope covers the whole PWA and
        # can't reach up into the rest of the Odoo backend.
        path = os.path.join(
            get_module_path('cliffs_barcode_scanner'), 'static', 'src', 'pwa', 'service_worker.js'
        )
        with open(path, 'rb') as f:
            content = f.read()
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Service-Worker-Allowed', '/barcode_scanner/'),
                ('Cache-Control', 'no-cache'),
            ],
        )

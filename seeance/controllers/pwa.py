import json

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.modules.module import get_module_resource

# Any request that successfully reaches these endpoints (heartbeat, sync, or a
# checkin) is itself proof the kiosk is online, so they all touch last_seen.
#
# These are plain JSON-over-HTTP endpoints (type='http'), not Odoo's
# type='json' JSON-RPC routes: the kiosk PWA is a bespoke client, not the
# Odoo web client, so it posts/receives plain JSON bodies without the
# JSON-RPC 2.0 envelope. Authorization is via the Check Point's PIN, not an
# Odoo user session, since kiosk devices are never logged into Odoo.


class SeeanceKioskController(http.Controller):

    def _get_check_point(self, pin):
        if not pin:
            raise AccessDenied('Missing kiosk PIN.')
        check_point = request.env['seeance.check_point'].sudo().search(
            [('access_pin', '=', pin)], limit=1)
        if not check_point:
            raise AccessDenied('Invalid kiosk PIN.')
        return check_point

    def _touch_check_point(self, check_point, os_info=None, connection_type=None):
        vals = {
            'last_seen': fields.Datetime.now(),
            'last_ip': request.httprequest.remote_addr,
        }
        if os_info is not None:
            vals['last_os_info'] = os_info
        if connection_type is not None:
            vals['last_connection_type'] = connection_type
        check_point.sudo().write(vals)

    def _json_response(self, data, status=200):
        return request.make_response(
            json.dumps(data), status=status,
            headers=[('Content-Type', 'application/json')])

    def _read_json_body(self):
        raw = request.httprequest.get_data()
        return json.loads(raw) if raw else {}

    # -- Kiosk shell / installability ---------------------------------------

    @http.route('/seeance/kiosk/<int:check_point_id>', type='http', auth='public', website=False)
    def kiosk_shell(self, check_point_id, pin=None, **kwargs):
        check_point = request.env['seeance.check_point'].sudo().browse(check_point_id)
        if not check_point.exists():
            return request.not_found()
        # Rendered manually (rather than request.render) so we control the
        # raw response body: QWeb's XML source can't safely contain a literal
        # <!DOCTYPE html> line, so it's prepended here instead.
        body = request.env['ir.qweb']._render('seeance.kiosk_shell', {
            'check_point_id': check_point.id,
            'pin': pin or '',
        })
        html = '<!DOCTYPE html>\n' + str(body)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/seeance/kiosk/<int:check_point_id>/manifest.webmanifest',
                type='http', auth='public', website=False)
    def kiosk_manifest(self, check_point_id, pin=None, **kwargs):
        check_point = request.env['seeance.check_point'].sudo().browse(check_point_id)
        if not check_point.exists() or not pin or check_point.access_pin != pin:
            return request.not_found()
        start_url = f'/seeance/kiosk/{check_point.id}?pin={pin}'
        manifest = {
            'name': f'Seeance - {check_point.work_location_id.name or check_point.name}',
            'short_name': 'Seeance',
            'description': 'Seeance sign in / sign out kiosk',
            'start_url': start_url,
            'id': start_url,
            'scope': '/seeance/kiosk/',
            'display': 'standalone',
            'orientation': 'any',
            'background_color': '#111827',
            'theme_color': '#111827',
            'icons': [
                {'src': '/seeance/static/src/pwa/icons/icon-192.png',
                 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any maskable'},
                {'src': '/seeance/static/src/pwa/icons/icon-512.png',
                 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'},
            ],
        }
        return request.make_response(
            json.dumps(manifest),
            headers=[('Content-Type', 'application/manifest+json')])

    @http.route('/seeance/kiosk/service-worker.js', type='http', auth='public', website=False)
    def kiosk_service_worker(self, **kwargs):
        path = get_module_resource('seeance', 'static', 'src', 'pwa', 'service-worker.js')
        with open(path, 'rb') as f:
            content = f.read()
        return request.make_response(content, headers=[
            ('Content-Type', 'application/javascript'),
            ('Service-Worker-Allowed', '/seeance/kiosk/'),
            ('Cache-Control', 'no-cache'),
        ])

    # -- JSON API used by the PWA --------------------------------------------

    @http.route('/seeance/kiosk/api/heartbeat', type='http', auth='public', csrf=False, methods=['POST'])
    def kiosk_heartbeat(self, **kwargs):
        body = self._read_json_body()
        try:
            check_point = self._get_check_point(body.get('pin'))
        except AccessDenied as exc:
            return self._json_response({'ok': False, 'error': str(exc)}, status=403)
        self._touch_check_point(
            check_point, os_info=body.get('os_info'), connection_type=body.get('connection_type'))
        return self._json_response({
            'ok': True, 'server_time': fields.Datetime.to_string(fields.Datetime.now())})

    @http.route('/seeance/kiosk/api/sync', type='http', auth='public', csrf=False, methods=['POST'])
    def kiosk_sync(self, **kwargs):
        body = self._read_json_body()
        try:
            check_point = self._get_check_point(body.get('pin'))
        except AccessDenied as exc:
            return self._json_response({'ok': False, 'error': str(exc)}, status=403)
        self._touch_check_point(
            check_point, os_info=body.get('os_info'), connection_type=body.get('connection_type'))
        payload = check_point.sudo()._get_pwa_sync_payload()
        payload['ok'] = True
        return self._json_response(payload)

    @http.route('/seeance/kiosk/api/checkin', type='http', auth='public', csrf=False, methods=['POST'])
    def kiosk_checkin(self, **kwargs):
        body = self._read_json_body()
        try:
            check_point = self._get_check_point(body.get('pin'))
        except AccessDenied as exc:
            return self._json_response({'ok': False, 'error': str(exc)}, status=403)

        mechanism = body.get('mechanism')
        if mechanism not in ('sign_in', 'sign_out'):
            return self._json_response({'ok': False, 'error': 'Invalid mechanism.'}, status=400)

        origin_uuid = body.get('origin_uuid')
        Attendance = request.env['seeance.attendance'].sudo()
        if origin_uuid:
            existing = Attendance.search([('origin_uuid', '=', origin_uuid)], limit=1)
            if existing:
                return self._json_response({'ok': True, 'id': existing.id, 'duplicate': True})

        vals = {
            'datetime': body.get('datetime') or fields.Datetime.now(),
            'mechanism': mechanism,
            'company_id': check_point.company_id.id,
            'work_location_id': check_point.work_location_id.id,
            'check_point_id': check_point.id,
            'origin_uuid': origin_uuid,
        }
        if body.get('image'):
            vals['image'] = body['image']

        identity_field = check_point._get_pwa_identity_field()
        identity_values = {'user_id': body.get('user_id'), 'employee_id': body.get('employee_id')}
        identity_value = identity_values.get(identity_field)
        if identity_field in Attendance._fields and identity_value:
            vals[identity_field] = identity_value

        record = Attendance.create(vals)
        return self._json_response({'ok': True, 'id': record.id})

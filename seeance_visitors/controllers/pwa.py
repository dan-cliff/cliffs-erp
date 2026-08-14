from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.seeance.controllers.pwa import SeeanceKioskController


class SeeanceVisitorKioskController(SeeanceKioskController):

    @http.route('/seeance/kiosk/api/visitor_register', type='http', auth='public',
                csrf=False, methods=['POST'])
    def kiosk_visitor_register(self, **kwargs):
        body = self._read_json_body()
        try:
            check_point = self._get_check_point(body.get('pin'))
        except AccessDenied as exc:
            return self._json_response({'ok': False, 'error': str(exc)}, status=403)

        if not check_point.allow_visitor_registration:
            return self._json_response(
                {'ok': False, 'error': 'Visitor registration is not enabled at this Check Point.'},
                status=400)

        name = (body.get('name') or '').strip()
        if not name:
            return self._json_response({'ok': False, 'error': 'Visitor name is required.'}, status=400)

        origin_uuid = body.get('origin_uuid')
        Registration = request.env['seeance.visitor.registration'].sudo()
        if origin_uuid:
            existing = Registration.search([('origin_uuid', '=', origin_uuid)], limit=1)
            if existing:
                return self._json_response({'ok': True, 'id': existing.id, 'duplicate': True})

        questions_by_id = {q.id: q for q in check_point.visitor_question_ids}
        answered = {
            a.get('question_id'): (a.get('answer') or '').strip()
            for a in (body.get('answers') or [])
        }
        answer_vals = [
            (0, 0, {'question_id': question_id, 'answer': answer_text})
            for question_id, answer_text in answered.items()
            if question_id in questions_by_id
        ]
        missing_required = [
            q.name for q in check_point.visitor_question_ids
            if q.is_required and not answered.get(q.id)
        ]
        if missing_required:
            return self._json_response(
                {'ok': False, 'error': f"Missing required answers: {', '.join(missing_required)}"},
                status=400)

        vals = {
            'name': name,
            'datetime': body.get('datetime') or fields.Datetime.now(),
            'company_id': check_point.company_id.id,
            'work_location_id': check_point.work_location_id.id,
            'check_point_id': check_point.id,
            'origin_uuid': origin_uuid,
            'answer_ids': answer_vals,
        }
        if body.get('image'):
            vals['image'] = body['image']

        record = Registration.create(vals)
        return self._json_response({'ok': True, 'id': record.id})

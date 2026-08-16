import hashlib
import hmac
import secrets
import time

from odoo import http
from odoo.http import request

from ..const import LOGIN_ROUTE, SYSTEM_MANAGER_XML_ID, TOKEN_SECRET_PARAM, TOKEN_TTL_SECONDS


def sign_token(secret, nonce, expires_at):
    message = f'{nonce}.{expires_at}'.encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def make_login_token(secret, ttl=TOKEN_TTL_SECONDS):
    nonce = secrets.token_urlsafe(16)
    expires_at = int(time.time()) + ttl
    signature = sign_token(secret, nonce, expires_at)
    return f'{nonce}.{expires_at}.{signature}'


class CliffsSystemLoginController(http.Controller):

    @http.route(LOGIN_ROUTE, type='http', auth='public')
    def system_login(self, token):
        env = request.env(su=True)
        secret = env['ir.config_parameter'].get_param(TOKEN_SECRET_PARAM)
        user = env.ref(SYSTEM_MANAGER_XML_ID, raise_if_not_found=False)
        if not secret or not user or not self._consume_token(env, secret, token):
            return request.not_found()

        # Mirrors what res.users.authenticate() sets after a normal
        # password login - there is no public API for "establish a
        # session for this user without a credential check".
        request.session.uid = user.id
        request.session.login = user.login
        request.session.session_token = user._compute_session_token(request.session.sid)
        return request.redirect('/odoo')

    def _consume_token(self, env, secret, token):
        try:
            nonce, expires_at, signature = token.split('.')
            expires_at = int(expires_at)
        except ValueError:
            return False

        if time.time() > expires_at:
            return False
        if not hmac.compare_digest(sign_token(secret, nonce, expires_at), signature):
            return False

        nonces = env['cliffs.login.nonce'].sudo()
        if nonces.search_count([('nonce', '=', nonce)]):
            return False
        nonces.create({'nonce': nonce})
        return True

def _set_home_screen_as_default_action(env):
    action = env.ref('cliffs_home_screen.action_home_screen', raise_if_not_found=False)
    if not action:
        return
    env['ir.default'].set('res.users', 'action_id', action.id)
    env['res.users'].search([]).write({'action_id': action.id})


def _unset_home_screen_as_default_action(env):
    action = env.ref('cliffs_home_screen.action_home_screen', raise_if_not_found=False)
    if not action:
        return
    env['ir.default'].search([
        ('field_id.model', '=', 'res.users'),
        ('field_id.name', '=', 'action_id'),
        ('json_value', '=', str(action.id)),
    ]).unlink()
    env['res.users'].search([('action_id', '=', action.id)]).write({'action_id': False})

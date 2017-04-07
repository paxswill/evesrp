import flask_babel

from evesrp import new_models as models


def pretty_permission(permission_type):
    if permission_type == models.PermissionType.submit:
        return flask_babel.gettext(u'Submitter')
    elif permission_type == models.PermissionType.review:
        return flask_babel.gettext(u'Reviewer')
    elif permission_type == models.PermissionType.pay:
        return flask_babel.gettext(u'Payer')
    elif permission_type == models.PermissionType.audit:
        return flask_babel.gettext(u'Auditor')
    elif permission_type == models.PermissionType.admin:
        return flask_babel.gettext(u'Administrator')

import six
from evesrp import new_models as models
from . import errors


class RequestSubmissionActivity(object):

    def __init__(self, store, user):
        self.store = store
        if isinstance(user, six.integer_types):
            user = self.store.get_user(user_id=user)
        self.user = user

    def list_divisions(self):
        permissions = self.user.get_permissions(self.store)
        submit_division_ids = {p.division_id for p in permissions if \
                              p.type_ == models.PermissionType.submit}
        divisions = self.store.get_divisions(division_ids=submit_division_ids)
        return divisions

    def submit_request(self, details, division, killmail):
        if isinstance(division, six.integer_types):
            division = self.store.get_division(division_id=division)
        # Check permissions first
        if division not in self.list_divisions():
            error_message = (u"User {} does not have permission to submit to "
                             u"Division {}.").format(self.user.id_,
                                                     division.id_)
            raise errors.InsuffcientPermissionsError(error_message)
        if isinstance(killmail, six.integer_types):
            killmail = self.store.get_killmail(killmail_id=killmail)
        request = models.Request(None, details, killmail_id=killmail.id_,
                                 division_id = division.id_)
        request.id_ = self.store.add_request(request)
        return request


class RequestActivity(object):

    def __init__(self, store, user, request):
        pass

    def _add_action(self, type_, comment=u''):
        pass

    def comment(self, comment=u''):
        pass

    def approve(self, comment=u''):
        pass

    def incomplete(self, comment=u''):
        pass

    def evaluate(self, comment=u''):
        pass

    def pay(self, comment=u''):
        pass

    def reject(self, comment=u''):
        pass

    def _add_modifier(self, value, type_, comment=u''):
        pass

    def add_relative_modifier(self, value, comment=u''):
        pass

    def add_absolute_modifier(self, value, comment=u''):
        pass

    def void_modifier(self, modifier):
        pass

    def edit_details(self, new_details):
        pass

    def set_payout(self, new_payout):
        pass

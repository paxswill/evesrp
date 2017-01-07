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
            raise errors.InsufficientPermissionsError(error_message)
        if isinstance(killmail, six.integer_types):
            killmail = self.store.get_killmail(killmail_id=killmail)
        request = models.Request(None, details, killmail_id=killmail.id_,
                                 division_id = division.id_)
        request.id_ = self.store.add_request(request)
        return request


class RequestActivity(object):

    def __init__(self, store, user, request):
        self.store = store
        if isinstance(user, six.integer_types):
            user = self.store.get_user(user_id=user)
        self.user = user
        if isinstance(request, six.integer_types):
            request = self.store.get_request(request_id=request)
        self.request = request
        # Check permissions now
        # Create the permission tuples that will allow access to this request
        allowed_permissions = {(pt, self.request.division_id) for pt in \
                               models.PermissionType.elevated}
        allowed_permissions.add(('user_id', self._submitter_id))
        if allowed_permissions.isdisjoint(user.get_permissions(self.store)):
            error_message = u"User {} does not have access to request #{}."\
                .format(self.user.id_, self.request.id_)
            raise errors.InsufficientPermissionsError(error_message)

    def _add_action(self, type_, allowed_permissions, error_message,
                    comment=u''):
        if allowed_permissions.isdisjoint(
                self.user.get_permissions(self.store)):
            raise errors.InsufficientPermissionsError(error_message)
        else:
            return self.request.add_action(self.store,
                                           type_,
                                           contents=comment,
                                           user=self.user)

    @property
    def _submitter_id(self):
        return self.request.get_killmail(self.store).user_id

    def comment(self, comment=u''):
        PT = models.PermissionType
        allowed_permissions = {(p, self.request.division_id) for p in
                               (PT.review, PT.pay, PT.admin)}
        allowed_permissions.add(('user_id', self._submitter_id))
        error_message = (u"User {} does not have permission to comment on "
                         u"request #{}.").format(self.user.id_,
                                                 self.request.id_)
        return self._add_action(models.ActionType.comment, allowed_permissions,
                                error_message, comment)

    def approve(self, comment=u''):
        PT = models.PermissionType
        if self.request.status == models.ActionType.paid:
            allowed_permissions = {(p, self.request.division_id) for p in
                                   (PT.pay, PT.admin)}
        else:
            allowed_permissions = {(p, self.request.division_id) for p in
                                   (PT.review, PT.admin)}
        error_message = (u"User {} does not have permission to approve request"
                         u" #{}.").format(self.user.id_, self.request.id_)
        return self._add_action(models.ActionType.approved, allowed_permissions,
                                error_message, comment)

    def incomplete(self, comment=u''):
        PT = models.PermissionType
        allowed_permissions = {(p, self.request.division_id) for p in
                               (PT.review, PT.admin)}
        error_message = (u"User {} does not have permission to mark "
                         u"request #{} as incomplete.").format(self.user.id_,
                                                               self.request.id_)
        return self._add_action(models.ActionType.incomplete,
                                allowed_permissions, error_message, comment)

    def evaluate(self, comment=u''):
        PT = models.PermissionType
        if self.request.status == models.ActionType.paid:
            allowed_permissions = {(p, self.request.division_id) for p in
                                   (PT.pay, PT.admin)}
        else:
            allowed_permissions = {(p, self.request.division_id) for p in
                                   (PT.review, PT.admin)}
        error_message = (u"User {} does not have permission to mark request"
                         u" #{} as evaluating.").format(self.user.id_,
                                                        self.request.id_)
        return self._add_action(models.ActionType.evaluating,
                                allowed_permissions, error_message, comment)

    def pay(self, comment=u''):
        PT = models.PermissionType
        allowed_permissions = {(p, self.request.division_id) for p in
                               (PT.pay, PT.admin)}
        error_message = (u"User {} does not have permission to mark "
                         u"request #{} as paid.").format(self.user.id_,
                                                         self.request.id_)
        return self._add_action(models.ActionType.paid, allowed_permissions,
                                error_message, comment)

    def reject(self, comment=u''):
        PT = models.PermissionType
        allowed_permissions = {(p, self.request.division_id) for p in
                               (PT.review, PT.admin)}
        error_message = (u"User {} does not have permission to reject request "
                         u" #{}.").format(self.user.id_, self.request.id_)
        return self._add_action(models.ActionType.rejected, allowed_permissions,
                                error_message, comment)

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
        PT = models.PermissionType
        allowed_permissions = {(p, self.request.division_id) for p in
                               (PT.review, PT.admin)}
        if allowed_permissions.isdisjoint(
                self.user.get_permissions(self.store)):
            error_message = (u"User {} does not have permission to set the "
                             u"payout for request #{}.").format(
                                 self.user.id_, self.request.id_)
            raise errors.InsufficientPermissionsError(error_message)
        else:
            self.request.set_base_payout(self.store, new_payout)

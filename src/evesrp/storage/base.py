class BaseStore(object):

    def __init__(self):
        pass

    ### Divisions ###

    def get_division(self, division_id):
        pass

    def add_division(self, division):
        pass

    def save_division(self, division):
        pass

    ### Permissions ###

    def get_permission(self):
        pass

    def get_permissions(self, **kwargs):
        pass

    def add_permission(self, permission):
        pass

    def remove_permission(self, permission_id):
        pass

    ### Users and Groups ###

    def get_user(self, user_id):
        pass

    def get_users(self, **kwargs):
        pass

    def get_groups(self, **kwargs):
        pass

    def associate_user_group(self, user_id, group_id):
        pass

    def disassociate_user_group(self, user_id, group_id):
        pass

    ### Killmails ###

    def get_killmail(self, killmail_id):
        pass

    def get_killmails(self, **kwargs):
        pass

    ### Requests ###

    def get_request(self):
        pass

    def get_requests(self, **kwargs):
        pass

    def add_request(self, request):
        pass

    def save_request(self, request):
        pass

    ### Request Actions ###

    def get_action(self):
        pass

    def get_actions(self, **kwargs):
        pass

    def add_action(self, action):
        pass

    ### Request Modifiers ###

    def get_modifier(self, modifier_id):
        pass

    def get_modifiers(self, **kwargs):
        pass

    def add_modifier(self, modifier):
        pass

    def save_modifier(self, modifier):
        pass

    ### Filtering ###

    def filter_requests(self, filters):
        pass

    def filter_sparse(self, filters, fields):
        pass

    ### Misc ###

    def get_pilot(self, pilot_id):
        pass

    def get_notes(self, **kwargs):
        pass


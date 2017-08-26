class StorageError(Exception):

    def __init__(self, kind, identifier):
        self.kind = kind
        self.identifier = identifier
        self.error = "Error interacting with {} '{}'.".format(self.kind,
                                                              self.identifier)


class NotFoundError(StorageError):

    def __init__(self, kind, identifier):
        super(NotFoundError, self).__init__(kind, identifier)
        self.error = "{} '{}' not found.".format(self.kind,
                                                 self.identifier)


class NotInAllianceError(NotFoundError):

    def __init__(self, kind, identitifer):
        super(NotInAllianceError, self).__init__(kind, identitifer)
        self.error = "{} '{}' is not in an alliance.".format(self.kind,
                                                             self.identifier)


class EsiError(Exception):

    def __init__(self, response):
        self.status = response.status_code
        self.url = response.url
        try:
            json_resp = response.json()
        except ValueError:
            self.error = "No parseable JSON."
        else:
            self.error = json_resp[u'error']

    def __str__(self):
        return self.error


class EsiWarning(DeprecationWarning):
    pass


class VoidedModifierError(Exception):

    def __init__(self, modifier_id):
        self.modifier_id = modifier_id

    def __str__(self):
        return "Modifier #{} is already voided.".format(self.modifier_id)

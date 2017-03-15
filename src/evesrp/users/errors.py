class InsufficientPermissionsError(ValueError):
    """Error raised when the :py:class:`User` does not have the correct
    permissions to make that change to a :py:class:`request <Request>`\.
    """
    # PermissionError would've been a nicer name, but it's defined as a builtin
    # type in Python >=3.3
    pass


class AdminPermissionError(InsufficientPermissionsError):
    pass


class InvalidFieldsError(ValueError):

    def __init__(self, *fields):
        self.fields = fields

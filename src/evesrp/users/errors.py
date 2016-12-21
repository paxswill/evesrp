# PermissionError would've been a nicer name, but it's defined as a builtin
# type in Python >=3.3
class InsuffcientPermissionsError(ValueError):
    """Error raised when the :py:class:`User` does not have the correct
    permissions to make that change to a :py:class:`request <Request>`\.
    """
    pass


class AdminPermissionError(InsuffcientPermissionsError):
    pass

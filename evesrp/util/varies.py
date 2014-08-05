from functools import wraps
from flask import make_response
import six


def varies(*on):
    def vary_decorator(func):
        @wraps(func)
        def vary_decorated(*args, **kwargs):
            response = make_response(func(*args, **kwargs))
            response.headers['Vary'] = ', '.join(on)
            return response
        return vary_decorated
    return vary_decorator

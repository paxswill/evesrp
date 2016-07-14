# Heavily inspired by https://github.com/danriti/python-mocked-service
from __future__ import absolute_import
import os.path

from httmock import response, urlmatch


class Resource(object):

    def __init__(self, path):
        base_path = os.path.dirname(__file__)
        base_path = os.path.abspath(base_path)
        if path == '/':
            path = ''
        self.path = os.path.join(base_path, path)

    def get(self):
        if os.path.isdir(self.path):
            filename = os.path.join(self.path, '_index')
        else:
            filename = self.path
        with open(filename, 'rb') as f:
            return f.read()


class RESTService(object):

    def __init__(self, netloc, headers={}):
        self.netloc = netloc
        self.headers = headers

    def __call__(self, url, request):
        path = url.netloc + url.path
        resource = Resource(path)
        method = request.method.lower()
        if not hasattr(resource, method):
            # Signals to HTTMock that we don't handle this method
            return None
        method_method = getattr(resource, method)
        try:
            content = method_method()
        except EnvironmentError:
            return response(404, headers=self.headers, request=request)
        return response(200, content, headers=self.headers, request=request)

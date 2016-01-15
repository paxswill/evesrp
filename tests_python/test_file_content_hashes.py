from __future__ import absolute_import
from bs4 import BeautifulSoup
from .util_tests import TestApp
from evesrp import init_app


class TestFileHashes(TestApp):

    def setUp(self):
        super(TestFileHashes, self).setUp()
        self.client = self.app.test_client()

    def _test_static_files(self, index_resp):
        soup = BeautifulSoup(index_resp.get_data(as_text=True), 'html.parser')
        # Check href for link elements
        for link in soup.find_all('link'):
            static_filepath = link['href']
            if static_filepath[0] != '/':
                continue
            static_resp = self.client.get(static_filepath,
                    follow_redirect=True)
            self.assertEqual(static_resp.static_code, 200)

    def test_hashes_disabled(self):
        # default is hashes off
        index_resp = self.client.get('/')
        self._test_static_files(index_resp)

    def test_hashes_enabled(self):
        self.app.config['SRP_STATIC_FILE_HASH'] = True
        init_app(self.app)
        index_resp = self.client.get('/')
        self._test_static_files(index_resp)

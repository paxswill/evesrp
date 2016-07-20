from __future__ import absolute_import
import pytest
from bs4 import BeautifulSoup


class TestFileHashDisabled(object):

    def _test_static_files(self, index_resp, client):
        soup = BeautifulSoup(index_resp.get_data(as_text=True), 'html.parser')
        # Check href for link elements
        for link in soup.find_all('link'):
            static_filepath = link['href']
            if static_filepath[0] != '/':
                continue
            static_resp = client.get(static_filepath, follow_redirect=True)
            assert static_resp.status_code == 200

    def test_file_hash(self, test_client):
        index_resp = test_client.get('/')
        self._test_static_files(index_resp, test_client)


class TestFileHashEnabled(TestFileHashDisabled):

    @pytest.fixture
    def app_config(self, app_config):
        app_config['SRP_STATIC_FILE_HASH'] = True
        return app_config

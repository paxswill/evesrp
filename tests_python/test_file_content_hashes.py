from __future__ import absolute_import
import pytest
from bs4 import BeautifulSoup


def app_config_id(param):
    test_id = ''
    for key, value in param.items():
        id_value = 'Enabled' if value else 'Disabled'
        test_id += '{}{}'.format(key.capitalize(), id_value)
    return test_id


@pytest.fixture(params=({'hash': False},
                        {'hash': True, 'debug': True},
                        {'hash': True, 'debug': False}), 
                ids=app_config_id,
                autouse=True)
def app_config(app_config, request):
    app_config['SRP_STATIC_FILE_HASH'] = request.param['hash']
    if 'debug' in request.param:
        app_config['DEBUG'] = request.param['debug']
    return app_config


@pytest.fixture
def css_path(test_client):
    index_resp = test_client.get('/', follow_redirects=True)
    soup = BeautifulSoup(index_resp.get_data(as_text=True), 'html.parser')
    css_path = soup.find('link', rel='stylesheet')['href']
    # Sanity check
    assert 'css' in css_path
    return css_path


def test_css(test_client, css_path):
    css_resp = test_client.get(css_path)
    assert css_resp.status_code == 200


def test_css_map(test_client, css_path):
    map_resp = test_client.get(css_path + '.map')
    assert map_resp.status_code == 200


def test_not_found(test_client, css_path):
    unknown_resp = test_client.get(css_path + '.bogus')
    assert unknown_resp.status_code == 404

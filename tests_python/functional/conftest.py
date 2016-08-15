from __future__ import absolute_import

import os
import socket
from six.moves.socketserver import ThreadingMixIn
import threading
import tempfile
from wsgiref import simple_server

from httmock import HTTMock
import pytest
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


# Mark all tests in this package as functional tests
def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_marker('browser') is None:
            if item.fspath is not None and 'functional' in str(item.fspath):
                item.add_marker(pytest.mark.browser)


class ThreadingWSGIServer(ThreadingMixIn, simple_server.WSGIServer):
    
    # So we can use addresses accidentally left in use (like by a badly closing
    # test run).
    allow_reuse_address = True


# Figure out which browser to run, defaulting to just PhantomJS
browsers = os.environ.get('SELENIUM_DRIVER', 'PhantomJS')
if ',' in browsers:
    browsers = browsers.split(',')
else:
    browsers = [browsers]
@pytest.yield_fixture(scope='session', params=browsers)
def driver(request):
    browser = request.param
    # Check to see if we're running on Travis. Explicitly check the value
    # of TRAVIS as tox sets it to an empty string.
    if os.environ.get('TRAVIS') == 'true' and browser != 'PhantomJS':
        username = os.environ['SAUCE_USERNAME']
        access_key = os.environ['SAUCE_ACCESS_KEY']
        default_capabilities = getattr(webdriver.DesiredCapabilities,
                                       browser.upper())
        capabilities = default_capabilities.copy()
        capabilities['tunnel-identifier'] = os.environ['TRAVIS_JOB_NUMBER']
        capabilities['build'] = os.environ['TRAVIS_BUILD_NUMBER']
        capabilities['tags'] = ['CI']
        sauce_url = "{}:{}@localhost:4445".format( username, access_key)
        command_url = "http://{}/wd/hub".format(sauce_url)
        driver = webdriver.Remote(desired_capabilities=capabilities,
                                      command_executor=command_url)
    else:
        driver = getattr(webdriver, browser)()
    # TODO: Add mobile testing as well
    driver.set_window_size(1024, 768)
    yield driver
    driver.quit()


@pytest.yield_fixture
def app_server(evesrp_app, crest, zkillboard):
    # Use port 0 to get a port assigned to us by the OS
    server = simple_server.make_server('', 0, evesrp_app,
                                       server_class=ThreadingWSGIServer)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    with HTTMock(crest, zkillboard):
        yield server
    server.shutdown()
    server_thread.join()


@pytest.fixture
def server_port(app_server):
    port = app_server.socket.getsockname()[1]
    return port


@pytest.fixture
def server_address(app_server):
    host, port = app_server.socket.getsockname()
    if host in ('0.0.0.0', '::'):
        host = 'localhost'
    address = "http://{}:{}".format(host, port)
    return address


@pytest.yield_fixture
def app_config(app_config):
    # If using an SQLite in-memory DB, change it to an actual file DB so it can
    # be shared between threads (I'm not going to try enforcing a recent SQLite
    # version to use shared in-memory databases across threads).
    if app_config['SQLALCHEMY_DATABASE_URI'] in ('sqlite:///', 'sqlite://'):
        _, path = tempfile.mkstemp()
        app_config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(path)
    else:
        path = None
    yield app_config
    if path is not None:
        os.remove(path)


@pytest.yield_fixture
def driver_login(user, driver, server_address):
    driver.get(server_address + '/login/')
    name = driver.find_element_by_id('null_auth_1-name')
    name.send_keys(user.name)
    name.send_keys(Keys.RETURN)
    yield
    # Logout just to keep things clean
    chain = ActionChains(driver)
    right_nav = driver.find_element_by_id('right-nav')
    dropdown = right_nav.find_element_by_class_name('dropdown')
    chain.move_to_element(dropdown)
    # Calling click here to make it visible, acting like a real user
    chain.click(dropdown)
    logout_link = dropdown.find_elements_by_tag_name('a')[-1]
    chain.move_to_element(logout_link)
    chain.click(logout_link)
    chain.perform()
    driver.delete_all_cookies()

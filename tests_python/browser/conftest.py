from __future__ import absolute_import

import os
import re
import socket
from six.moves.socketserver import ThreadingMixIn
from six.moves.http_client import HTTPException
import threading
import tempfile
from wsgiref import simple_server

from httmock import HTTMock
import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.utils import join_host_port


# Mark all tests in this package as functional tests
def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_marker('browser') is None:
            if item.fspath is not None and 'browser' in str(item.fspath):
                item.add_marker(pytest.mark.browser)


class ThreadingWSGIServer(ThreadingMixIn, simple_server.WSGIServer):
    
    # So we can use addresses accidentally left in use (like by a badly closing
    # test run).
    allow_reuse_address = True


def parse_capabilities(capabilities_string):
    if ',' in capabilities_string:
        # If I could drop support for Python2, I could use:
        # browser, *raw_capabilities = capabilities_string.split(',')
        # But I am not dropping Python2 (yet), so we have this little mess for
        # the time being.
        split_caps = capabilities_string.split(',')
        browser, raw_capabilities = split_caps[0], split_caps[1:]
    else:
        browser, raw_capabilities = capabilities_string, ''
    requested_capabilities = dict([cap.split('=') for cap in raw_capabilities])
    default_capabilities = getattr(webdriver.DesiredCapabilities,
                                   browser.upper())
    capabilities = default_capabilities.copy()
    # Massage some special key/values
    if 'platform' in requested_capabilities:
        platform = requested_capabilities['platform']
        match = re.match(r'Win(\d+)', platform)
        if match is not None:
            platform = 'Windows {}'.format(match.group(1))
        requested_capabilities['platform'] = platform
    capabilities.update(requested_capabilities)
    return capabilities


# Figure out which browser to run, defaulting to just PhantomJS
browsers = os.environ.get('BROWSERS', 'PhantomJS')
if ';' in browsers:
    browsers = browsers.split(';')
else:
    browsers = [browsers]
@pytest.fixture(scope='session', params=browsers)
def driver(request):
    capabilities = parse_capabilities(request.param)
    # tox sets passed variables to an empty string instead of not setting them
    if os.environ.get('WEBDRIVER_URL') != '':
        # Use a local WebDriver Remote is available
        webdriver_url = os.environ.get('WEBDRIVER_URL')
    else:
        webdriver_url = None
    # Configure Travis-based environments
    if os.environ.get('TRAVIS') == 'true':
        # Add some metadata to the tunnel
        capabilities['tunnelIdentifier'] = os.environ['TRAVIS_JOB_NUMBER']
        capabilities['build'] = os.environ['TRAVIS_BUILD_NUMBER']
        capabilities['tags'] = ['CI']
        # Create the URL to use Sauce Connect
        username = os.environ['SAUCE_USERNAME']
        access_key = os.environ['SAUCE_ACCESS_KEY']
        sauce_url = "{}:{}@localhost:4445".format(username, access_key)
        webdriver_url = "http://{}/wd/hub".format(sauce_url)
    # If we have a Remote WebDriver, use it unless we're using PhantomJS. In
    # that case just use a local PhantomJS driver.
    if webdriver_url is not None and \
            capabilities['browserName'] != 'phantomjs':
        driver = webdriver.Remote(desired_capabilities=capabilities,
                                      command_executor=command_url)
    else:
        # There are just enough inconsistencies in spacing/capitalization to
        # make doing this manually the easier way.
        local_drivers = {
            'chrome': webdriver.Chrome,
            'edge': webdriver.Edge,
            'internet explorer': webdriver.Ie,
            'firefox': webdriver.Firefox,
            'opera': webdriver.Opera,
            'phantomjs': webdriver.PhantomJS,
            'safari': webdriver.Safari,
        }
        DriverClass = local_drivers[capabilities['browserName']]
        try:
            driver = DriverClass()
        except WebDriverException as e:
            pytest.skip("Unable to launch local WebDriver {}".format(e))
    # TODO: Add mobile testing as well
    driver.set_window_size(1024, 768)
    yield driver
    # I don't care about WebDriver exceptions when quitting. And we'll get an
    # error as SauceLabs will auto-close the connection after 90s.
    try:
        driver.quit()
    except (WebDriverException, HTTPException):
        pass


@pytest.fixture
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
    joined = join_host_port(host, port)
    address = "http://{}".format(joined)
    return address


@pytest.fixture
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


@pytest.fixture
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

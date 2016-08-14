from __future__ import absolute_import
from __future__ import unicode_literals
import os
import signal
import socket
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from ..util_tests import TestLogin


class TestSelenium(TestLogin):

    @classmethod
    def setUpClass(cls):
        browser = os.environ.get('SELENIUM_DRIVER', 'PhantomJS')
        # Check to see if we're running on Travis. Explicitly check the value
        # of TRAVIS as tox sets it to an empty string.
        if os.environ.get('TRAVIS') == 'true':
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
            cls.driver = webdriver.Remote(desired_capabilities=capabilities,
                                          command_executor=command_url)
        else:
            cls.driver = getattr(webdriver, browser)()

    def setUp(self):
        super(TestSelenium, self).setUp()
        self.child_id = os.fork()
        if self.child_id == 0:
            self.app.run(port=5555)

    def tearDown(self):
        os.kill(self.child_id, signal.SIGTERM)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def add_permissions(self):
        # The DB is shared between the forked process and this one
        with self.app.test_request_context():
            # "Normal User" has the pilot "Paxswill"
            paxswill = Pilot(self.normal_user, 'Paxswill', 570140137)
            # "Admin User" has the pilot "DurrHurrDurr"
            durrhurrdurr = Pilot(self.admin_user, 'DurrHurrDurr', 1456384556)
            db.session.add_all((paxswill, durrhurrdurr))
            # Add some divisions with varied permissions
            d1 = Division('Division 1')
            d2 = Division('Division 2')
            d3 = Division('Division 3')
            db.session.add_all((d1, d2, d3))
            # Division 1: Normal Submits. Admin Reviews and Pays.
            db.session.add(Permission(d1, PermissionType.submit,
                                      self.normal_user))
            db.session.add(Permission(d1, PermissionType.review,
                                      self.admin_user))
            db.session.add(Permission(d1, PermissionType.pay,
                                      self.admin_user))
            # Division 3: Admin Submits, Reviews and Pays. Normal Audits.
            db.session.add(Permission(d3, PermissionType.submit,
                                      self.admin_user))
            db.session.add(Permission(d3, PermissionType.review,
                                      self.admin_user))
            db.session.add(Permission(d3, PermissionType.pay,
                                      self.admin_user))
            db.session.add(Permission(d3, PermissionType.audit,
                                      self.normal_user))
            # Division 2: Normal Reviews and Pays. Admin Submits.
            db.session.add(Permission(d2, PermissionType.submit,
                                      self.admin_user))
            db.session.add(Permission(d2, PermissionType.review,
                                      self.normal_user))
            db.session.add(Permission(d2, PermissionType.pay,
                                      self.normal_user))
            db.session.commit()

    def login_user(self, username):
        self.driver.get('http://localhost:5555/login/')
        name = self.driver.find_element_by_id('null_auth_1-name')
        name.send_keys(username)
        name.send_keys(Keys.RETURN)

    def logout(self):
        right_nav = self.driver.find_element_by_id('right-nav')
        dropdown = right_nav.find_element_by_class_name('dropdown')
        # Calling click here to make it visible, acting like a real user
        dropdown.click()
        logout_link = dropdown.find_elements_by_tag_name('a')[-1]
        logout_link.click()

from selenium.webdriver.common.keys import Keys
from .util import TestSelenium


class TestLogin(TestSelenium):

    def setUp(self):
        super(TestLogin, self).setUp()
        self.driver.get('http://localhost:5555/login/')

    def tearDown(self):
        self.logout()

    def test_login_button(self):
        # Test that when logged out, there is only a login button
        navbar = self.driver.find_element_by_id('eve-srp-navbar-collapse')
        buttons = navbar.find_elements_by_tag_name('li')
        self.assertEqual(len(buttons), 1)

    def test_ui_elements_presence(self):
        tab_area = self.driver.find_element_by_id('login-tabs')
        tabs = tab_area.find_elements_by_tag_name('li')
        # util_tests.TestLogin (which TestSelenium inherits from) defines two
        # active AuthMethods.
        self.assertEqual(len(tabs), 2)
        panel = self.driver.find_element_by_id('null_auth_1')
        inputs = panel.find_elements_by_tag_name('input')
        # 2 for the two actual inputs defined in NullAuthForm, and 1 for the
        # CSRF token automatically inserted.
        self.assertEqual(len(inputs), 3)

    def _test_logged_in(self):
        navbar = self.driver.find_element_by_id('eve-srp-navbar-collapse')
        dropdown = navbar.find_element_by_class_name('dropdown')
        dropdown_links = dropdown.find_elements_by_tag_name('a')
        user_name = dropdown_links[0].text
        self.assertEqual(user_name, 'Admin User')

    def test_login_button_click(self):
        name = self.driver.find_element_by_id('null_auth_1-name')
        name.send_keys('Admin User')
        button = self.driver.find_element_by_id('null_auth_1-submit')
        button.click()
        self._test_logged_in()

    def test_login_return(self):
        name = self.driver.find_element_by_id('null_auth_1-name')
        name.send_keys('Admin User')
        name.send_keys(Keys.RETURN)
        self._test_logged_in()

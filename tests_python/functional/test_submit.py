from selenium.webdriver.common.keys import Keys
from .util import TestSelenium


class TestSubmit(TestSelenium):

    def setUp(self):
        super(TestSubmit, self).setUp()
        self.add_permissions()

    def test_division_dropdown_single(self):
        self.login_user('Normal User')
        submit_button = self.driver.find_element_by_partial_link_text('Submit')
        submit_button.click()
        division_select = self.driver.find_element_by_id('division')
        division_options = division_select.find_elements_by_tag_name('option')
        self.assertEqual(len(division_options), 1)
        self.assertFalse(division_select.is_enabled())
        self.logout()

    def test_division_dropdown_multiple(self):
        self.login_user('Admin User')
        submit_button = self.driver.find_element_by_partial_link_text('Submit')
        submit_button.click()
        division_select = self.driver.find_element_by_id('division')
        division_options = division_select.find_elements_by_tag_name('option')
        self.assertEqual(len(division_options), 2)
        self.assertTrue(division_select.is_enabled())
        self.logout()

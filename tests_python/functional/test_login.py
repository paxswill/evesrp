import pytest
from selenium.webdriver.common.keys import Keys


pytestmark = pytest.mark.usefixtures('user')


# Override the user_role fixture to just give normal users
@pytest.fixture
def user_role():
    # Returning Admin jsut to mix things up, and to reuse already written
    # tests.
    return 'Admin'


@pytest.fixture(autouse=True)
def get_login(driver, server_address):
    driver.delete_all_cookies()
    driver.get(server_address + '/login/')


def test_login_button(driver):
    # Test that when logged out, there is only a login button
    navbar = driver.find_element_by_id('eve-srp-navbar-collapse')
    buttons = navbar.find_elements_by_tag_name('li')
    assert len(buttons) == 1


def test_ui_elements_presence(driver):
    tab_area = driver.find_element_by_id('login-tabs')
    tabs = tab_area.find_elements_by_tag_name('li')
    # There are two authmethods defined in the base app_config fixture
    assert len(tabs) == 2
    panel = driver.find_element_by_id('null_auth_1')
    inputs = panel.find_elements_by_tag_name('input')
    # 2 for the two actual inputs defined in NullAuthForm, and 1 for the
    # CSRF token automatically inserted.
    assert len(inputs) == 3


def _test_logged_in(web_driver):
    navbar = web_driver.find_element_by_id('eve-srp-navbar-collapse')
    dropdown = navbar.find_element_by_class_name('dropdown')
    dropdown_links = dropdown.find_elements_by_tag_name('a')
    user_name = dropdown_links[0].text
    assert user_name == 'Admin User'


def test_login_button_click(driver):
    name = driver.find_element_by_id('null_auth_1-name')
    name.send_keys('Admin User')
    button = driver.find_element_by_id('null_auth_1-submit')
    button.click()
    _test_logged_in(driver)


def test_login_return(driver):
    name = driver.find_element_by_id('null_auth_1-name')
    name.send_keys('Admin User')
    name.send_keys(Keys.RETURN)
    _test_logged_in(driver)

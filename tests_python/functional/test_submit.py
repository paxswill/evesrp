import pytest
from selenium.webdriver.support.ui import Select
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import Division, Permission, Pilot


pytestmark = pytest.mark.usefixtures('user')


@pytest.fixture(autouse=True)
def add_permissions(user, request_context):
    d1 = Division('Division One')
    d2 = Division('Division Two')
    if user.admin:
        db.session.add(Permission(d1, PermissionType.submit, user))
        db.session.add(Permission(d2, PermissionType.submit, user))
    else:
        db.session.add(Permission(d1, PermissionType.submit, user))
    db.session.commit()


def test_division_dropdown(driver, driver_login, user):
    submit_button = driver.find_element_by_partial_link_text('Submit')
    submit_button.click()
    division_select = driver.find_element_by_id('division')
    division_options = division_select.find_elements_by_tag_name('option')
    if user.admin:
        assert len(division_options) == 2
        assert division_select.is_enabled()
    else:
        assert len(division_options) == 1
        assert not division_select.is_enabled()


@pytest.mark.parametrize('details', (None, 'Some details'), ids=('NoDetails',
                                                                 'Details'))
@pytest.mark.parametrize('killmail_url',
                         ('https://zkillboard.com/kill/30290604/',
                          ('http://crest-tq.eveonline.com/killmails/30290604/'
                           '787fb3714062f1700560d4a83ce32c67640b1797/'),
                          'http://google.com'),
                         ids=('zKillboard', 'CREST', 'Invalid'))
def test_submit(driver, driver_login, user, details, killmail_url):
    Pilot(user, 'CCP Foxfour', 92168909)
    db.session.commit()
    # Go to the submit page (we're logged in by the driver_login fixture)
    driver.find_element_by_partial_link_text('Submit').click()
    submit_url = driver.current_url
    url_field = driver.find_element_by_id('url')
    url_field.send_keys(killmail_url)
    if details is not None:
        details_field = driver.find_element_by_id('details')
        details_field.send_keys(details)
    division_select = Select(driver.find_element_by_id('division'))
    # Select the second division for the admin user.
    if user.admin:
        division_select.select_by_visible_text('Division Two')
    else:
        division_select.select_by_visible_text('Division One')
    driver.find_element_by_id('submit').click()
    if 'google' in killmail_url:
        assert driver.current_url == submit_url
    elif details is None:
        assert driver.current_url == submit_url
        assert 'This field is required' in driver.page_source
    else:
        assert '30290604' in driver.current_url

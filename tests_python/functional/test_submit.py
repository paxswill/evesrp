import pytest
from selenium.webdriver.common.keys import Keys
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import Division, Permission


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

import pytest
from evesrp import db
from evesrp.auth import PermissionType
from evesrp.auth.models import Division, Permission, Pilot


def add_comment(web_session, comment):
    note_field = web_session.find_element_by_id('note')
    comment_button = web_session.find_element_by_id('comment')
    note_field.send_keys(comment)
    comment_button.click()


def test_add_comment(web_session, server_address, driver_login, srp_request,
                     user):
    web_session.get('{}/request/{}/'.format(server_address, srp_request.id))
    actions_list = web_session.find_element_by_id('actionList')
    actions = actions_list.find_elements_by_class_name('list-group-item')
    assert len(actions) == 0
    comment = "A comment."
    add_comment(web_session, comment)
    actions_list = web_session.find_element_by_id('actionList')
    actions = actions_list.find_elements_by_class_name('list-group-item')
    assert len(actions) == 1
    comment_p = actions[0].find_element_by_tag_name('p')
    assert comment_p.text == comment

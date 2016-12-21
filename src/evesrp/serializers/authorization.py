import json
from .datetime import ISOTimestampEncoder
from .enum import EnumEncoder


class EntityEncoder(json.JSONEncoder):

    def default(self, o):
        try:
            return {
                "name": o.name,
                "id": o.id_,
            }
        except AttributeError:
            return super(EntityEncoder, self).default(o)


class UserEncoder(EntityEncoder):

    def default(self, o):
        try:
            return {
                "name": o.name,
                "id": o.id_,
                "admin": o.admin,
            }
        except AttributeError:
            return super(UserEncoder, self).default(o)


class DivisionEncoder(json.JSONEncoder):

    def default(self, o):
        try:
            return {
                "name": o.name,
                "id": o.id_,
            }
        except AttributeError:
            return super(DivisionEncoder, self).default(o)


# Child of EnumEncoder to encode PermissionTypes correctly
class PermissionEncoder(EnumEncoder):

    def default(self, o):
        try:
            return {
                "entity_id": o.entity_id,
                "division_id": o.division_id,
                "type": o.type_
            }
        except AttributeError:
            return super(PermissionEncoder, self).default(o)


# Child of ISOTimestampEncoder to format timestamps
class NoteEncoder(ISOTimestampEncoder):

    def default(self, o):
        try:
            return {
                "contents": o.contents,
                "timestamp": o.timestamp,
                "id": o.id_,
                "subject_id": o.subject_id,
                "submitter_id": o.submitter_id,
            }
        except AttributeError:
            return super(NoteEncoder, self).default(o)

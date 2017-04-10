import decimal

import graphene
import six


if six.PY3:
    unicode = str


class Decimal(graphene.types.Scalar):
    
    @staticmethod
    def serialize(num):
        return unicode(num)

    @staticmethod
    def parse_literal(node):
        if isinstance(node, graphene.language.ast.StringValue):
            return decimal.Decimal(node.value)

    @staticmethod
    def parse_value(value):
        return decimal.Decimal(value)

******
Models
******

.. py:module:: evesrp.models

.. autoclass:: ActionType

    An :py:class:`~.Enum` for representing the types of :py:class:`Action`\s
    performed on a :py:class:`Request` in addition to the
    :py:attr:`~Request.status` of a :py:class:`Request`.

    .. py:attribute:: statuses

        A :py:class:`frozenset` of all of the single :py:class:`ActionType`
        members that also double as statuses for :py:class:`Request`\s.

    .. py:attribute:: finalized

        A :py:class:`frozenset` of the :py:class:`ActionType`\s that are
        terminal states for a :py:class:`Request` (:py:attr:`paid` and
        :py:attr:`rejected`).

    .. py:attribute:: pending

       A :py:class:`frozenset` of :py:class:`ActionType`\s for
       :py:class:`Request`\s that require further action to be put in a
       :py:attr:`finalized` state.

.. autoexception:: StatusError
    :exclude-members: __weakref__

.. autoexception:: SRPPermissionError
    :exclude-members: __weakref__

.. autoclass:: Action
    :exclude-members: request_id, user_id
    :show-inheritance:

.. autoclass:: Modifier
    :exclude-members: request_id, user_id, voided_user_id
    :show-inheritance:

    .. py:attribute:: voided

        Boolean of whether this modifier has been voided or not.

        This property is available as a
        :py:class:`~sqlalchemy.ext.hybrid.hybrid_property`, so it can be used
        natively in SQLAlchemy queries.

.. autoclass:: AbsoluteModifier

.. autoclass:: RelativeModifier

.. autoclass:: Request
    :exclude-members: submitter_id, division_id, pilot_id
    :show-inheritance:

    .. py:attribute:: payout

    The total payout of this request taking all active :py:attr:`modifiers`
    into account.

    In calculating the total payout, all
    :py:class:`absolute modifiers <AbsoluteModifier>` along with the
    :py:attr:`base_payout` are summed. This is then multipled by the sum of
    all of the :py:class:`relative modifiers <RelativeModifier>` plus 1.
    This property is a read-only
    :py:class:`~sqlalchemy.ext.hybrid.hybrid_property`, so it can be used
    natively in SQLAlchemy queries.

    .. py:attribute:: finalized

    Boolean of if this request is in a :py:attr:`~ActionType.finalized` state.
    Also a read-only :py:class:`~sqlalchemy.ext.hybrid.hybrid_property` so it
    can be used natively in SQLAlchemy queries.


Killmail Handling
=================

.. py:currentmodule:: evesrp.killmail

EVE-SRP relies on outside sources for its killmail information. Whether that
source is CREST, zKillboard, or some private killboard does not matter, there
just has to be some sort of access to the information somehow. Included with
EVE-SRP is support for CREST verified killmails, and the building blocks for
support for zKillboard based killboards.

The interface for :py:class:`Killmail` is fairly simple. It
provides a number of attributes, and for those that correspond to in-game
entities, it also provides their ID number. The default implementation has all
values set to ``None``. :py:class:`CRESTMail` is a complete
implementation, offering the character, corporation, alliance, and ship type
along with the ID numbers for each. As CREST killmail links are API verified as
a matter of course, the :py:attr:`Killmail.verified` attribute
is permanently set to ``True``. :py:class:`ZKillmail` is a
near-complete implementation using zKillboard based killboards.
The zKillboard API does not return the ship type
name, only the ID, so to provide the name lookup there are a pair of mixin
classes that can provide :py:attr:`Killmail.ship` given
:py:attr:`Killmail.ship_id` exists.
:py:class:`EveMDShipNameMixin` will look up the ship name
using the `eve-marketdata.com <http://eve-marketdata.com/>`_ API. This can be a
slow process, and is dependent on the web server having access to their
website. :py:func:`~evesrp.killmail.SQLShipMixin` provides an alternative
method of mapping ship ID numbers to names. If you already have a database with
the static data export, this is the preferred method. You will need a DBAPI 2.0
compatible driver for your particular database, but support for most databases
should be available by default.

Practical Example
*****************

This example demonstrates how you can combine :py:func:`SQLShipMixin` to
provide :py:attr:`~Killmail.ship` to :py:class:`ZKillmail`::

    from evesrp.killmail import ZKillmail, SQLShipMixin

    class SQLZKillmail(ZKillmail, SQLShipMixin('sqlite:///rubicon.sqlite')): pass

API
***

.. py:module:: evesrp.killmail

.. autoclass:: Killmail
    :exclude-members: __weakref__

.. autoclass:: ZKillmail
    :show-inheritance:

.. autoclass:: CRESTMail
    :show-inheritance:

.. autoclass:: RequestsSessionMixin
    :exclude-members: __weakref__

.. autoclass:: EveMDShipNameMixin
    :show-inheritance:

.. autofunction:: SQLShipMixin

.. autofunction:: ShipURLMixin

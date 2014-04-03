Killmail Handling
=================

EVE-SRP relies on outside sources for its killmail information. Whether that
source is CREST, zKillboard, or some private killboard does not matter, there
just has to be some sort of access to the information somehow. Included with
EVE-SRP is support for CREST verified killmails, and the building blocks for
support for zKillboard based killboards.

The interface for :py:class:`~evesrp.killmail.Killmail` is fairly simple. It
provides a number of attributes, and for those that correspond to in-game
entities, it also provides their ID number. The default implementation has all
values set to ``None``. :py:class:`~evesrp.killmail.CRESTMail` is a complete
implementation, offering the character, corporation, alliance, and ship type
along with the ID numbers for each. As CREST killmail links are API verified as
a matter of course, the :py:attr:`~evesrp.killmail.Killmail.verified` attribute
is permanently set to ``True``. :py:class:`~evesrp.killmail.ZKillmail` is a
near-complete implementation. The zKillboard API does not return the ship type
name, only the ID. To provide the name lookup, there are a pair of mixin classes
that can provide :py:attr:`~evesrp.killmail.Killmail.ship` given
:py:attr:`~evesrp.killmail.Killmail.ship_id` exists.
:py:class:`~evesrp.killmail.EveMDShipNameMixin` will look up the ship name
using the `eve-marketdata.com <http://eve-marketdata.com/>` API. This can be a
slow process, and is dependent on the web server having access to their
website. :py:class:`~evesrp.killmail.SQLShipNameMixin` provides an alternative
method of mapping ship ID numbers to names. If you already have a database with
the static data export, this is the preferred method. You will need a DBAPI 2.0
compatible driver for your particular database, but support for most databases
should be available by default.

Practical Example
*****************

This example shows how to configure the SQL ship name mapper and how to create
use it to provide the :py:attr:`ship` attribute.::

    import sqlite3
    from evesrp.killmail import ZKillmail, SQLShipNameMixin

    SQLShipNameMixin.driver = sqlite3
    SQLShipNameMixin.connect_args = 'rubicon.sqlite'

    class SQLZKillmail(ZKillmail, SQLShipNameMixin): pass

API
***

.. py:module:: evesrp.killmail

.. autoclass:: Killmail
    :members:

.. autoclass:: ZKillmail
    :members:

.. autoclass:: CRESTMail
    :members:

.. autoclass:: RequestsSessionMixin
    :members:

.. autoclass:: EveMDShipNameMixin
    :members:

.. autofunction:: SQLShipMixin

*****************
Killmail Handling
*****************

.. py:currentmodule:: evesrp.killmail

EVE-SRP relies on outside sources for its killmail information. Whether that
source is CREST, zKillboard, or some private killboard does not matter, there
just has to be some sort of access to the information somehow. Included with
EVE-SRP is support for CREST verified killmails and zKillboard based
killboards.

The interface for :py:class:`Killmail` is fairly simple. It
provides a number of attributes, and for those that correspond to in-game
entities, it also provides their ID number. The default implementation has all
values set to ``None``. Two implementations for creating a :py:class:`Killmail`
from a URL are provided: :py:class:`CRESTMail` is created from a CREST external
killmail link, and :py:class:`ZKillmail` is created from a `zKillboard
<https://zkillboard.com>`_ details link.

Extension Example
=================

The intent of having killmails handled in a separate class was for
administrators to be able to have customized behavior. As an example, here's a
:py:class:`Killmail` subclass that will link the ship name to the Eve-Online
wiki page for that ship, and only accept killmails from the `TEST Alliance
killboard <https://zkb.pleaseignore.com/>`_. ::

    from evesrp.killmail import ZKillmail, ShipURLMixin
    
    
    eve_wiki_url = 'https://wiki.eveonline.com/en/wiki/{name}'
    EveWikiMixin = ShipURLMixin(eve_wiki_url)
    
    
    class TestZKillmail(ZKillmail, EveWikiMixin):
        def __init__(self, *args, **kwargs):
            super(TestZKillmail, self).__init__(*args, **kwargs)
            if self.domain not in ('zkb.pleaseignore.com', 'kb.pleaseignore.com'):
                raise ValueError("This killmail is from the wrong killboard.")

API
===

.. py:module:: evesrp.killmail

.. autoclass:: Killmail
    :exclude-members: __weakref__

.. autoclass:: ZKillmail
    :show-inheritance:

    .. py:attribute:: domain

        The domain name of this killboard.

.. autoclass:: CRESTMail
    :show-inheritance:

.. autoclass:: RequestsSessionMixin
    :exclude-members: __weakref__

.. autoclass:: ShipNameMixin
    :exclude-members: __weakref__

.. autoclass:: LocationMixin
    :exclude-members: __weakref__

.. autofunction:: ShipURLMixin

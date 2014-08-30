*****************
Killmail Handling
*****************

.. py:currentmodule:: evesrp.killmail

EVE-SRP relies on outside sources for its killmail information. Whether that
source is CREST, zKillboard, or some private killboard does not matter, there
just has to be some sort of access to the information.

The interface for :py:class:`Killmail` is fairly simple. It
provides a number of attributes, and for those that correspond to in-game
entities, it also provides their ID number. The default implementation has all
values set to ``None``. If a killmail is invalid in some way, it can be
signaled either by raising a :py:exc:`ValueError` or :py:exc:`LookupError` in
the killmail's :py:meth:`~Killmail.__init__` method or by defining a
:py:attr:`Killmail.verified` property and returning ``False`` from it when the
killmail is invalid.

Two implementations for creating a :py:class:`Killmail`
from a URL are included: :py:class:`CRESTMail` is created from a CREST external
killmail link, and :py:class:`ZKillmail` is created from a `zKillboard
<https://zkillboard.com>`_ details link.

Extension Examples
==================

The reasoning behind having killmails handled in a separate class was for
administrators to be able to customize behavior. Here're a few useful snippets
that may be useful for your situation.

Restricting Valid zKillboards
-----------------------------

:py:class:`ZKillmail` by default will accept any link that looks and acts like
a zKillboard instance. It does *not* restrict itself to any particular domain
name, but it makes allowances for this common requirement. ::

    from evesrp.killmail import ZKillmail


    class OnlyZKillboard(ZKillmail):
        def __init__(self, *args, **kwargs):
            super(TestZKillmail, self).__init__(*args, **kwargs)
            if self.domain != 'zkillboard.com':
                raise ValueError(u"This killmail is from the wrong killboard.")

Submitting CREST Links to zKillboard
------------------------------------

To streamline the process for users, you can accept CREST killmail links and
then submits them to zKillboard.com and uses the new zKillboard.com link as the
canonical URL for the request. ::

    from decimal import Decimal
    from flask import Markup
    from evesrp.killmail import CRESTMail


    class SubmittedCRESTZKillmail(CRESTMail):
        """Accepts and validates CREST killmail links, but submits them to
        ZKillboard and substitutes the zKB link in as the canonical link
        """

        def __init__(self, url, **kwargs):
            # Let CRESTMail validate the CREST link
            super(self.__class__, self).__init__(url, **kwargs)
            # Submit the CREST URL to ZKillboard
            resp = self.requests_session.post('https://zkillboard.com/post/',
                    data={'killmailurl': url})
            # Use the URL we get from ZKillboard as the new URL (if it's successful).
            if self.kill_id in resp.url:
                self.url = resp.url
            else:
                # Leave the CREST URL as-is and finish
                return
            # Grab zkb's data from their API
            api_url = ('https://zkillboard.com/api/no-attackers/'
                       'no-items/killID/{}').format(self.kill_id)
            zkb_api = self.requests_session.get(api_url)
            retrieval_error = LookupError(u"Error retrieving killmail data (zKB): {}"
                    .format(zkb_api.status_code))
            if zkb_api.status_code != 200:
                raise retrieval_error
            try:
                json = zkb_api.json()
            except ValueError as e:
                raise retrieval_error
            try:
                json = json[0]
            except IndexError as e:
                raise LookupError(u"Invalid killmail: {}".format(url))
            # Recent versions of zKillboard calculate a loss' value.
            try:
                self.value = Decimal(json[u'zkb'][u'totalValue'])
            except KeyError:
                self.value = Decimal(0)

        description = Markup(u'A CREST external killmail link that will be '
                             u'automatically submitted to <a href="https://'
                             u'zkillboard.com">zKillboard.com</a>.')

Setting Base Payouts from a Spreadsheet
---------------------------------------

If you have standardized payout values in a Google spreadsheet, you can set
:py:attr:`Request.base_payout <evesrp.models.Request.base_payout>` to the values in
this spreadsheet. This is assuming your spreadsheet is set up with ship hull
names in one column and payouts in another column. Both Columns need to have a
header ('Hull' and 'Payout' in the example below). This uses the
`Google Data Python Client <https://code.google.com/p/gdata-python-client/>`_
which only supports Python 2, and can be installed with ``pip install
gdata``. ::

    import gdata.spreadsheets.client
    from decimal import Decimal


    # patch the spreadsheet's client to use the public feeds
    gdata.spreadsheets.client.PRIVATE_WORKSHEETS_URL = \
            gdata.spreadsheets.client.WORKSHEETS_URL
    gdata.spreadsheets.client.WORKSHEETS_URL = ('https://spreadsheets.google.com/'
                                                'feeds/worksheets/%s/public/full')
    gdata.spreadsheets.client.PRIVATE_LISTS_URL = \
            gdata.spreadsheets.client.LISTS_URL
    gdata.spreadsheets.client.LISTS_URL = ('https://spreadsheets.google.com/feeds/'
                                           'list/%s/%s/public/full')


    class SpreadsheetPayout(ZKillmail):

        # The spreadsheet's key
        # (https://docs.google.com/spreadsheets/d/THE_PART_HERE/edit).
        # Make sure the spreadsheet has been published (File->Publish to web...)
        spreadsheet_key = 'THE_PART_HERE'

        # The name of the worksheet with the payouts
        worksheet_name = 'Payouts'

        # The header for the hull column (always lowercase, the Google API
        # lowercases it).
        hull_key = 'hull'

        # And the same for the payout column
        payout_key = 'payout'

        client = gdata.spreadsheets.client.SpreadsheetsClient()

        @property
        def value(self):
            # Find the worksheet
            sheets = self.client.get_worksheets(self.spreadsheet_key)
            for sheet in sheets.entry:
                if sheet.title.text == self.worksheet_name:
                    worksheet_id = sheet.get_worksheet_id()
                    break
            else:
                return Decimal('0')
            # Read the worksheet's data
            lists = self.client.get_list_feed(self.spreadsheet_key, worksheet_id,
                    query=gdata.spreadsheets.client.ListQuery(sq='{}={}'.format(
                            self.hull_key, self.ship)))
            for entry in lists.entry:
                return Decimal(entry.get_value(self.payout_key))
            return Decimal('0')

Developer API
=============

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

**********
Javascript
**********

The following documentation is directed towards people developing the front-end
for EVE-SRP. These functions should not be used by end-users, and are purely an
implementation detail.

Utilities
=========

.. js:function:: month(month_int)

    Convert an integer representing a month to the three letter abbreviation.

    :param int month_int: An integer (0-11) representing a month.
    :returns: The three letter abbreviation for that month.
    :rtype: string

.. js:function:: padNum(num, width)

    Pad a number with leading 0s to the given width.

    :param int num: The number to pad.
    :param int width: The width to pad ``num`` to.
    :returns: ``num`` padded to ``width`` with 0s.
    :rtype: string

.. js:function:: pageNumbers(num_pages, current_page[, options])

    Return an array of page numbers, skipping some of them as configured by the
    options argument. This function should be functionally identical to
    Flask-SQLAlchemy's
    :py:meth:`Pagination.iter_pages\
    <flask_sqlalchemy.Pagination.iter_pages>`
    (including in default arguments). One deviation is that this function uses
    0-indexed page numbers instead of 1-indexed, to ease compatibility with
    PourOver. Skipped numbers are represented by ``null``.

    :param int num_pages: The total number of pages.
    :param int current_page: The index of the current page.
    :param options: An object with vonfiguration values for where to sjip
        numbers. Keys are ``left_edge``, ``left_current``, ``right_current``,
        and ``right_edge``. The default values are 2, 2, 5 and 2 respectively.
    :returns: The page numbers to be show, in order.
    :rtype: An array on integers (and ``null``).

.. js:function:: pager_a_click(ev)

    Event callback for pager links. It intercepts the event and changes the
    current PourOver view to reflect the new page.

    :param event ev: The event object.

PourOver
========

.. js:class:: RequestsView(name, collection)

    An extension of PourOver.View with a custom ``render`` function recreating
    a table of :py:class:`~.models.Request`\s with the associated pager.

.. js:function:: addRequestSorts(collection)

    Add sorts for :py:class:`~.models.Request` attributes to the given
    PourOver.Collection.

    :param collection: A collection of requests.
    :type collection: PourOver.Collection

.. js:function:: addRequestFilters(collection)

    Add filters for :py:class:`~.models.Request` attributes to the given
    PourOver.Collection.

    :param collection: A collection of requests.
    :type collection: PourOver.Collection

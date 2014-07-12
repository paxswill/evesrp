************
External API
************

EVE-SRP provides read-only access to requests you can access to external
applications. Two formats are supported, XML and JSON.

API Keys
========

The first step to using the external API is to create an API key from your
personal page. Click the "Create API Key" button, and a key will be generated.

.. image:: images/create_api_key.png

You can revoke API keys at any time by clicking the "X" in the "Remove" column.
The key is the string of letters and numbers and can be copied to your
clipboard by clicking on it (requires Flash).

To use the API key, provide it as a query string along with the desired format.
The field name for the key is ``apikey`` and the field name for the format is
``fmt``. Valid values for the format are ``json`` and ``xml``.

Endpoints
=========

The URLs for the API endpoints are the same ones you access normally, just with
the api key and a format specifier. For example, if you wanted to access your
list of personal requests in JSON, the URL would look something like
``http://example.com/request/personal/?apikey=dVbP0_SCPS12LnLpIZoJvemzeUUOOUErT7nojbJW4_I,&fmt=json``
and the response would be something like this.

.. literalinclude:: code/api-personal.json

To get more detailed information about an item, you can follow the ``href``
attribute. For example, detailed queries about a request will include the full
log of actions performed for that request, as well as a log of modifiers
applied to it.
Here's an example of what a URL like
``http://example.com/request/39861569/?apikey=dVbP0_SCPS12LnLpIZoJvemzeUUOOUErT7nojbJW4_I,&fmt=json``
would respond with.

.. literalinclude:: code/api-detail.json

XML
===

IN addition to the JSON responses (more suited for external applications) there
is also an XML representation that is well suited for importing into
spreadsheets like Google Docs. The above personal request listing would look
like this if requested with the XML format.

.. literalinclude:: code/api-personal.xml
    :language: xml

And a request detail in XML format.

.. literalinclude:: code/api-detail.xml
    :language: xml

RSS
===

Some users might want to have an RSS feed of a list of requests, for example
reviewers might want a feed of pending requests. This can be retrieved by
adding ``rss.xml`` to the end of the URL path, so for pending requests,
something like
``http://example.com/request/personal/rss.xml?apikey=dVbP0_SCPS12LnLpIZoJvemzeUUOOUErT7nojbJW4_I,``

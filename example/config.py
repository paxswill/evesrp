# Should be set to a random string, like the output of os.urandom(24). Needs to
# be a static value that won't change between running the application.
SECRET_KEY = 'random_string'

# Set to the domain name for the app. It fixes things with static files and
# creating external links.
SERVER_NAME = 'srp.example.com'

# Here's an example using a unix socket...
SQLALCHEMY_DATABASE_URI = ('mysql://username:password@hostname/'
                           'database_name?unix_socket=/path/to/mysql.sock')
# ...and here's one using TCP. You should only use one though.
SQLALCHEMY_DATABASE_URI = ('mysql://root:password@hostname:port/'
                           'database_name')

# Used as the HTTP user agent for external API requests (like for CREST and
# zKillboard).
SRP_USER_AGENT_EMAIL = u'admin@example.com'

SRP_AUTH_METHODS = [
    {
        # The 'type' key is an importable path followed by the name of the
        # AuthMethod class, separated either by a dot or a colon.
        'type': 'evesrp.auth.testoauth.TestOAuth',
        # You can specify users to treat a site-wide administrators via the
        # 'admins' key. The value to this key is a list of strings (in the
        # special case of some AuthMethods, integers are also acceptable values
        # for the list.). This is very useful when first setting up the app, as
        # only site-wide administrators can create divisions.
        'admins': [u'Paxswill'],
        # The OAuth consumer key and secret.
        'consumer_key': '123456',
        'consumer_secret': 'abcdef',
        # You can set a different name for an auth method here. This name is
        # shown to users, and should not be changed (and cannot without a lot
        # of manual mucking about in the database).
        'name': u'Test Auth',
    },
    {
        'type': 'evesrp.auth.bravecore.BraveCore',
        # The client's private key
        'client_key': 'foo',
        # Teh server's public key
        'server_key': 'bar',
        # The app's identifier from the Core instance
        'identifier': 'baz',
    },
]

# You can specify custom killmail handling classes here. The instance folder is
# added to the import search path, so the modules can be placed in there.
SRP_KILLMAIL_SOURCES = [
    'custom_killmails.ZeroValueZKillboard',
    'custom_killmails.ZeroValueSubmittedCRESTZKillmail',
]

SRP_SHIP_TYPE_URL_TRANSFORMERS = [
    (u'TEST Reimbursement Wiki',
        'https://wiki.pleaseignore.com/wiki/Reimbursement:{}'),
]

SRP_PILOT_URL_TRANSFORMERS = [
    (u'TEST Auth Page',
        'https://auth.pleaseignore.com/eve/character/{0.id}/'),
]

# You can set a custom name for your site here
SRP_SITE_NAME = 'My SRP'

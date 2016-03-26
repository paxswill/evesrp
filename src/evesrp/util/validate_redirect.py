from flask import request
from six.moves.urllib.parse import urlparse, urljoin


def is_safe_redirect(redirect_url):
    # Fail everything starting with more then one slash
    # http://homakov.blogspot.com/2014/01/evolution-of-open-redirect-vulnerability.html
    if redirect_url.startswith('//'):
        return False
    # Validate given URL to make sure it's still on this server
    current_server = urlparse(request.host_url)
    redirect = urlparse(urljoin(request.host_url, redirect_url))
    return redirect.scheme in ('http', 'https') and \
            redirect.netloc == current_server.netloc

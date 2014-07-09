from flask import render_template, make_response


def xmlify(template, content_type='application/xml', **context):
    """Render a template and modify the ``Content-Type`` header to say it's XML

    The ``template`` and ``context`` arguemnts are identical to those of
    :py:func:`flask.render_template`.

    :param str content_type: The MIME type that the ``Content-Type`` header is
        to be set to. Defaults to ``'application/xml'``.
    """
    content = render_template(template, **context)
    response = make_response(content)
    response.headers['Content-Type'] = content_type
    return response

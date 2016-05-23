import flask 


def jsonify(*args, **kwargs):
    if flask.request.is_xhr:
        # Add flashed messages
        kwargs[u'flashed_messages'] = [{'message': m, 'category':c} for c, m in
                flask.get_flashed_messages(with_categories=True)]
    return flask.jsonify(*args, **kwargs)

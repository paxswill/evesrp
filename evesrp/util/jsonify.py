import flask 


def jsonify(*args, **kwargs):
    messages = [{'message': m, 'category':c} for c, m in
            flask.get_flashed_messages(with_categories=True)]
    return flask.jsonify(*args, flashed_messages=messages, **kwargs)

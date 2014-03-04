import requests
from flask import Response
from flask import stream_with_context
from flask import current_app

def _get_requests_session():
    try:
        return current_app.proxy_requests_session
    except AttributeError:
        current_app.proxy_requests_session = requests.Session()
        return current_app.proxy_requests_session

def proxy(url):
    req = _get_requests_session().get(url)
    return Response(stream_with_context(req.iter_content()),
                    content_type = req.headers['content-type'])

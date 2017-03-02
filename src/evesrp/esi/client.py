import requests
from .bravado.requests_client import RequestsClient
from .bravado.client import SwaggerClient


ESI_SWAGGER_URL = ("https://esi.tech.ccp.is/latest/swagger.json"
                   "?datasource=tranquility")


def create_client(requests_session=None):
    if requests_session is None:
        requests_session = requests.Session()
    swagger_spec = requests_session.get(ESI_SWAGGER_URL).json()
    bravado_http_client = RequestsClient()
    # Replace the requests.Session() created by RequestsClient with our
    # shared session
    bravado_http_client.session = requests_session
    client = SwaggerClient.from_url(ESI_SWAGGER_URL,
                                    http_client=bravado_http_client,
                                    config={'use_models': False})
    return client

"""
authtok.py – Fetch an OAuth2 Bearer token from the DNS API server.
"""

import requests
from urllib.parse import urljoin

# Suppress InsecureRequestWarning for self-signed certificates
try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass

DEFAULT_HOST = "https://10.73.17.95:9443"

# Base64-encoded client_id:client_secret
CLIENT_CREDENTIALS_B64 = (
    "Um1Gak1uWm4wWE5uUTZkN1R2Qnd5RExIZW84ZkY2TWx4d0V3SWFRcjoxVTNsUlI1cXJ3WTl2ZmtsZXk4MU1VS3pTOE1zbGZxZ2F3c0xvNzkxR2Njc2d6RHBiT1EwR25vM2hhaDV0UVpFTDJ1OEFUMmRTSTdjbDY5R3d2ZnFSYkozSVRiZlRuaGR5REhpSVFRd3ZFejk4cUdsMGlKUUNMQ01sWFdkTnJEMg=="
)


def get_bearer(host=None, verify=False):
    """
    Obtain an access_token using the OAuth2 client-credentials flow.

    Parameters
    ----------
    host : str, optional
        Base URL of the API server (default: DEFAULT_HOST).
    verify : bool
        Whether to verify SSL (default False for self-signed certs).

    Returns
    -------
    str
        The Bearer access token.

    Raises
    ------
    RuntimeError
        If the token request fails.
    """
    if host is None:
        host = DEFAULT_HOST

    api_url = urljoin(host, "/oauth2/token/")

    headers = {
        "Authorization": f"Basic {CLIENT_CREDENTIALS_B64}",
    }
    data = {
        "grant_type": "client_credentials",
    }

    resp = requests.post(api_url, headers=headers, data=data, verify=verify)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to get bearer token: {resp.status_code} – {resp.text}"
        )

    json_data = resp.json()
    token = json_data.get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {json_data}")

    return token

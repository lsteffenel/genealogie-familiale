import os

import requests
from django.core.cache import cache
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_URI = "https://oauth2.googleapis.com/token"
MEDIA_ITEMS_URL = "https://photoslibrary.googleapis.com/v1/mediaItems/{}"
CACHE_TTL = 60 * 60 * 6


def _credentials():
    refresh_token = os.environ.get("GOOGLE_PHOTOS_REFRESH_TOKEN")
    client_id = os.environ.get("GOOGLE_PHOTOS_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_PHOTOS_CLIENT_SECRET")
    if not (refresh_token and client_id and client_secret):
        return None
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
    )


def get_media_item_base_url(media_item_id, width=800, height=600):
    if not media_item_id:
        return None
    cache_key = f"gphotos:{media_item_id}:{width}x{height}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    creds = _credentials()
    if creds is None:
        return None
    try:
        creds.refresh(Request())
        response = requests.get(
            MEDIA_ITEMS_URL.format(media_item_id),
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        base_url = response.json().get("baseUrl")
    except Exception:
        return None
    if not base_url:
        return None
    sized_url = f"{base_url}=w{width}-h{height}"
    cache.set(cache_key, sized_url, CACHE_TTL)
    return sized_url

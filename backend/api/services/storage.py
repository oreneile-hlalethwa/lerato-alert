"""Private evidence backup on Cloudinary.

Files are uploaded as type='authenticated', so they can't be opened by a plain link.
The app only ever gets short-lived signed URLs (10 minutes).
"""
import logging
import time
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.conf import settings

log = logging.getLogger('api')
_ready = False


class StorageUnavailable(Exception):
    pass


def _credentials():
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        return settings.CLOUDINARY_CLOUD_NAME, settings.CLOUDINARY_API_KEY, settings.CLOUDINARY_API_SECRET
    if settings.CLOUDINARY_URL:
        u = urlparse(settings.CLOUDINARY_URL)  # cloudinary://key:secret@cloud
        return u.hostname, u.username, u.password
    return None


def configured():
    return _credentials() is not None


def _setup():
    global _ready
    creds = _credentials()
    if not creds:
        raise StorageUnavailable('Cloudinary keys are not set')
    if not _ready:
        cloud, key, secret = creds
        cloudinary.config(cloud_name=cloud, api_key=key, api_secret=secret, secure=True)
        _ready = True


def resource_type_for(kind):
    return 'image' if kind == 'photo' else 'video'   # Cloudinary stores audio under "video"


def upload(fileobj, kind, member_id):
    _setup()
    try:
        res = cloudinary.uploader.upload(
            fileobj,
            resource_type=resource_type_for(kind),
            type='authenticated',
            folder=f'lerato/{member_id}',
            use_filename=False,
            unique_filename=True,
            overwrite=False,
            tags=['lerato-evidence', kind],
        )
    except Exception as exc:
        log.warning('Cloudinary upload failed: %s', exc)
        raise StorageUnavailable(str(exc)) from exc
    return {
        'public_id': res['public_id'],
        'resource_type': res.get('resource_type', resource_type_for(kind)),
        'format': res.get('format', ''),
        'bytes': res.get('bytes', 0),
    }


def signed_url(item, seconds=600):
    _setup()
    return cloudinary.utils.private_download_url(
        item.public_id, item.format, resource_type=item.resource_type,
        type='authenticated', expires_at=int(time.time()) + seconds,
    )


def delete(item):
    if not item.public_id:
        return
    try:
        _setup()
        cloudinary.uploader.destroy(item.public_id, resource_type=item.resource_type, type='authenticated', invalidate=True)
    except Exception as exc:
        log.warning('Cloudinary delete failed: %s', exc)
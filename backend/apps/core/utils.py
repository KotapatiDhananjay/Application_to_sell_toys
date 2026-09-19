def absolute_url(request, url: str) -> str:
    """Turn '/media/x.png' into 'http://host/media/x.png'.

    The React app runs on a different origin than the API, so uploaded-image
    URLs must be absolute. External URLs (http/https) are returned unchanged.
    """
    if not url:
        return ""
    if url.startswith(("http://", "https://")) or request is None:
        return url
    return request.build_absolute_uri(url)
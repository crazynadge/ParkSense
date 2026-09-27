class VisionUnavailableError(Exception):
    """The Vision provider could not produce an extraction (network, timeout, quota, outage).

    Distinct from an unreadable sign: this is our failure, not the photo's, so the
    user is told to retry rather than to retake the picture.
    """

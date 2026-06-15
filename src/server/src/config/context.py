import os


def maps_api_key(request):  # noqa: D401
    """Inject Google Maps API key from environment variable into templates."""
    return {"GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY", "")}

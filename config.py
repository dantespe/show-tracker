from datetime import timedelta
import os


# DEFAULTS
CACHE_FILE = ".cache"
SHOW_FILE = "shows.yaml"
FILM_FILE = "film.yaml"

# Expirations
SHOW_EXPIRATION = timedelta(days=365)
FILM_EXPIRATION = timedelta(days=180)
LAST_UPDATED_EXPIRATION = timedelta(minutes=15)

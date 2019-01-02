#! /usr/bin/env python

from pyextras.cache import EncryptedDiskCache
from datetime import timedelta as td
from todoist.api import TodoistAPI
import yaml
import tmdbsimple as tmdb
import os
import json

from config import (
    CACHE_FILE,
    SHOW_FILE,
    FILM_FILE,
    SHOW_EXPIRATION,
    FILM_EXPIRATION,
    LAST_UPDATED_EXPIRATION
)

API_KEY = os.environ.get("TODOIST_API_KEY")

def load_cache(cache):
    """
        A function that setup the cache. Tries to read CACHE_FILE. If the data
        was corrupted or the file doesn't exists, the cache is initilized.
    """
    try:
        cache.load(CACHE_FILE)
    except:
        cache.add("_films_updated", value=set(), timedelta=td(days=30))
        cache.add("_shows_updated", value=set(), timedelta=td(days=30))
        cache.add("_shows_waiting", value=set(), timedelta=td(days=30))
        cache.add("_films", value=set(), timedelta=td(days=180))
        cache.add("_shows", value=set(), timedelta=td(days=2*365))
        cache.add("_capacities", value=set(), timedelta=SHOW_EXPIRATION)


def append_updated(cache, show, key="_shows_updated"):
    cache.get(key).add(show)

def append_waiting(cache, show, key="_shows_waiting"):
    cache.get(key).add(show)

def append_films(cache, film, key="_films"):
    # CREATE TASK TODO FIXME
    cache.get(key).add(film)

def append_show(cache, show, key="_shows"):
    cache.get(key).add(show)

def add_shows(cache):
    with open(SHOW_FILE, 'r') as stream:
        data = yaml.safe_load(stream)

    reviewed_shows = set()
    for show in data:
        reviewed_shows.add(show['name'])

        added = show.get('added', False)
        waiting = show.get('waiting', False)

        if show['name'] not in cache:
            cache.add(show['name'], value=show, timedelta=SHOW_EXPIRATION)
            append_show(cache, show['name'])

            if not added and not waiting:
                append_updated(cache, show['name'])

        elif (cache.get(show['name'])['season'] != show['season'] or \
            cache.get(show['name'])['episode'] != show['episode']) and\
            not added and not waiting:
            append_updated(cache, show['name'])

        if waiting:
            append_waiting(cache, show['name'])

    for show in cache.get('_shows'):
        if show not in reviewed_shows and cache.isExpired(show):
            cache.remove(show)
            cache.get("_show_waiting").remove(show)
            cache.get("_shows_updated").remove(show)


def add_films(cache):
    with open(FILM_FILE, 'r') as stream:
        data = yaml.safe_load(stream)

    for film in data:
        if film not in cache.get("_films"):
            cache.get("_films_updated").add(film)
            append_films(cache, film)


def searchForFilmId(film, name="original_title"):
    search = tmdb.Search()
    response = search.movie(query=show)

    return (
        response['results'][0][name],
        response['results'][0]['id']
    ) if response['total_results'] else None

def searchForShowId(show, name="name"):
    search = tmdb.Search()
    response = search.tv(query=show)

    return (
        response['results'][0][name],
        response['results'][0]['id']
    ) if response['total_results'] else None


def searchForShowIds(cache):
    for show in cache.get('_shows'):
        if 'id' not in cache.get(show):
            cache.get(show)['id'] = searchForShowId(show)


def read_data(cache):
    add_shows(cache)
    searchForShowIds(cache)
    add_films(cache)


def getTaskForShow(show):
    if show['season'] < 10:
        season = "0%s" % (str(show['season']))
    else:
        season = show['season']

    if show['episode'] < 10:
        episode = "0%s" % (str(show['episode']))
    else:
        episode = show['episode']

    return "{n} S{s}E{e}".format(n=show['name'], s=season, e=episode)


def add_tasks(cache):
    PROJECT_ID = os.environ.get("TODOIST_TV_PROJECT_ID")

    api = TodoistAPI(API_KEY)
    api.sync()

    for show in cache.get("_shows_updated"):
        api.items.add(getTaskForShow(cache.get(show)), PROJECT_ID)
    cache["_shows_updated"] = set()

    for film in cache.get("_films_updated"):
        api.items.add(film, PROJECT_ID)
    cache["_films_updated"] = set()

    api.commit()

def main(cache):
    tmdb.API_KEY = os.environ.get("TMDB_API_KEY_V3")
    read_data(cache)
    add_tasks(cache)

if __name__ == "__main__":
    cache = EncryptedDiskCache("SHOW_TRACKER_ENCRYPTION_KEY")
    load_cache(cache)
    err = None

    try:
        main(cache)
    except Exception as e:
        err = e

    cache.store(CACHE_FILE)

    if err:
        raise err

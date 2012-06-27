from lib.api import eveapi
from django.core.cache import cache
from datetime import datetime

def get_api():
    return eveapi.EVEAPIConnection()

def get_list(ltype, name, **kwargs):
    if kwargs:
        t = [ltype, name]
        t.extend(map(str,kwargs.values()))
        cache_key = ".".join(t)
    else:
        cache_key = ".".join([ltype, name])

    cached_value = cache.get(cache_key)

    if cached_value:
        return cached_value

    api = get_api()
    context = getattr(api, ltype)
    service = getattr(context, name)
    result = service(**kwargs)

    cached_until = datetime.fromtimestamp(result._meta.cachedUntil)
    cache_time = cached_until - datetime.now()
    cache.set(cache_key, result, int(cache_time.total_seconds()))

    return result

def get_list_uncached(ltype, name, **kwargs):
    api = get_api()
    context = getattr(api, ltype)
    service = getattr(context, name)
    result = service(**kwargs)
    return result

if __name__ == '__main__':
    r = get_list('corp', 'CorporationSheet', corporationID=597600789)

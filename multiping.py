#!/usr/bin/env python

from __future__ import print_function
import multiprocessing
import socket
import time


MAX_PING = 5.0  # maximum ping and socket timeout


def get_ping(mirror):
    """Adds 'ping' key with milliseconds to the single mirror info.

    URL is being split by slashes to get the server address.

    Returns:
        a dict with mirror data.
    """
    mirror_socket = socket.socket()
    mirror_socket.settimeout(MAX_PING)
    time_pre = time.time()
    try:
        mirror_socket.connect((mirror['url'].split('/')[2], 80))
        ping = time.time() - time_pre
    except socket.error:
        ping = MAX_PING
    finally:
        mirror_socket.close()
    mirror['ping'] = ping * 1000.0
    return mirror


def get_mirrors_pinged(mirrors, processes=8):
    """ Returns new array of mirrors' dicts with new 'ping' data (float)
    """
    pool = multiprocessing.Pool(processes=processes)
    return pool.map(get_ping, mirrors)


if __name__ == '__main__':
    # For testing and demo
    import json

    mirrors = [
        {
            "url": "http://us2.php.net/get/php-7.0.9.tar.bz2/from/this/mirror",
            "name": "Hurricane Electric",
            "provider": "http://he.net/"
        },
        {
            "url": "http://us3.php.net/get/php-7.0.9.tar.bz2/from/this/mirror",
            "name": "C7 Data Centers",
            "provider": "https://www.c7.com/"
        },
        {
            "url": "http://docs.php.net/get/php-7.0.9.tar.bz2/from/this/mirror",
            "name": "EUKhost",
            "provider": "http://eukhost.com/"
        }
    ]

    mirrors_with_ping = get_mirrors_pinged(mirrors)
    print(json.dumps(mirrors_with_ping, indent=2))

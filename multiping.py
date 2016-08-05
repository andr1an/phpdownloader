#!/usr/bin/env python

import subprocess
import multiprocessing
import re
import os

def ping(ip, count=1):
    """ Uses the system ping command to get speed of ip or domain name
    """
    p_ping = subprocess.Popen(['ping', '-c', str(count), '-W', '1', ip],
                          shell=False,
                          stdout=subprocess.PIPE,
                          stderr=open(os.devnull, 'w'))

    p_ping_out = p_ping.communicate()[0]

    if p_ping.wait() == 0:
        # rtt min/avg/max/mdev = 22.293/22.293/22.293/0.000 ms
        search = re.search(r'rtt min/avg/max/mdev = (.*)/(.*)/(.*)/(.*) ms',
                         p_ping_out, re.M|re.I)

        return float(search.group(2))
    else:
        return 9999.0


def get_ping(mirror):
    """ Calls ping function for 1 dict with mirror data;
        URL is being split by slashes to get only domain name.
        Returns new dict with old data and ping.
    """
    res = mirror
    res["ping"] = ping(mirror["url"].split('/')[2])
    return res


def get_mirrors_pinged(mirrors, processes=8):
    """ Returns new array of mirrors' dicts with new 'ping' data (float)
    """
    pool = multiprocessing.Pool(processes=processes)
    return pool.map(get_ping, mirrors)


if __name__ == '__main__':
    # For testing and demo
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

    import json
    print json.dumps(mirrors_with_ping, indent=2)
    print json.dumps(mirrors, indent=2)

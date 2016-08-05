#!/usr/bin/env python
import os
import sys
import contextlib
import urllib2
from lxml import html
import hashlib

import multiping

import json


BASE_URL = 'http://php.net'
DOWNLOAD_PATH = '/tmp'


def parse_downloads_page(downloads_url):
    """Parses data from php.net downloads page
    Returns:
        [php_mirrors_url, php_filename, php_hash]
    """

    XPATH_BASE = "//div[@class='content-box']/ul/li"

    with contextlib.closing(urllib2.urlopen(downloads_url)) as response:
        tree = html.fromstring(response.read())

        links = tree.xpath(XPATH_BASE + "/a")
        if len(links) > 0:
            php_mirrors_url = BASE_URL + links[0].attrib["href"]
            php_filename = links[0].text_content()

        spans = tree.xpath(XPATH_BASE + "/span[@class='sha256']")
        if len(spans) > 0:
            php_hash = spans[0].text_content()

    return [php_mirrors_url, php_filename, php_hash]


def parse_mirrors_page(mirrors_url):
    """Gets mirrors_url page and parses mirror list from it.
    Retunrs:
        [
            {
                'name':     'Some Mirror Co.',
                'provider': 'http://mirror.org',
                'url':      'http://mirror.org/php.tar.bz2'
            },
            ...
        ]
    """

    mirrors_parsed = []

    with contextlib.closing(urllib2.urlopen(mirrors_url)) as response:
        tree = html.fromstring(response.read())

        mirrors = tree.xpath("//div[@class='entry']")
        for m in mirrors:
            prov_name = m.xpath("div[@class='provider']/a")[0].text_content()
            prov_url = m.xpath("div[@class='provider']/a")[0].attrib["href"]
            php_url = m.xpath("div[@class='url']/a")[0].attrib["href"]
            mirrors_parsed.append({'name': prov_name,
                                   'provider': prov_url,
                                   'url': php_url})
    if len(mirrors_parsed) < 1:
        raise Exception("Can't parse mirrorlist!")

    return mirrors_parsed


def download_php(php_url, php_filename):
    file_temp = urllib2.urlopen(php_url)

    meta = file_temp.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (php_filename, file_size)

    file_size_dl = 0
    block_sz = 8192

    with open(php_filename, "wb") as file_local:
        while True:
            buffer = file_temp.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            file_local.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl,
                                        file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,

    print


def verify_php_hash(php_filename, php_hash):
    print "Verifying SHA256 checksum...",

    file_hash = hashlib.sha256(open(php_filename, 'rb').read()).hexdigest()

    if file_hash == php_hash:
        print 'OK'
        return True
    else:
        print 'FAIL'
        return False


def mirror_speed_key(mirror):
    return mirror["ping"]


def run():
    php_mirrors_url, php_filename, php_hash = parse_downloads_page(BASE_URL +
                                                            '/downloads.php')
    mirrors_parsed = parse_mirrors_page(php_mirrors_url)

    print "Got mirror list..."

    mirrors_pinged = multiping.get_mirrors_pinged(mirrors_parsed, processes=16)
    print "Pinged!"
    mirrors_pinged.sort(key=mirror_speed_key)
    print "Sorted!"
    selected_mirror = mirrors_pinged[0]
    # print "Mirror list:"
    # print json.dumps(mirrors_pinged, indent=2)
    print "Selected mirror:"
    print json.dumps(selected_mirror, indent=2)

    php_filename = os.path.join(DOWNLOAD_PATH, php_filename)

    if not selected_mirror['url']:
        print "Can't download from mirror: \"%s\"!" % selected_mirror['name']
        return 1

    if os.path.isfile(php_filename):
        print "%s already exists!" % php_filename
        if verify_php_hash(php_filename, php_hash):
            print os.path.join(php_filename)
            return 0
        else:
            print 'Wrong checksum! Redownloading...'
            os.remove(php_filename)
    else:
        print "New release found: %s" % php_filename

    download_php(selected_mirror['url'], php_filename)

    if verify_php_hash(php_filename, php_hash):
        print os.path.join(php_filename)
        return 0
    else:
        return 1


if __name__ == '__main__':
    code = run()
    sys.exit(code)

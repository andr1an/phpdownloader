#!/usr/bin/env python
#
# Downloads latest PHP tarballs (one of 'oldstable', 'stable' or 'new'
# release branch).
#

from __future__ import print_function
import os
import sys
import argparse
from contextlib import closing
from operator import itemgetter
import hashlib
import logging

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from lxml import html

from multiping import get_mirrors_pinged


BASE_URL = 'https://php.net'
PHP_STORAGE = '/opt'
PHP_RELEASES_DIV_SKIP = {
    'new': 0,
    'stable': 1,
    'oldstable': 2,
}

logger = logging.getLogger(__name__)
args = None


def parse_downloads_page(downloads_url, php_release='new'):
    """Parses data from php.net downloads page.

    Gets latest .tar.bz2 filename for specified release, its sha256 digest
    and mirrorlist page link.

    Returns:
        [php_mirrors_url, php_filename, php_hash]
    """
    skip_div = PHP_RELEASES_DIV_SKIP[php_release]

    xpath_base = "//div[@class='content-box']/ul/li"

    with closing(urlopen(downloads_url)) as response:
        tree = html.fromstring(response.read())
    links = tree.xpath(xpath_base + "/a")
    spans = tree.xpath(xpath_base + "/span[@class='sha256']")

    if links and spans:
        php_mirrors_url = BASE_URL + links[skip_div * 7].attrib["href"]
        php_filename = links[skip_div * 7].text_content()
        php_hash = spans[skip_div * 3].text_content()
    else:
        raise RuntimeError("Can't parse downloads page!")

    return php_mirrors_url, php_filename, php_hash


def yield_mirrors(mirrors_url):
    """Yields mirrors from mirrors page.

    Yields:
        Dict with mirror data:
        {
            'name':     'Some Mirror Co.',
            'provider': 'http://mirror.org',
            'url':      'http://mirror.org/php.tar.bz2'
        }
    """
    with closing(urlopen(mirrors_url)) as response:
        html_tags = html.fromstring(response.read())
    tag_tree = html_tags.xpath("//div[@class='entry']")

    for tag in tag_tree:
        prov_name = tag.xpath("div[@class='provider']/a")[0].text_content()
        prov_url = tag.xpath("div[@class='provider']/a")[0].attrib["href"]
        php_url = tag.xpath("div[@class='url']/a")[0].attrib["href"]

        yield {'name': prov_name,
               'provider': prov_url,
               'url': php_url}


def download_php(php_url, php_filename):
    """Downloads php_url to php_filename."""
    global args
    global logger

    progress_fmt = '{:>10}  [{:3.2f}%]'

    with closing(urlopen(php_url)) as file_temp:
        meta = file_temp.info()
        file_size = int(meta.get('Content-Length'))
        logger.info('Downloading: %s Bytes: %s', php_filename, file_size)

        file_size_dl = 0
        block_sz = 8192

        with open(php_filename, 'wb') as file_local:
            for buf in iter(lambda: file_temp.read(block_sz), b''):
                file_size_dl += len(buf)
                file_local.write(buf)
                if not args.quiet:
                    status = progress_fmt.format(
                        file_size_dl, file_size_dl * 100. / file_size)
                    status += chr(8) * (len(status) + 1)
                    print(status, end='')

    if not args.quiet:
        print()


def verify_php_hash(php_filename, php_hash):
    """Verifies SHA256 checksum of tarball.

    Returns:
        True or False
    """
    global args
    global logger

    if not args.quiet:
        print('Verifying SHA256 checksum...', end='')

    file_hash = hashlib.sha256(open(php_filename, 'rb').read()).hexdigest()

    if file_hash == php_hash:
        logger.info('OK')
        return True
    else:
        logger.info('FAIL')
        return False


def parse_args(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    php_releases = list(PHP_RELEASES_DIV_SKIP)
    parser.add_argument('-r', '--release',
                        default=php_releases[0],
                        choices=php_releases,
                        help='PHP release branch')
    parser.add_argument('-C', '--directory',
                        default=PHP_STORAGE,
                        help='Target directory')
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='Only print downloaded file name')
    return parser.parse_args(argv)


def main():
    """Checking for latest PHP, downloads (if needed) and checks sha256.

    If the new tarball was downloaded, checks it and prints its filename.
    No download retries will be attempted.

    If tarball already exists, checks it.
    If sum is OK, then prints filename.
    If not, re-downloads it and checks again. Returns 1, if tarball is
    still bad.
    """
    global args
    global logger

    args = parse_args()
    if not args.quiet:
        logger.setLevel(logging.INFO)

    logger.info('Searching for lastest available "%s" PHP release...',
                args.release)

    php_mirrors_url, php_filename, php_hash = parse_downloads_page(
        BASE_URL + '/downloads.php', args.release)

    php_file_target_name = os.path.join(args.directory, php_filename)

    if os.path.isfile(php_file_target_name):
        logger.info('%s already exists!', php_file_target_name)
        if verify_php_hash(php_file_target_name, php_hash):
            print(php_file_target_name)
            return 0
        else:
            logger.info('Wrong checksum! Redownloading...')
            os.remove(php_file_target_name)
    else:
        logger.info('New release found: %s', php_filename)

    logger.info('Choosing mirror...')
    mirrors_pinged = get_mirrors_pinged(yield_mirrors(php_mirrors_url),
                                        processes=16)
    selected_mirror = sorted(mirrors_pinged, key=itemgetter('ping'))[0]
    mirror_name = selected_mirror['name']
    mirror_ping = selected_mirror['ping']
    mirror_provider = selected_mirror['provider']
    mirror_url = selected_mirror['url']

    if not mirror_url:
        print("Can't find URL for mirror \"{}\"!".format(mirror_name))
        return 1

    logger.info('Selected mirror: name=%s, ping=%s, provider=%s, url=%s',
                mirror_name, mirror_ping, mirror_provider, mirror_url)

    download_php(mirror_url, php_file_target_name)

    if verify_php_hash(php_file_target_name, php_hash):
        print(php_file_target_name)
    else:
        print('Failed to download {}'.format(php_filename))
        sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(format='%(message)s', stream=sys.stdout)
    main()

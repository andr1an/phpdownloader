#!/usr/bin/env python2.7
#
# Downloads latest PHP tarballs (one of 'oldstable', 'stable' or 'new'
# release branch).
#

import os
import sys
import json
import argparse
import contextlib
import urllib2
from lxml import html
import hashlib

from multiping import get_mirrors_pinged


BASE_URL = 'http://php.net'
PHP_STORAGE = '/opt'


def parse_downloads_page(downloads_url, php_release='new'):
    """Parses data from php.net downloads page.

    Gets latest .tar.bz2 filename for specified release, its sha256 digest
    and mirrorlist page link.

    Returns:
        [php_mirrors_url, php_filename, php_hash]
    """

    skip_info = {
        'new': 0,
        'stable': 1,
        'oldstable': 2
    }

    skip_div = skip_info[php_release]

    xpath_base = "//div[@class='content-box']/ul/li"

    with contextlib.closing(urllib2.urlopen(downloads_url)) as response:
        tree = html.fromstring(response.read())
        links = tree.xpath(xpath_base + "/a")
        spans = tree.xpath(xpath_base + "/span[@class='sha256']")

        if links and spans:
            php_mirrors_url = BASE_URL + links[skip_div*7].attrib["href"]
            php_filename = links[skip_div*7].text_content()
            php_hash = spans[skip_div*3].text_content()
        else:
            raise Exception("Can't parse downloads page!")

    return php_mirrors_url, php_filename, php_hash

def mirrorlist(tag_tree):
    """Parses mirrors from DIV:entry elements.

    Yields:
        Dict with mirror data:
        {
            'name':     'Some Mirror Co.',
            'provider': 'http://mirror.org',
            'url':      'http://mirror.org/php.tar.bz2'
        }
    """
    for tag in tag_tree:
        prov_name = tag.xpath("div[@class='provider']/a")[0].text_content()
        prov_url = tag.xpath("div[@class='provider']/a")[0].attrib["href"]
        php_url = tag.xpath("div[@class='url']/a")[0].attrib["href"]

        yield {'name': prov_name,
               'provider': prov_url,
               'url': php_url}

def mirror_divs(mirrors_url):
    """Gets mirrors_url page DIV:entry's for future parsing."""
    with contextlib.closing(urllib2.urlopen(mirrors_url)) as response:
        html_tags = html.fromstring(response.read())
        return html_tags.xpath("//div[@class='entry']")


class Application(object):
    """Base class for phpdownloader."""

    def __init__(self):
        # Parsing command line arguments
        argp = argparse.ArgumentParser()

        argp.add_argument('-r', '--release',
                          action='store',
                          default='new',
                          choices=['new', 'stable', 'oldstable'],
                          help="PHP release branch")

        argp.add_argument('-C', '--directory',
                          action='store',
                          default=PHP_STORAGE,
                          help="Target directory")

        argp.add_argument('-q', '--quiet',
                          action='store_true',
                          default=False,
                          help="Only print downloaded file name")

        self.args = argp.parse_args(sys.argv[1:])

    def log(self, message):
        """Prints message, if not in quiet mode."""
        if not self.args.quiet:
            print message


    def download_php(self, php_url, php_filename):
        """Downloads php_url to php_filename."""

        file_temp = urllib2.urlopen(php_url)

        meta = file_temp.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        self.log("Downloading: %s Bytes: %s" % (php_filename, file_size))

        file_size_dl = 0
        block_sz = 8192

        with open(php_filename, "wb") as file_local:
            while True:
                buf = file_temp.read(block_sz)
                if not buf:
                    break

                file_size_dl += len(buf)
                file_local.write(buf)
                if not self.args.quiet:
                    status = r"%10d  [%3.2f%%]" % (
                        file_size_dl, file_size_dl * 100. / file_size)
                    status += chr(8)*(len(status)+1)
                    print status,

        if not self.args.quiet:
            print

    def verify_php_hash(self, php_filename, php_hash):
        """Verifies SHA256 checksum of tarball.

        Returns:
            True or False
        """

        if not self.args.quiet:
            print "Verifying SHA256 checksum...",

        file_hash = hashlib.sha256(open(php_filename, 'rb').read()).hexdigest()

        if file_hash == php_hash:
            self.log('OK')
            return True
        else:
            self.log('FAIL')
            return False


    def run(self):
        """Checking for latest PHP, downloads (if needed) and checks sha256.

        If the new tarball was downloaded, checks it and prints its filename.
        No download retries will be attempted.

        If tarball already exists, checks it.
        If sum is OK, then prints filename.
        If not, re-downloads it and checks again. Returns 1, if tarball is
        still bad.
        """

        self.log("Searching for lastest available '%s' PHP release..."
                 % self.args.release)

        php_mirrors_url, php_filename, php_hash = parse_downloads_page(
            BASE_URL + '/downloads.php', self.args.release)

        php_file_target_name = os.path.join(self.args.directory, php_filename)

        if os.path.isfile(php_file_target_name):
            self.log("%s already exists!" % php_file_target_name)
            if self.verify_php_hash(php_file_target_name, php_hash):
                print php_file_target_name
                return 0
            else:
                self.log('Wrong checksum! Redownloading...')
                os.remove(php_file_target_name)
        else:
            self.log("New release found: %s" % php_filename)

        self.log("Choosing mirror...")
        mirrors_pinged = get_mirrors_pinged(mirrorlist(mirror_divs(
            php_mirrors_url)), processes=16)
        mirrors_pinged.sort(key=lambda m: m['ping'])
        selected_mirror = mirrors_pinged[0]

        if not selected_mirror['url']:
            print "Can't find URL for mirror \"%s\"!" % selected_mirror['name']
            return 1

        self.log("Selected mirror:")
        self.log(json.dumps(selected_mirror, indent=2))

        self.download_php(selected_mirror['url'], php_file_target_name)

        if self.verify_php_hash(php_file_target_name, php_hash):
            print php_file_target_name
            return 0
        else:
            print 'Failed to download', php_filename
            return 1


if __name__ == '__main__':
    sys.exit(Application().run())

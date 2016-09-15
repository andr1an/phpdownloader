# phpdownloader

Automatic PHP tarball downloader written in Python 2.7. I personally use this as a part
of automatic Debian package build system.

* Parses php.net and gets all mirrors for latest PHP tar.bz2-archive.
* Verifies checksum before downloading, skips it if SHA256 is okay
* Verifies checksum after download
* Uses Python [multiprocessing](https://docs.python.org/2/library/multiprocessing.html) module
for parallel pinging of mirrors and uses fastest mirror to download tarball.
* Prints downloaded file path or exits error code

## Usage

    usage: phpdownloader.py [-h] [-r {new,stable,oldstable}] [-C DIRECTORY]
    
    optional arguments:
      -h, --help	help message
    
      -r, --release {new,stable,oldstable}
			Choose PHP release branch (were 7.0, 5.6 and 5.5 on 2016-09-15)
    
      -C, --directory DIRECTORY
			Target directory

# phpdownloader
Automatic PHP tarball downloader written in Python 2.7

* Parses php.net and gets all mirrors for latest PHP 7 tarball.
* Uses Python [multiprocessing](https://docs.python.org/2/library/multiprocessing.html) module
for parallel pinging of mirrors and uses fastest mirror to download tarball.
* Verifies checksum before download, skips if OK; also verifies checksum after download
* Prints downloaded file path, else exits with code 1

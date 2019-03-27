# phpdownloader

Automatic PHP tarball downloader written in Python. I personally use this as a
part of automatic Debian package build system.

* Parses php.net and gets all mirrors for latest PHP tarball;
* Verifies SHA-256 checksum before downloading, skips if it is okay;
* Verifies checksum after download;
* Uses Python `multiprocessing` module for parallel pinging of mirrors; fastest
 mirror is used for downloading;
* Prints downloaded file path or exits with error code.

## Requirements

* Python 2.7 or 3.4+
* `lxml` module

## Usage

```
usage: phpdownloader.py [-h] [-r {new,stable,oldstable}] [-C DIRECTORY]

optional arguments:
  -h, --help    help message

  -r, --release {new,stable,oldstable}
        Choose PHP release branch (were 7.3, 7.2 and 7.1 on 2019-03-27)

  -C, --directory DIRECTORY
        Target directory
```

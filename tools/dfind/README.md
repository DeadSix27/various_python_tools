# dfind.py  (Windows only)
#### SQLite based indexed search program

##### Simple tool that indexes every available drive and its files. (Configurable)

The benefit (for me) is that it's faster and more reliable than any default search on Windows¹, it also has wildcard support and can easily used via the Terminal.
It's faster because it only indexes when asked to, e.g it won't be "live".
The primary use case would be to search archives/disks/systems that rarely change.


### Basic usage:

Before using it, you have to index your system by running: `dfind --index`,
after which you can then search files by simply typing: `dfind mySearchText`
This will search for files matching exactly `mySearchText`,
if you want to look for files containing said text, use the wildcard like so: `dfind *mySearchText*`.

### Important:

As previously mentioned, indexing is only done manually, so it will never know if a file has been removed after the indexing is finished.
This search script is primarily used for archives which rarely if ever change.
Thus indexing can be automated via a cronjob (or w7e its called on Windows) if needed.

### Config options (inside the .py file):

```py
# Prefix of the index database file, which is saved in
# the same directory as this script, so make sure its writeable
#
# Default: dfind
#
INDEX_PREFIX = 'dfind'

# The file extension of the database, e.g .sqlite, .db
#
# Default: db
#
INDEX_EXTENSION = '.db'

# Drive's to be ignored, e.g C:, only write the letter and :, e.g 'C:'
# 
# Default: C:
# IGNORED_DRIVES = ('C:')

# Custom locations, e.g network shares: \\\\192.168.178.45\\someShare\\someFolderInThere
# 
# Default: ()
# CUSTOM_PLACES = ()
```

Full usage:
```
dfind.py [-h] [-e] [-c] [-u] [-n] [-i] [search]

Simple search SQLite based indexed search program. (Windows only) You can simple-search by just typing: "dfind <text>" no need for the arguments

positional arguments:
  search

optional arguments:
  -h, --help            show this help message and exit
  -e, --exact-match     Do not use wildcard search (default: yes)
  -c, --case-sensitive  Search case-sensitively (default: no)
  -u, --with-ui         Show UI with search results (default: yes)
  -n, --single-threaded
                        Single threaded indexing? (Default: no)
  -i, --index           Generate index, warning by default this will spin up and scan all driveson the system at once and could be CPU & HDD intensiveSee the option --single-threaded to index
                        drives one by one.
```


¹ Assumption.
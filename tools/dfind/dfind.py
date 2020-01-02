#!/usr/bin/env python3

from __future__ import annotations

# Copyright (C) 2019 <https://github.com/DeadSix27/>
# 
# This source code is licensed under a
# Creative Commons Attribution-NonCommercial 4.0 International License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# 
# You should have received a copy of the license along with this
# work. If not, see <http://creativecommons.org/licenses/by-nc/4.0/>.

# PIP REQUIREMENTS:
# pywin32 xxhash
# Install via cmd.exe and run:
# pip install xxhash pywin32

# dfind.py - Simple search SQLite based indexed search program. (Windows only)
#
# Description:
#
# A search tool (primarily for Windows, see notes below) that indexes every file on the system
# into an SQlite Database file and uses that for very quick searches.
#
# ################################################
#
# Simple usage:
#
# Index: dfind -i
# Search: dfind <searchText>
#
# Full Usage:
#
# dfind.py [-h] [-e] [-c] [-u] [-n] [-i] [search]
# 
# Simple search SQLite based indexed search program. (Windows only) You can simple-search by just typing: "dfind <text>"
# no need for the arguments
# 
# positional arguments:
#   search
# 
# optional arguments:
#   -h, --help            show this help message and exit
#   -e, --exact-match     Do not use wildcard search (default: yes)
#   -c, --case-sensitive  Search case-sensitively (default: no)
#   -u, --with-ui         Show UI with search results (default: yes)
#   -n, --single-threaded
#                         Single threaded indexing? (Default: no)
#   -i, --index           Generate index, warning by default this will spin up and scan all driveson the system at once
#                         and could be CPU & HDD intensiveSee the option --single-threaded to index drives one by one
#
# ################################################
#
# Note: This tool was made purely for Windows, it uses pywin32,
#       but could easily be ported.
#


# ################### CONFIGURATION OPTIONS ###################
# #############################################################
# ###################  You can change these ###################
# ###################    options at will    ###################
# #############################################################

# Prefix of the index database file, which is saved in
# the same directory as this script, so make sure its writeable
#
# Default: 'dfind'
# Type: String
# Example: 'dfind'
#
INDEX_PREFIX = 'dfind'

# The file extension of the database, e.g .sqlite, .db
#
# Default: '.db'
# Type: String
# Example: '.db'
#
INDEX_EXTENSION = '.db'

# Drive's to be ignored, e.g C:, only write the letter and :, e.g 'C:'
# 
# Default: C:
# Type: List
# Example: ('C:')
#
IGNORED_DRIVES = ('C:')

# Custom locations, e.g network shares: \\\\192.168.178.45\\someShare\\someFolderInThere
# 
# Default: ()
# Type: List
# Example: ('\\\\192.168.178.45\\weebShare')
#
CUSTOM_PLACES = ()

# Only scan these drives
# This option is the opposite of IGNORED_DRIVES, it will only scan the selection drive and nothing else
# If you want to disable this behavior set it to "None", if enabled it overrides IGNORED_DRIVES, but NOT CUSTOM_PLACES!
#
# Default: ()
# Type: List
# Example: ('Z:')
#
WHITELISTED_DRIVES = ()


# ########################### CODE ############################
# #############################################################
# ################     Only change this if      ###############
# ################ you know what you're doing   ###############
# #############################################################

import argparse
import datetime
import math
import os
import pathlib
import sqlite3
import sys
import threading
import time
from typing import AnyStr, List

import win32.win32api as win32api
import xxhash

def hashString(s):
	return xxhash.xxh64(s.encode('utf-8')).hexdigest().upper()

def pretty_time_delta(delta):
	if isinstance(delta, int) or isinstance(delta, float):
		delta = datetime.timedelta(seconds=delta)
	seconds = int(delta.total_seconds())
	days, seconds = divmod(seconds, 86400)
	hours, seconds = divmod(seconds, 3600)
	minutes, seconds = divmod(seconds, 60)
	milliseconds = delta.total_seconds() * 1000
	if days > 0:
		return '%dd%dh%dm%ds' % (days, hours, minutes, seconds)
	elif hours > 0:
		return '%dh%dm%ds' % (hours, minutes, seconds)
	elif minutes > 0:
		return '%dm%ds' % (minutes, seconds)
	elif seconds > 0:
		return '%ds' % (seconds,)
	else:
		return '%dms' % (milliseconds, )

def sizeToIECString(num: int, suffix: str = "B") -> str:
	magnitude = int(math.log(num, 1024))
	val = num / math.pow(1024, magnitude)
	if magnitude > 7: magnitude = 7			
	return F"{val:3.1f}{['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'][magnitude]}{suffix}"

def scantree(path):
	try:
		for entry in os.scandir(path):
			if entry.is_dir(follow_symlinks=False):
				yield from scantree(entry.path)
			else:
				yield Path(entry.path)
	except PermissionError:
		pass
	except FileNotFoundError:
		pass
	except OSError:
		pass

def sanitizeDriveList(l):
	if isinstance(l, str):
		l = [l, ]
	return [str(x).upper()[0:2] for x in l]

def getDriveRoots(ignoredRoots = (), customPlaces = (), whitelistedDrives=()):
	drives = win32api.GetLogicalDriveStrings()
	drives = drives.split('\000')[:-1]
	drives = sanitizeDriveList(drives)
	drives = set(drives) - set(ignoredRoots)
	if len(whitelistedDrives):
		drives = list(drives.intersection(set(whitelistedDrives)))
	else:
		drives = list(drives)

	for c in customPlaces:
		drives.insert(0, c)

	return drives

def indexDrives(singleThreaded=False):
	def gProgStr(x):
		progs = ["|", "/", "-", "\\"]
		if x < 0:
			return None
		if x >=len(progs):
			x = 0
			rx = 0
		else:
			rx = x + 1
		return (rx, progs[x])

	ignoreDrives = sanitizeDriveList(IGNORED_DRIVES)
	whitelistedDrives = sanitizeDriveList(WHITELISTED_DRIVES)

	driveRoots = getDriveRoots(ignoreDrives, CUSTOM_PLACES, whitelistedDrives)
	if not len(driveRoots):
		print("There are no drives set to be indexed, please fix your config.")
		exit(1)

	print(F'Indexing all drives ({"Single threaded" if singleThreaded else "Mutli threaded"})')
	print(F'Drives to be indexed: {", ".join(driveRoots)}')

	if DB_FILE.exists():
		print(F'Deleting old SQLite DB file: {DB_FILE}')
		DB_FILE.unlink()
	db = sqlite3.connect(DB_FILE, check_same_thread=False)
	c = db.cursor()
	c.execute('CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, drive TEXT, fullpath TEXT, fullpath_hash TEXT, name TEXT, name_hash TEXT, size INTEGER, modify_date TEXT, create_date TEXT);')
	c.execute('CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY AUTOINCREMENT, fullpath TEXT, fullpath_hash TEXT, name TEXT, name_hash TEXT, size INTEGER, modify_date TEXT, create_date TEXT);')
	c.execute('CREATE TABLE IF NOT EXISTS info (id INTEGER PRIMARY KEY AUTOINCREMENT, var TEXT, value TEXT);')
	db.commit()
	if not singleThreaded:
		thrList = []
		for i, d in enumerate(driveRoots):
			thread = threading.Thread(target=indexSingleDrive, args=(d, db))
			if d.startswith("\\\\"):
				d = F"@{i}"
			thrList.append((thread, d))

		for thr in thrList:
			thr[0].start()

		keepChecking = True
		progStrN = 0
		while keepChecking:
			threadStatus = [(thr[0].is_alive(), thr[1]) for thr in thrList]
			progStrN, progStr = gProgStr(progStrN)

			print(progStr + " " + " | ".join([F'{thr[1][0:2]}->..' if thr[0].is_alive() else F'{thr[1]}->OK' for thr in thrList]), end="\r")
			
			xthl = [x[0] for x in threadStatus]
			if True not in xthl:
				keepChecking = False
				break
			else:
				try:
					time.sleep(0.300)
				except KeyboardInterrupt:
					exit(1)
		print("\nFinished indexing")
	else:
		for d in driveRoots:
			start_time = datetime.datetime.now()
			print(F'Indexing "{d}"')
			indexSingleDrive(d, db)
			print(F'Indexing "{d}": Done, took {pretty_time_delta(datetime.datetime.now() - start_time)}')
	db.commit()

	# Running another loop on this, since it's only once during indexing
	# is simpler than having to deal with multithreaded access to the folder dictionary

	print("Calculating sizes...")
	c.execute('SELECT * FROM files;')
	c.row_factory = sqlite3.Row
	folderSizes = {}
	totalSize = 0

	for row in c.fetchall():
		try:
			p = Path(row['fullpath'])
		except OSError as e:
			if e.errno == 22:
				continue
			else:
				print(F"Failed to access the path: {row['fullpath']}:")
				print(e)
				exit(1)

		if p.parent in folderSizes:
			folderSizes[p.parent] = folderSizes[p.parent] + row["size"]
		else:
			folderSizes[p.parent] = row["size"]
		totalSize += row["size"]

	print("Adding sizes to database...")

	for folder, size in folderSizes.items():
		p = Path(folder)
		values = (
			str(p.resolve()), hashString(str(p.resolve())),
			p.name if p.name not in ('', None) else str(p.resolve()),
			hashString(p.name if p.name not in ('', None) else str(p.resolve())),
			size,
			p.modifyDate(),
			p.createDate(),
		)
		c.execute(F'INSERT INTO folders (fullpath, fullpath_hash, name, name_hash, size, modify_date, create_date) VALUES (?, ?, ?, ?, ?, ?, ?);', values)

	c.execute(F'INSERT INTO info (var, value) VALUES (?, ?);', ("totalSize", totalSize))
	print("Done.")
	db.commit()
	c.close()
	db.close()

def indexSingleDrive(drive, sqlDb):
	count = 0
	sqlCursor = sqlDb.cursor()
	for entry in scantree(drive):
		try:
			if len(entry.parts) >= 2:
				# Never index these MS Internal paths
				if entry.parts[1] in ('$RECYCLE.BIN', 'System Volume Information'):
					continue

			values = (
				entry.root,
				str(entry.resolve()), hashString(str(entry.resolve())),
				entry.name, hashString(entry.name),
				entry.size(),
				entry.modifyDate(),
				entry.createDate(),
			)
			sqlCursor.execute(F'INSERT INTO files (drive, fullpath, fullpath_hash, name, name_hash, size, modify_date, create_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?);', values)
			count += 1
		except (PermissionError, FileNotFoundError, OSError):
			continue

	sqlCursor.close()

def top(top_type, top_max, ascending):
	db = sqlite3.connect(F'file:{DB_FILE}?mode=ro', uri=True)
	c = db.cursor()
	c.execute(F'SELECT * FROM {top_type} ORDER BY size {"DESC " if not ascending else ""}LIMIT ?;', (top_max, ))
	c.row_factory = sqlite3.Row
	print(F"Top {top_max} {top_type}:")
	for i, row in enumerate(c.fetchall(), 1):
		print(F'#{i:2}: {sizeToIECString(row["size"]):>15}  -  {row["fullpath"]}')

def find(search: str, noWildcard = False, case_sensitive = False) -> DFindResultList:
	start_time = time.time()
	search = search.replace('*', '%')
	db = sqlite3.connect(F'file:{DB_FILE}?mode=ro', uri=True)
	c = db.cursor()

	queryStr = {"query": None}

	def rawQuery(x):
		queryStr["query"] = x

	db.set_trace_callback(rawQuery)

	if case_sensitive:
		c.execute('PRAGMA case_sensitive_like = on;')
	if noWildcard:
		c.execute('SELECT * FROM files WHERE name = ? OR fullpath = ?;', (search, search))
	else:
		c.execute('SELECT * FROM files WHERE name LIKE ? OR fullpath LIKE ?;', (search, search))

	c.row_factory = sqlite3.Row

	db.set_trace_callback(None)

	def format_row(_row):
		ro = DFindResult()
		_row = dict(zip(_row.keys(), _row))
		ro.Id = _row['id']
		ro.Drive = _row['drive']
		ro.FullPath = _row['fullpath']
		ro.FullPathHash = _row['fullpath_hash']
		ro.Name = _row['name']
		ro.NameHash = _row['name_hash']
		ro.Size = _row['size']
		ro.ModifyDate = _row['modify_date']
		ro.CreateDate = _row['create_date']
		return ro

	rlist = [format_row(row) for row in c.fetchall()]

	took = time.time() - start_time

	tookStr = pretty_time_delta(took)

	r = DFindResultList()
	r.List = rlist
	r.Count = len(rlist)
	r.TookStr = tookStr
	r.Took = took
	r.CaseSensitive = case_sensitive
	r.Wildcard = not noWildcard
	r.OriginalSearch = search
	r.Query = queryStr["query"]
	
	c.close()
	db.close()

	return r

def showUi(rl: DFindResultList):
	if rl.Count <= 0:
		print("No results.")
		print(F"Query: {rl.Query}")
		exit()
	import tkinter
	import tkinter.scrolledtext

	master_window = tkinter.Tk()
	group1 = tkinter.LabelFrame(master_window, text="Text Box", padx=5, pady=5)
	group1.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky=tkinter.E + tkinter.W + tkinter.N + tkinter.S)
	master_window.columnconfigure(0, weight=1)
	master_window.rowconfigure(1, weight=1)
	master_window.title(F'{rl}')
	group1.rowconfigure(0, weight=1)
	group1.columnconfigure(0, weight=1)
	txtbox = tkinter.scrolledtext.ScrolledText(group1, width=220, height=50)
	txtbox.grid(row=0, column=0, sticky=tkinter.E + tkinter.W + tkinter.N + tkinter.S)

	for f in rl.List:
		txtbox.insert(tkinter.END, f.FullPath)
		txtbox.insert(tkinter.END, "\n")
	tkinter.mainloop()

class DFindResultList():
	OriginalSearch: AnyStr
	Count: int
	List: List[DFindResult]
	Took: float
	TookStr: AnyStr
	CaseSensitive: bool
	Wildcard: bool
	Query: str

	def __repr__(self):
		return F'[DFindResultList] Search for: "{self.OriginalSearch}"; Count: {self.Count}, Took: {self.TookStr}, {"Case-Sensitive" if self.CaseSensitive else "Case-Insensitive"} {"Wildcard" if self.Wildcard else "Exact"} Match'

class DFindResult():
	Id: int
	Drive: AnyStr
	FullPath: AnyStr
	FullPathHash: AnyStr
	Name: AnyStr
	NameHash: AnyStr
	Size: int

class Path(pathlib.Path): # Part of https://gist.github.com/DeadSix27/036810df93804d02b962c0aec8d08b59
	_flavour = pathlib._windows_flavour if os.name == 'nt' else pathlib._posix_flavour

	def __new__(cls, *args):
		return super(Path, cls).__new__(cls, *args)

	def __init__(self, *args):
		super().__init__()
		self.ssuffix = self.suffix.lstrip(".")
		self._some_instance_ppath_value = self.exists()

	def size(self) -> int:
		return self.stat().st_size

	def createDate(self):
		return self.stat().st_ctime

	def modifyDate(self):
		return self.stat().st_mtime

	def joinpath(self, *other):
		return Path(super().joinpath(*other))

if __name__ == '__main__':

	def printResutls(results):
		if len(results):
			for x in results:
				print(x.FullPath)
		else:
			print(F"Error: Found nothing for: '{args.search}', maybe try re-indexing via the argument: --index")
			exit(1)

	SCRIPT_DIR = Path(__file__).parent
	DB_FILE = SCRIPT_DIR.joinpath(INDEX_PREFIX + INDEX_EXTENSION)

	parser = argparse.ArgumentParser(description=
		'Simple search SQLite based indexed search program. (Windows only)\n'
		'You can simple-search by just typing: "dfind <text>" no need for the arguments\n'
	)
	parser.set_defaults(which='main_p')

	parser.add_argument('-i', '--index',
		help=
			'Generate index, warning by default this will spin up and scan all drives'
			'on the system at once and could be CPU & HDD intensive'
			'See the option --single-threaded to index drives one by one.'
		,
		dest='index', action='store_true', default=False
	)
	parser.add_argument('-n', '--single-threaded', help='Single threaded indexing? (Default: no)', dest='singleThreaded', action='store_true', default=False)

	sps = parser.add_subparsers(help="Sub commands")

	sp = sps.add_parser("search", help="Search the database\nType: \"" + parser.prog + " plain --help\" for more help")
	sp.add_argument('search', nargs="?")
	sp.add_argument('-e', '--exact-match', help='Do not use wildcard search (default: yes)', dest='noWildCard', action='store_true', default=False)
	sp.add_argument('-c', '--case-sensitive', help='Search case-sensitively (default: no)', dest='caseSensitive', action='store_true', default=False)
	sp.add_argument('-u', '--with-ui', help='Show UI with search results (default: yes)', dest='withUi', action='store_true', default=False)

	sp = sps.add_parser("top", help="Shows the top files and folders in terms of Size\nType: \"" + parser.prog + " plain --help\" for more help")
	sp.set_defaults(which="top_p")
	sp.add_argument("-t", "--type", help="Wether to list folders or files", choices=("folders", "files"), dest="type", default="folders")
	sp.add_argument("-m", "--max-results", help="The amount of items to show", type=int, choices=range(1,101), dest="max", default=10)
	sp.add_argument("-a", "--ascending", help="Wether to sort asecnding (smallest first)", action='store_true', dest="asc", default=False)

	# ###
	# Comprimise, either use this unreliable and imperfect dirty hack or
	# require a sub-parser or argument for searches
	# the latter is a far bigger burden to me.
	#
	if len(sys.argv) >= 2 and sys.argv[1] not in ("search", "top") and not sys.argv[1].startswith("-"):
		printResutls(find(" ".join(sys.argv[1:]), False, False).List)
		exit()
	# ####

	args = parser.parse_args()

	if args.index:
		indexDrives(args.singleThreaded)
		exit(0)

	if not DB_FILE.exists():
		print("No index DB found, please create one using the command:")
		print("dfind index")
		exit(1)

	if args.which == "search":
		if not args.search:
			parser.print_help()
			exit(1)
		if args.withUi:
			showUi(find(args.search, args.noWildCard, args.caseSensitive))
		else:
			printResutls(find(args.search, args.noWildCard, args.caseSensitive).List)

	elif args.which == "top_p":
		top(args.type, args.max, args.asc)
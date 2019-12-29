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


# opus.py - Simple opus encoder and share-helper
#
# Description:
#
# Simple tool to automatically encode a media file into opus
# with cover-art, metadata and optional defined range (e.g 0:20 to 0:34)
# Most important settings, e.g bitrate/vbr can changed via the config
# The main appeal is the ability to move the output file
# to a specified path/network path (if configured)
# and copy a configured URL with the filename
# to clip-board (if pyperclip is installed)
#
# Syntax/Usage:
#   opus <file> [<start_time> [<end_time]]
# 
# 	Examples:
#   opus 'ネネ (CV:水瀬いのり).flac' 3:07 3:15
#   opus 'music.flac' 3:07

# ################### CONFIGURATION OPTIONS ###################
# #############################################################
# ###################  You can change these ###################
# ###################    options at will    ###################
# #############################################################

#
# Bitrate of the opus file, default is 60 (per channel)
# 60 is about as low as you can go with little artifacting while having the smallest filesize.
# Note that that is not transparent, if you want something more transparent, try 1
#
# Default: 64
#
BITRATE = 64

#
# Use variable bitrate for opus, leave on if you do not know what this means, otherwise google it.
#
# Default: True
#
OPUS_VBR = True

# Path to output folder, if set to None it will be saved into the same folder as the input file
# Examples:
# "/someLinux/path"
# "\\\\192.168.178.45\\someWindowsNetworkPath"
# "C:/OtherWindowsPath/"
# 
# Note: If using Network path, or a path that is a public/http reachable location
#       the option "save URL to clip-board might be interesting to you"
#
# Default: None
#
OUTPUT_PATH = None

#
# If set to True the URL based on BASE_URL will be copied to the clipboard once encoding is done.
# This requeres
#
# See BASE_URL and OUTPUT_PATH setting for more information
#
# Default: False
#
COPY_SHARE_LINK = False

# If this setting is set to True it will allow any file as input file, may cause issues.
# Note: This setting is only used when the Python package: "magic" is installed,
#       otherwise the program behaves as if it's set to True.
#
# Default: False
#
IGNORE_MIME = False

#
# The base URL is used for copying the output files share-link into clip-board,
# this is only used when "COPY_SHARE_LINK" is set to True, see OUTPUT_PATH Notes for more info
# Make sure that the OUTPUT_PATH option is set and points to a
# web-accessable location, e.g /var/www on Linux or # a Samba shared path that
# is web accessable, e.g: \\\\192.168.178.45\\someWebPath\\http\\share\\
#
# Examples:
#   - https://generic.weeb.url.xyz/myshare/
#   - https://i.wonder.why.so.many.devs.watch.anime/{file_name}/
# 
# Notes:
# - COPY_SHARE_LINK has to be set to True to make this work!!!
#
# - You can use {file_name} as variable for the file name, e.g: https://typical.weeb.url.nyaa.kawaii.moe/share/{file_name}
#   if said variable is not used, the file name will be added to the end of the URL.
#
# Default: None
#
BASE_URL = None

#
# If set to True (the default), it will first try to extract the Cover art from the input file,
# and if that has None, it will search for common cover art files in the
# input file's directory, e.g: cover.jpg/png folder.jpg/png and
# attach these to the output opus file.
#
# Default: True
#
WITH_COVER = True

# ########################### CODE ############################
# #############################################################
# ################     Only change this if      ###############
# ################ you know what you're doing   ###############
# #############################################################
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import shutil

class OpusMaker:
	def extractCover(self, file_path: Path) -> Path:
		temp_out_path = file_path.change_name(file_path.stem + "opusthing_xyz.jpg")
		cmd = [
			'ffmpeg',
			'-y',
			'-i',
			str(file_path),
			'-an',
			'-compression_level',
			'75',
			'-pix_fmt',
			'yuvj444p',
			'-s',
			'300x300',
			'-c:v',
			'mjpeg',
			str(temp_out_path),
		]
		_ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
		return temp_out_path
	
	def getFfprobe(self, file_path: Path) -> dict:
		cmd = [
			'ffprobe',
			'-show_streams',
			'-show_format',
			'-print_format',
			'json',
			'-loglevel',
			'panic',
			str(file_path),
		]
		return json.loads(subprocess.check_output(cmd))

	def getCoverFromFolder(self, file_path: Path) -> Path:
		foundFile = None
		for file in file_path.parent.listfiles(('.jpg', '.jpeg', '.png', '.webp',)):
			if any(w in file.name.lower() for w in ('cover', 'folder', 'artwork')):
				foundFile = file
				break
			elif not foundFile:
				foundFile = file
		return foundFile

	def hasCover(self, file_path) -> bool:
		probe = self.getFfprobe(file_path)
		for stream in probe["streams"]:
			if stream['codec_type'] == 'video':
				if 'tags' in stream and 'comment' in stream['tags']:
					if 'cover' in stream['tags']['comment'].lower():
						return True
		return False

	def getCoverFromFile(self, file_path: Path) -> Path:
		if self.hasCover(file_path):
			return self.extractCover(file_path)
		return None

	def encodeFile(self, original_file: Path) -> Path:
		output_file_path = original_file.parent.joinpath(original_file.name.replace(" ", "_").replace("_-_", "_")).change_suffix(".opus")
		if output_file_path.exists():
			_output_file_path = output_file_path
			_append_num = 1
			while _output_file_path.exists():
				if _append_num >= 10000:
					# Who would ever keep 10000 re-encodes of the same file-name in the same folder!?
					raise Exception("Failed to find suitable alternative name for output file")
				_output_file_path = _output_file_path.append_stem(F"_{_append_num}")
				_append_num += 1
			output_file_path = _output_file_path

		cover: Path = None
		if self.withCover:
			cover = self.getCoverFromFile(original_file)
			if not cover:
				cover = self.getCoverFromFolder(original_file)
				print(F"Using cover from folder: {cover}")
			else:
				print(F"Using cover from file: {cover}")

		cmd1 = [
			'ffmpeg',
			'-loglevel',
			'panic',
			'-i',
			str(original_file),
			'-map_metadata',
			'0',
		]
		if self.startTime:
			cmd1.append('-ss')
			cmd1.append(self.startTime)

		if self.endTime:
			cmd1.append('-to')
			cmd1.append(self.endTime)

		cmd1.extend([
			'-f',
			'flac',
			'-',
		])
		cmd2 = [
			'opusenc',
			'-',
			'--bitrate',
			str(self.bitrate),
		]
		if self.opusVbr:
			cmd2.append('--vbr')
		if cover:
			cmd2.append('--picture')
			cmd2.append(str(cover))
		cmd2.append(str(output_file_path))

		erange = ""
		if start_time and end_time:
			erange = F" from {start_time} to {end_time}"
		elif start_time:
			erange = F" from {start_time} to end"
		elif end_time:
			erange = F" from start to {end_time}"

		print(F"Encoding{erange} into file {output_file_path}...")
		p = subprocess.Popen(cmd1, shell=False, bufsize=0, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)
		p2 = subprocess.Popen(cmd2, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stdin=p.stdout)
		stdo, stde = p2.communicate()

		if cover:
			cover.unlink()

		return output_file_path

	def mime(self, path: Path) -> str:
		ext = path.suffix.lstrip(".").lower()
		custom_types = {
			'ttf': 'font/ttf',
			'otf': 'font/otf',
		}
		if ext in custom_types:
			return custom_types[ext]

		mime = magic.Magic(mime=True)
		mime = mime.from_file(str(path))
		return mime
	
	def __init__(self, original_file: Path,
		start_time: str = None,
		end_time: str = None,
		output_dir: Path = None,
		copy_link: bool = None,
		base_url: str = None,
		opus_vbr: bool = None,
		bit_rate: int =None,
		with_cover: bool = None,
		have_mime: bool = None,
		ignore_mime: bool = None,
		have_pyperclip: bool = None
	) -> None:
		errors = []
		# Settings
		self.opusVbr = opus_vbr
		self.outputDir = output_dir
		self.copyLink = copy_link
		self.baseUrl = base_url
		self.bitrate = bit_rate
		self.withCover = with_cover
		self.ignoreMime = ignore_mime

		# Commandline args
		self.startTime = start_time
		self.endTime = end_time
		self.originalFile = original_file

		# ###
		self.haveMime = have_mime
		self.havePyperclip = have_pyperclip

		if not self.bitrate or not isinstance(self.bitrate, (float, int)):
			errors.append("The BITRATE setting has to be a number (float or int), default is 64.")

		if not self.opusVbr or not isinstance(self.opusVbr, bool):
			errors.append("The OPUS_VBR setting has to be a boolean (True or False), default is True")

		if self.outputDir and not isinstance(self.outputDir, str):
			errors.append("The OUTPUT_PATH setting has string of an existing Path or None, default is None")
		else:
			self.outputDir = Path(output_dir)
			if self.outputDir and not self.outputDir.exists():
				errors.append("The OUTPUT_PATH setting has to be an existing proper Path, default is None")

		if not self.withCover and not isinstance(self.withCover, bool):
			errors.append("The WITH_COVER setting has to be a boolean (True or False), default is True")

		if self.copyLink and not isinstance(self.copyLink, bool):
			errors.append("The COPY_SHARE_LINK setting has to be a boolean (True or False), default is False")

		if self.copyLink and not self.havePyperclip:
			errors.append("The COPY_SHARE_LINK requires pyperclip to be installed (pip install pyperclip)")

		if self.copyLink and not self.baseUrl:
			errors.append("The COPY_SHARE_LINK setting requires BASE_URL to be set.")

		if len(errors):
			print("Incorrect config settings:")
			print("\t- " + "\n\t- ".join(errors))
			exit(1)

		try:
			self.originalFile = Path(self.originalFile)
		except Exception:
			print(F"{self.originalFile} is not a valid audio/video file path.")
			exit(1)
		if not self.originalFile.exists():
			print(F"File {self.originalFile} does not exist.")
			exit(1)

		if self.haveMime:
			if not self.ignoreMime and not self .mime(self.originalFile).startswith(("audio/", "video/")):
				print(F"File {self.originalFile} is no video or audio file.")
				exit(1)

		output_file_path = self.encodeFile(self.originalFile)

		if self.outputDir:
			print(F"Moving output file to: {self.outputDir}")
			new_output_file_path = self.outputDir.joinpath(output_file_path.name)
			shutil.move(output_file_path, new_output_file_path)

			if self.copyLink:
				url = self.baseUrl.format(file_name=new_output_file_path.name)
				print(F"Copying URL to clip-board: {url}")
				pyperclip.copy(url)

class Path(pathlib.Path): # Part of https://gist.github.com/DeadSix27/036810df93804d02b962c0aec8d08b59
	_flavour = pathlib._windows_flavour if os.name == 'nt' else pathlib._posix_flavour

	def __new__(cls, *args):
		return super(Path, cls).__new__(cls, *args)

	def __init__(self, *args):
		super().__init__()
		self.ssuffix = self.suffix.lstrip(".")
		self._some_instance_ppath_value = self.exists()

	def listfiles(self, extensions=()) -> List[Path]:
		'''### listfiles
		##### listfiles

		### Args:
			`extensions` (tuple, optional): List of extensions to limit listing to, with dot prefix. Defaults to ().

		### Returns:
			List[Path]: List of Paths, matching the optionally specificed extension(s)
		'''
		lst = None
		if len(extensions) > 0:
			lst = [self.joinpath(x) for x in self._accessor.listdir(self) if self.joinpath(x).is_file() and x.lower().endswith(extensions)]
		else:
			lst = [self.joinpath(x) for x in self._accessor.listdir(self) if self.joinpath(x).is_file()]

		def convert(text):
			return int(text) if text.isdigit() else text

		def alphanum_key(key):
			return [convert(c) for c in re.split('([0-9]+)', str(key))]

		lst = sorted(lst, key=alphanum_key)
		return lst

	def change_suffix(self, newSuffix: str) -> Path:
		'''### change_name
		##### Changes the name, including suffix

		### Args:
			`newSuffix` (str): The new suffix

		### Returns:
			Path: Newly named Path.
		'''
		return Path(self.parent.joinpath(self.stem + newSuffix))

	def change_name(self, name: str) -> Path:
		'''### change_name
		##### Changes the name, including suffix

		### Args:
			`name` (str): The new name

		### Returns:
			Path: Newly named Path.
		'''
		return self.parent.joinpath(name)

	def append_stem(self, append_str: str) -> Path:
		'''### append_stem
		##### Appends a string to the stem, excluding the suffix.

		### Args:
			`append_str` (str): String to append.

		### Returns:
			Path: Newly named Path.
		'''
		return self.parent.joinpath(self.stem + append_str + self.suffix)

if __name__ == "__main__":
	try:
		import magic
		HAVE_MIME = True
	except ImportError:
		HAVE_MIME = False

	try:
		import pyperclip
		HAVE_PYPERCLIP = True
	except ImportError:
		HAVE_PYPERCLIP = False

	if len(sys.argv) >= 2:
		file_path = sys.argv[1]
		start_time = None
		end_time = None
		if len(sys.argv) == 3:
			start_time = sys.argv[2]
		elif len(sys.argv) >= 4:
			start_time = sys.argv[2]
			end_time = sys.argv[3]

		OpusMaker(file_path, start_time, end_time,
			output_dir=OUTPUT_PATH,
			copy_link=COPY_SHARE_LINK,
			base_url=BASE_URL,
			opus_vbr=OPUS_VBR,
			bit_rate=BITRATE,
			with_cover=WITH_COVER,
			have_mime=HAVE_MIME,
			ignore_mime=IGNORE_MIME,
			have_pyperclip=HAVE_PYPERCLIP,
		)
	else:
		print("Syntax: opus <file> [<start_time> [<end_time]]")
		exit(1)

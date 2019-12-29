
## opus.py - Simple opus encoder and share-helper

### Description:

Simple tool to automatically encode a media file into opus
with cover-art, metadata and optional defined range (e.g 0:20 to 0:34)
Most important settings, e.g bitrate/vbr can changed via the config
The main appeal is the ability to move the output file
to a specified path/network path (if configured)
and copy a configured URL with the filename
to clip-board (if pyperclip is installed)

```
Syntax/Usage:
  opus <file> [<start_time> [<end_time]]

	Examples:
  opus 'ネネ (CV:水瀬いのり).flac' 3:07 3:15
  opus 'music.flac' 3:07
 ```

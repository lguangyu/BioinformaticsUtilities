#!/usr/bin/env python3

import argparse
import io
import json
import sys


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type = str, nargs = "?",
		metavar = "json", default = "-",
		help = "input json (default: stdin)")
	ap.add_argument("-o", "--output", type = str,
		metavar = "json", default = "-",
		help = "write output json to this file instead of stdout")
	ap.add_argument("-d", "--indent-char", type = str,
		metavar = "<tab>|<space>|off",
		choices = ["\t", " ", "off"], default = "\t",
		help = "indentation character, if set to 'off', a single-line json will"
			" be produced (default: <tab>)")
	ap.add_argument("-S", "--no-sort-keys", action = "store_false",
		help = "without sorting keys (default: off)")
	args = ap.parse_args()
	# refine args
	if args.input == "-":
		args.input = sys.stdin
	if args.output == "-":
		args.output = sys.stdout
	if args.indent_char == "off":
		args.indent_char = None
	return args


def get_fh(file, mode = "r", *ka, open_factory = open, **kw) -> io.IOBase:
	"""
	return a file handle, wrapper function to ensure safe invocation when used
	used on an instance of file handle;

	ARGUMENTS
	file:
		of type io.IOBase (e.g. stderr) or a str (as file name); return <file>
		unchanged if <file> is an io.IOBase instance; no mode check will be
		performed;
	mode:
		open mode; omitted if <file> is an io.IOBase instance; this argument
		follows the convention used by open_factory() as the second positional
		argument if used;
	open_factory:
		method to create the file handle; default is open() from built-in;
	*ka, **kw:
		other keyargs/kwargs passed to open_factory()
	"""
	if isinstance(file, io.IOBase):
		fh = file
	elif isinstance(file, str):
		fh = open_factory(file, mode, *ka, **kw)
	else:
		raise TypeError("file must be io.IOBase or str, not '%s'"\
			% type(file).__name__)
	return fh


def main():
	args = get_args()
	with get_fh(args.input, "r") as ifp:
		with get_fh(args.output, "w") as ofp:
			json.dump(json.load(ifp), ofp, indent = args.indent_char,
				sort_keys = not args.no_sort_keys)
	return


if __name__ == "__main__":
	main()

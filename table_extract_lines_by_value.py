#!/usr/bin/env python3

import argparse
import io
import sys


def get_args() -> argparse.Namespace:
	ap = argparse.ArgumentParser(description="extract lines in a table with "
		"interested value(s) found in a given column")
	ap.add_argument("input", type=str, nargs="?", default="-")
	ap.add_argument("-o", "--output", type=str, default="-",
		metavar="file",
		help="(default: <stdout>)")
	ap.add_argument("-k", "--column", type=int, default=0,
		metavar="int",
		help="column to look for values, 0 = entire line (default: 0)")
	ap.add_argument("-f", "--filter-values", type=str, required=True,
		metavar="file",
		help="print lines when given column has one of those value(s) in this"
			" list file (required)")
	ap.add_argument("-x", "--exclude-mode", "--reverse-select",
		action="store_true",
		help="excluding those filtered lines instead of only printing them "
			"out (default: off)")
	ap.add_argument("-d", "--delimiter", type=str, default="\t",
		metavar="char",
		help="field delimiter (default: <tab>)")
	# parse and refine args
	args = ap.parse_args()
	if args.input == "-":
		args.input = sys.stdin
		print("<< read from stdin", file=sys.stderr)
	if args.output == "-":
		args.output = sys.stdout
		print(">> write to stdout", file=sys.stderr)
	return args


def get_fp(file, *ka, factory=open, **kw) -> io.IOBase:
	if isinstance(file, io.IOBase):
		ret = file
	elif isinstance(file, str):
		ret = factory(file, *ka, **kw)
	else:
		raise TypeError("file must be str or io.IOBase, not '%s'"
			% type(file).__name__)
	return ret


def read_filter_values(file) -> set:
	with get_fp(file, "r") as fp:
		return set(fp.read().splitlines())


def _is_printing_line(line, field, filter_set, delimiter, exclude_mode=False):
	line = line.rstrip("\r\n")
	if field == 0:
		has_filter_value = (line in filter_set)
	else:
		splitted = line.split(delimiter)
		if field > 0:
			field -= 1
		has_filter_value = (splitted[field] in filter_set)
	return has_filter_value ^ exclude_mode


def filter_delimited_file(file_in, file_out, column, filter_set: set, *,
		delimiter="\t", exclude_mode=False) -> None:
	with get_fp(file_in, "r") as ifp:
		with get_fp(file_out, "w") as ofp:
			for line in ifp:
				if _is_printing_line(line, column=column,
					filter_set=filter_set, delimiter=delimiter,
					exclude_mode=exclude_mode):
					ofp.write(line)
	return


def main():
	args = get_args()
	filter_set = read_filter_values(args.filter_values)
	filter_delimited_file(args.input, args.output,
		column=args.column, filter_set=filter_set,
		delimiter=args.delimiter, exclude_mode=args.exclude_mode)
	return


if __name__ == "__main__":
	main()

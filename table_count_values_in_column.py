#!/usr/bin/env python3

import argparse
import collections
import io
import json
import os
import sys


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type=str, nargs="?", default="-",
		metavar="txt",
		help="input txt file [stdin]")
	ap.add_argument("-d", "--delimiter", type=str, default="\t",
		metavar="str",
		help="filed delimiter [<tab>]")
	ap.add_argument("-c", "--combine-consecutive-delimiters",
		action="store_true",
		help="treat consecutive delimiters in input as one [off]")
	ap.add_argument("-k", "--field-key", type=int, default=0,
		metavar="int",
		help="column id to count (1-based), use full lines if set to 0 [0]")
	ap.add_argument("-o", "--output", type=str, default="-",
		metavar="file",
		help="output file [stdout]")
	ap.add_argument("-f", "--output-format", type=str, default="txt",
		metavar="format", choices=("txt", "json"),
		help="output file format [txt]")

	# parse and refine args
	args = ap.parse_args()
	if args.input == "-":
		args.input = sys.stdin
	if args.output == "-":
		args.output = sys.stdout
	return args


def get_fp(f, *ka, factory=open, **kw) -> io.IOBase:
	if isinstance(f, io.IOBase):
		ret = f
	elif isinstance(f, str):
		ret = factory(f, *ka, **kw)
	else:
		raise TypeError("first argument of get_fp() must be str or io.IOBase, "
			"got '%s'" % type(f).__name__)
	return ret


def split_txt_line(s, delimiter="\t", combine_consecutive_delimiters=False) \
		-> list:
	ret = s.split(delimiter)
	if combine_consecutive_delimiters:
		ret = [i for i in ret if i]  # field values between consecutive delims
		# should be '', using this method to drop all of those
	return ret


def get_field_from_line(line, *, delimiter="\t", field_key=0,
		combine_consecutive_delimiters=False) -> str:
	line = line.rstrip(os.linesep)
	if field_key == 0:
		ret = line
	else:
		# change from 1-based to 0-based
		k = (field_key - 1) if field_key > 0 else field_key
		ret = split_txt_line(line, delimiter, combine_consecutive_delimiters)[k]
	return ret


def count_field_values_in_txt(file, **kw) -> collections.Counter:
	# **kw are arguments forwarded to get_field_from_line()
	values = list()
	with get_fp(file, "r") as fp:
		for i, line in enumerate(fp):
			try:
				values.append(get_field_from_line(line, **kw))
			except IndexError:
				print("bad field key at line '%u'" % (i + 1), file=sys.stderr)
				sys.exit(1)
	return collections.Counter(values)


def save(file, counter: collections.Counter, *, fmt="txt", delimiter="\t"):
	if fmt == "txt":
		# use open inside the if section to avoid creating empty output file
		# when error occurs
		with get_fp(file, "w") as fp:
			for k, v in counter.most_common():
				print(k + delimiter + str(v), file=fp)
	elif fmt == "json":
		with get_fp(file, "w") as fp:
			json.dump(counter, fp)
	else:
		raise ValueError("unaccepted output format: '%s'" % fmt)
	return


def main():
	args = get_args()
	counter = count_field_values_in_txt(args.input, delimiter=args.delimiter,
		combine_consecutive_delimiters=args.combine_consecutive_delimiters,
		field_key=args.field_key)
	save(args.output, counter, fmt=args.output_format, delimiter=args.delimiter)
	return


if __name__ == "__main__":
	main()

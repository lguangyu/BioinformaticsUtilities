#!/usr/bin/env python3

import argparse
import numpy
import sys


def get_args():
	ap = argparse.ArgumentParser(description="transpose delimited tabular "
		"txt files")
	ap.add_argument("input", nargs="?", type=str, default="-",
		help="input table (default: stdin)")
	ap.add_argument("-d", "--delimiter", type=str, default="\t",
		metavar="char",
		help="delimiter in both input and output (default: <tab>)")
	ap.add_argument("-c", "--comments", type=str, default="#",
		metavar="char",
		help="comments indicator (default: #); all comments will be discarded")
	ap.add_argument("-o", "--output", type=str, default="-",
		metavar="file",
		help="output file (default: stdout)")
	# parse and refine args
	args = ap.parse_args()
	if args.input == "-":
		args.input = sys.stdin
		print("<< read from stdin", file=sys.stderr)
	if args.output == "-":
		args.output = sys.stdout
		print(">> write to stdout", file=sys.stderr)
	return args


def main():
	args = get_args()
	data = numpy.loadtxt(args.input, delimiter=args.delimiter, dtype=object,
		comments=args.comments)
	numpy.savetxt(args.output, data.T, fmt="%s", delimiter=args.delimiter)
	return


if __name__ == "__main__":
	main()

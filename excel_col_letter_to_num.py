#!/usr/bin/env python3

import argparse
import sys


def get_args():
	ap = argparse.ArgumentParser(description="transforms Excel-style column id "
		"letter label into numerical label"
	)
	ap.add_argument("input", type=str,
		help="Excel-style letter-based column label, only a-z and A-Z are "
			"allowed (case-insensitive)"
	)
	ap.add_argument("-0", "--zero-based", action="store_true",
		help="the result is in 0-based format [no]"
	)

	# parse and refine args
	args = ap.parse_args()
	return args


def letter_label_to_num(label: str, zero_based=False):
	ret = 0
	for c in label.upper():
		v = ord(c) - ord("A") + 1
		if (v <= 0) or (v >= 27):
			raise ValueError("only alphabatical characters (a-z/A-Z) are "
				"allowed, got '%s'" % c
			)
		ret = ret * 26 + v

	if zero_based:
		ret -= 1
	return ret


def main():
	args = get_args()
	num_label = letter_label_to_num(args.input, args.zero_based)
	print(num_label, file=sys.stdout)
	return


if __name__ == "__main__":
	main()

#!/usr/bin/env python3

import argparse
import re
import sys


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type = str,
		help = "input fasta file")
	args = ap.parse_args()
	return args


class ContigFastaHeaderEncoder(dict):
	def encode(self, header):
		"""
		encode an input header, return a string (new header) in format
		c_00000000000000000001, c_00000000000000000002, ...
		if the input header has been encountered previously, old result will be
		returned
		"""
		return "c_%020u" % self.get_hid(header)

	def get_hid(self, header):
		"""
		return a integral header id;
		return the existing result if encountered previously
		"""
		hid = self.setdefault(header, len(self) + 1)
		# debug
		assert isinstance(hid, int), hid
		return hid

	def encode_by_regex_sub(self, matchobj):
		# used as the callable as repl argument in re.sub
		# re.sub will not call this if not matches,
		# so safe to not implement handling None case
		return self.encode(matchobj.group(1))


def main():
	args = get_args()
	fasta_header_re = re.compile(r"^(>\S+).*$")
	encoder = ContigFastaHeaderEncoder()
	# it is possible to not use formal fasta parser, since the format of fasta
	# seq header line is distinct
	# so simply do modification if it is a header, and throw everything else
	# back unchanged
	with open(args.input, "r") as fh:
		for line in fh:
			# try replace the header line by only using the fasta 'id' feature
			sys.stdout.write(fasta_header_re.sub(encoder.encode_by_regex_sub, line))
	return


if __name__ == "__main__":
	main()

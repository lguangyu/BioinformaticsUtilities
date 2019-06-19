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


class SeqNameEncoder(dict):
	def encode(self, seq_name):
		"""
		encode an input seq name, return a string (new name) in format
		s_0000000000000001, s_0000000000000002, ...
		if the input header has been encountered previously, old result will be
		returned
		"""
		return "s_%016u" % self.get_sid(seq_name)

	def get_sid(self, seq_name):
		"""
		return an integral seq id;
		return the existing result if encountered previously
		"""
		sid = self.setdefault(seq_name, len(self) + 1)
		# debug
		#assert isinstance(sid, int), sid
		return sid

	def encode_by_regex_sub(self, matchobj):
		# used as the callable as repl argument in re.sub
		# re.sub will not call this if not matches,
		# so safe to not implement handling None case
		return self.encode(matchobj.group(1))


def main():
	args = get_args()
	fasta_header_re = re.compile(r"^(>\S+).*$")
	encoder = SeqNameEncoder()
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

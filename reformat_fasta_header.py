#!/usr/bin/env python3

import argparse
import io
import re
import sys


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type=str, nargs="?", default="-",
		help="input fasta file")
	ap.add_argument("--prefix", "-p", type=str, default="s",
		metavar="str",
		help="specify a prefix (default: s)")
	ap.add_argument("--output", "-o", type=str, default="-",
		metavar="file",
		help="output file (default: <stdout>)")
	# parse and refine args
	args = ap.parse_args()
	if args.input == "-":
		args.input = sys.stdin
	if args.output == "-":
		args.output = sys.stdout
	return args


def get_fp(f, *ka, factory=open, **kw):
	if isinstance(f, io.IOBase):
		ret = f
	elif isinstance(f, str):
		ret = factory(f, *ka, **kw)
	else:
		raise TypeError("the first argument of get_fp must be str or io.IOBase,"
			" got '%s'" % type(f).__name__)
	return ret


class SeqNameReformatter(dict):
	def reformat(self, seq_name, *, prefix="s"):
		"""
		reformat an input seq name, return a string (new name) in format
		s_0000000000000001, s_0000000000000002, ...
		if the input header has been encountered previously, old result will be
		returned
		"""
		return "%s_%012u" % (prefix, self.get_sid(seq_name))

	def get_sid(self, seq_name):
		"""
		return an integral seq id;
		return the existing result if encountered previously
		"""
		sid = self.setdefault(seq_name, len(self) + 1)
		# debug
		# assert isinstance(sid, int), sid
		return sid

	def reformat_by_regex_sub(self, matchobj, prefix="s"):
		# used as the callable as repl argument in re.sub
		# re.sub will not call this if not matches,
		# so safe to not implement handling None case
		new_header = self.reformat(matchobj.group(1), prefix=prefix)
		# make sure fasta header leading '>' is preserved
		return (">" if matchobj.group(0).startswith(">") else "") + new_header


def main():
	args = get_args()
	fasta_header_re = re.compile(r"^>(\S+)")
	reformatter = SeqNameReformatter()
	# it is possible to not use formal fasta parser, since the format of fasta
	# seq header line is distinct
	# so simply do modification if it is a header, and throw everything else
	# back unchanged
	reformat_regex_lambda = lambda x: reformatter.reformat_by_regex_sub(x,
		prefix=args.prefix)
	with get_fp(args.input, "r") as ifp:
		with get_fp(args.output, "w") as ofp:
			for line in ifp:
				# replace the header line by only using the fasta 'id' feature
				# comments should not be touched
				ofp.write(fasta_header_re.sub(reformat_regex_lambda, line))
	return


if __name__ == "__main__":
	main()

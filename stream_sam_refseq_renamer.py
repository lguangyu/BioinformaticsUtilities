#!/usr/bin/env python3

import argparse
import sys


def get_args():
	ap = argparse.ArgumentParser(description = \
		"rename reference sequence names in SAM file to fulfill the picky "
		"flavour of anvi'o: a redemption if you forgot to reformat the names "
		"before mapping")
	ap.add_argument("input", type = str, nargs = "?", default = "-",
		help = "input sam file (default: stdin)")
	ap.add_argument("-o", "--output", type = str,
		metavar = "file", default = "-", required = False,
		help = "output sam file (default: stdout)")
	ap.add_argument("--rename-table", type = str,
		metavar = "file",  default = None, required = False,
		help = "if used, report the renaming table (default: off)")
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
		return a integral header id;
		return the existing result if encountered previously
		"""
		sid = self.setdefault(seq_name, len(self) + 1)
		# debug
		#assert isinstance(sid, int), sid
		return sid


class SAMStreamRenamer(object):
	class SAMAlignemtRecord(list):
		@property
		def rname(self):
			return self[2]
		@rname.setter
		def rname(self, _value):
			self[2] = _value
			return
		@property
		def rnext(self):
			return self[6]
		@rnext.setter
		def rnext(self, _value):
			self[6] = _value
			return

	def __init__(self, *ka, **kw):
		super(SAMStreamRenamer, self).__init__(*ka, **kw)
		self.encoder = SeqNameEncoder()
		return

	def _process_refseq(self, line) -> str:
		"""
		rename a refseq's SN tag
		"""
		sp = line.split("\t") # <tab> is the only valid separator in SAM
		for i, s in enumerate(sp):
			if s.startswith("SN:"):
				sp[i] = self.encoder.encode(s[3:])
				break
		return ("\t").join(sp)

	def _process_alignment(self, line) -> str:
		"""
		rename an alignment record's RNAME and RNEXT fields
		"""
		if not line:
			return line
		aln = self.SAMAlignemtRecord(line.split("\t"))
		if aln.rname != "*":
			aln.rname = self.encoder.encode(aln.rname)
		if (aln.rnext != "*") and (aln.rnext != "="):
			aln.rnext = self.encoder.encode(aln.rnext)
		return ("\t").join(aln)

	def process_line(self, sam_line):
		"""
		only response to the reference seqs and alignment section lines; change
		reference seq names in those lines using self.encoder; other irrelavent
		lines will directly pass through;
		"""
		sam_line = sam_line.rstrip() # get rid of EOL
		if sam_line.startswith("@SQ"):
			return self._process_refseq(sam_line)
		elif sam_line.startswith("@"):
			# other header lines are returned without change
			return sam_line
		else:
			# rest are alignemtn records
			return self._process_alignment(sam_line)


def main():
	args = get_args()
	ifp = (sys.stdin if args.input == "-" else open(args.input, "r"))
	ofp = (sys.stdout if args.output == "-" else open(args.output, "w"))
	rn = SAMStreamRenamer()
	for line in ifp:
		ofp.write(rn.process_line(line) + "\n")
	if args.rename_table:
		with open(args.rename_table, "w") as fp:
			for key in rn.encoder.keys():
				fp.write("%s\t%s\n" % (key, rn.encoder.encode(key)))
	ifp.close() # safe for stdin/stdout
	ofp.close()
	return


if __name__ == "__main__":
	main()

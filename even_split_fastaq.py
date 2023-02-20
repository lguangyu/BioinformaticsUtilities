#!/usr/bin/env python3

import argparse
import Bio.SeqIO
import itertools
import os


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type=str,
		help="input FastA/FastQ file")
	ap.add_argument("-f", "--format", type=str, required=True,
		choices=["fasta", "fastq"],
		help="file format (required)")
	ap.add_argument("-n", "--num-splits", type=int, required=True,
		metavar="int",
		help="numbr of splits (required)")
	ap.add_argument("-p", "--prefix", type=str,
		default=None, metavar="prefix",
		help="output prefix (default: same as input)")
	args = ap.parse_args()
	if args.prefix is None:
		args.prefix = args.input
	return args


class FastAQSplitter(object):
	class _FileHandleList(list):
		def __init__(self):
			return

		def close_all(self):
			for i in self:
				i.close()
			return

	@property
	def num_splits(self):
		return self._num_splits

	@num_splits.setter
	def num_splits(self, value):
		if not isinstance(value, int):
			raise TypeError("num_splits must be int")
		if value < 0:
			raise ValueError("num_splits must be positive")
		self._num_splits = value
		return

	@property
	def _output_fhs(self):
		try:
			# got name mangling will be fine since using property()
			return self.__ofhs
		except AttributeError:
			pass
		# create all fhs here
		self.__ofhs = FastAQSplitter._FileHandleList()
		for i in range(self.num_splits):
			fn = "%s.split_%03d.%s"\
				% (self.output_prefix, i, self.format)
			if os.path.isfile(fn):
				raise ValueError("'%s' already exist" % fn)
			self.__ofhs.append(open(fn, "w", buffering=65536))
		return self.__ofhs

	def __init__(self, fmt, num_splits, output_prefix):
		self.format = fmt
		self.num_splits = num_splits
		self.output_prefix = output_prefix
		return

	def split(self, input_file):
		inseq_io = Bio.SeqIO.parse(input_file, format=self.format)
		for seq, fh in zip(inseq_io, itertools.cycle(self._output_fhs)):
			Bio.SeqIO.write(seq, fh, self.format)
		return

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()
		return

	def close(self):
		self._output_fhs.close_all()
		return


def main():
	args = get_args()
	with FastAQSplitter(args.format, args.num_splits, args.prefix) as sp:
		sp.split(args.input)
	return


if __name__ == "__main__":
	main()

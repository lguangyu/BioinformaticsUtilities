#!/usr/bin/env python3
################################################################################
# sam_parser_lite.py
################################################################################
"""
light-weight SAM parser for regular use;

LIMITATIONS
this parser discard all headers;

SYNOPSIS
sam = SAMParserLite.from_file("foo.sam" or open("foo.sam"))
for aln in sam:
	print(aln.qname, ...)
"""

import io
import sys


class Struct(list):
	"""
	list wrapped as struct, can use attribute names to access data fields as
	well as indices
	"""
	class field(property):
		def __init__(self, index, type_cast=str, doc=None):
			super(Struct.field, self).__init__(doc=doc,
				fget=lambda self: type_cast(self[index]))
			return


class SAMParserLite(list):
	class SAMAlignment(Struct):
		"""
		attribute holder for SAM alignment records; header lines are ignored;
		field definition please refer to:
		  https://samtools.github.io/hts-specs/SAMv1.pdf
		"""
		# field definition as property
		qname = Struct.field(0, doc="query name")
		flag = Struct.field(1, type_cast=int)
		rname = Struct.field(2, type_cast=SILVARefSeqName, doc="ref name")
		pos = Struct.field(3, type_cast=int)
		mapq = Struct.field(4, type_cast=int, doc="mapping quality")
		cigar = Struct.field(5)
		rnext = Struct.field(6, doc="ref name of mate/next read")
		pnext = Struct.field(7, type_cast=int, doc="pos of mate/next read")
		tlen = Struct.field(8, type_cast=int, doc="template length")
		seq = Struct.field(9, doc="query seq")
		qual = Struct.field(10, doc="phred33 quality")

		@property
		def extra_tags(self):
			"""
			optional fields represented as tags
			"""
			return self[11:]  # all fields not the first 11

		# def __init__(self, *ka, **kw):
		# super(SAMParserLite.SAMAlignment, self).__init__(*ka, **kw)
		# return

		@classmethod
		def from_sam_text(cls, raw_line):
			fields = raw_line.strip().split("\t")
			aln_rec = cls(fields)
			return aln_rec

	def add_alignment(self, line):
		"""
		add a ling of sam alignment records
		"""
		assert not line.startswith("@"), line
		self.append(self.SAMAlignment.from_sam_text(line))
		return

	def add_header(self, line):
		"""
		ignore all headers
		"""
		return

	@classmethod
	def from_file(cls, file):
		if isinstance(file, str):
			with open(file, "r") as fp:
				return cls.from_file(fp)
		elif isinstance(file, io.IOBase):
			try:
				ret = cls()
				for line in file:
					if line.startswith("@"):
						ret.add_header(line)
					else:
						ret.add_alignment(line)
				return ret
			except UnicodeError as e:
				sys.exit(str(e) + "\nerror: parsing SAM failed; did you input "
					"a BAM file instead of SAM?")
				return
		else:
			raise TypeError("file must be file name or valid file handle")


if __name__ == "__main__":
	pass

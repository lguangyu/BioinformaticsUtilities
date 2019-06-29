#!/usr/bin/env python3

import argparse
import collections
import functools
import gzip
import io
import os
import pickle
import subprocess
import sys


def auto_init_property(init_factory):
	"""
	decorator factory for properties that auto initialize itself at the first
	time access

	ARGUMENTS
	init_factory:
	  factory to be called to generate the initial value to be called at the
	  first time access; also used to wrap the getter method;
	"""
	_attr_name = "_aip__" + init_factory.__name__

	@property
	@functools.wraps(init_factory)
	def getter(self):
		nonlocal _attr_name
		if not hasattr(self, _attr_name):
			setattr(self, _attr_name, init_factory(self))
		return getattr(self, _attr_name)
	assert isinstance(getter, property), type(getter)
	return getter


class Struct(list):
	"""
	list wrapped as struct, use attribute name to access data as well as index
	"""
	class field(property):
		def __init__(self, index, type_cast = str, doc = None):
			super(Struct.field, self).__init__(doc = doc,
				fget = lambda self: type_cast(self[index]))
			return


class NCBIDumpFormat(object):
	"""
	handles the NCBI taxonomy database dmp file format:
	delimiter: \\t|\\t
	EOL: \\t|\\n
	"""
	@classmethod
	def from_dumped_line(cls, raw_line):
		fields = raw_line.replace("\t|\n", "").split("\t|\t")
		return cls(fields)


class NCBITaxonomyNodeName(Struct, NCBIDumpFormat):
	"""
	name field definition please refer to:
	ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz/readme.txt
	"""
	# properties
	tax_id		= Struct.field(0, type_cast = int)
	name_txt	= Struct.field(1)
	unique_name	= Struct.field(2)
	name_class	= Struct.field(3)

	def __init__(self, fields):
		if len(fields) != 4:
			raise ValueError("bad format: " + str(fields))
		super(NCBITaxonomyNodeName, self).__init__(fields)
		return

	@property
	def is_scientific_name(self):
		return self.name_class == "scientific name"


class NCBITaxonomyNodeNameList(list):
	@property
	def scientific_name(self) -> str:
		"""
		scientific name of the node;
		"""
		# this property should point to the name object in self whose name class
		# is 'scientific name'
		return ("NULL" if self._sci_name_obj is None\
			else self._sci_name_obj.name_txt)

	def add_name_obj(self, name_obj):
		if not isinstance(name_obj, NCBITaxonomyNodeName):
			raise TypeError("name_obj must be NCBITaxonomyNodeName")
		self.append(name_obj)
		# check name class value, if is 'scientific name', update
		# self._sci_name_obj attribute
		if name_obj.is_scientific_name:
			self._sci_name_obj = name_obj
		return

	def __init__(self, *ka, **kw):
		super(NCBITaxonomyNodeNameList, self).__init__(*ka, **kw)
		self._sci_name_obj = None
		return


class NCBITaxonomyNode(Struct, NCBIDumpFormat):
	"""
	node field definition please refer to:
	ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz/readme.txt
	"""
	# properties
	tax_id			= Struct.field(0, type_cast = int)
	parent_tax_id	= Struct.field(1, type_cast = int)
	rank			= Struct.field(2)
	embl_code		= Struct.field(3)
	div_id			= Struct.field(4, type_cast = int)
	inh_div_flag	= Struct.field(5, type_cast = int) # 0-1 int
	gc_id			= Struct.field(6, type_cast = int, doc = "genetic code id")
	inh_gc_flag		= Struct.field(7, type_cast = int) # 0-1 int
	mgc_id			= Struct.field(8, type_cast = int, doc = "mitochondrial g.c. id")
	inh_mgc_flag	= Struct.field(9, type_cast = int) # 0-1 int
	gbk_hid_flag	= Struct.field(10, type_cast = int, doc = "genbank hidden flag")
	hit_st_flag		= Struct.field(11, type_cast = int, doc = "hidden subtree flag")
	comments		= Struct.field(12)

	@property
	def parent(self):
		return self._parent_node
	@parent.setter
	def parent(self, value):
		if not isinstance(value, NCBITaxonomyNode):
			raise TypeError("parent must be NCBITaxonomyNode")
		self._parent_node = value
		return

	@auto_init_property
	def name_list(self):
		"""
		list of known names
		"""
		return NCBITaxonomyNodeNameList()

	@property
	def scientific_name(self):
		return self.name_list.scientific_name

	def add_name_obj(self, *ka, **kw):
		self.name_list.add_name_obj(*ka, **kw)
		return

	def __init__(self, fields):
		if len(fields) != 13:
			raise ValueError("bad format: " + str(fields))
		super(NCBITaxonomyNode, self).__init__(fields)
		return

	def self_verify(self):
		if self.parent.tax_id != self.parent_tax_id:
			raise ValueError("node '%d' parent got '%d' (expected '%d')" %\
				(self.tax_id, self.parent.tax_id, self.parent_tax_id))
		for i in self.name_list:
			if i.is_scientific_name and i.name_txt != self.scientific_name:
				raise ValueError("node '%d' has ambiguous scientific names "
					"[self.scientific_name -> '%s'] "
					"[other -> '%s']" % (self.tax_id, self.scientific_name,
						i.name_txt))
		return


class NCBITaxonomyDB(collections.UserDict):
	def __getitem__(self, *ka, **kw) -> NCBITaxonomyNode:
		"""
		make database query by tax_id, return a node (NCBITaxonomyNode)
		"""
		return super(NCBITaxonomyDB, self).__getitem__(*ka, **kw)

	def query(self, tax_id: int = None) -> NCBITaxonomyNode:
		"""
		make database query, return a node (NCBITaxonomyNode)
		"""
		if tax_id is not None:
			return self.__getitem__(tax_id)
		else:
			raise ValueError("invalid query")

	def add_node(self, node: NCBITaxonomyNode):
		"""
		add a new node to the database
		"""
		if not isinstance(node, NCBITaxonomyNode):
			raise TypeError("must be NCBITaxonomyNode")
		if node.tax_id in self:
			raise ValueError("tax id %d already exist" % node.tax_id)
		self.update({node.tax_id: node})
		return

	############################################################################
	# database I/O: from dump files
	@classmethod
	def from_dumps(cls, nodes_dump, names_dump):
		"""
		load database from .dmp files

		ARGUMENTS:
		nodes_dump:
		  path to the nodes.dmp file
		names_dump:
		  path to the names.dmp file
		"""
		db = cls()
		print("nodes file: %s" % os.path.abspath(nodes_dump), file = sys.stderr)
		print("names file: %s" % os.path.abspath(names_dump), file = sys.stderr)
		print("loading nodes...", file = sys.stderr)
		with open(nodes_dump, "r") as fp:
			for line in fp:
				node = NCBITaxonomyNode.from_dumped_line(line)
				db.add_node(node)
		print("loading names...", file = sys.stderr)
		with open(names_dump, "r") as fp:
			for line in fp:
				name_obj = NCBITaxonomyNodeName.from_dumped_line(line)
				target = db.query(tax_id = name_obj.tax_id)
				target.add_name_obj(name_obj)
		# now polishing data after load has completed
		print("finalizing...", file = sys.stderr)
		db._link_parents()
		print("done", file = sys.stderr)
		return db

	def _link_parents(self):
		# link each nodes to its parent, node.parent will return the parent node
		# instead of parent node's tax_id (node.parent_tax_id)
		for node in self.values():
			assert isinstance(node, NCBITaxonomyNode), type(node).mro()
			node.parent = self.query(tax_id = node.parent_tax_id)
		return

	############################################################################
	# database I/O: from/to pickle
	def to_pickle(self, file, compresslevel: int = 9, *ka, **kw):
		"""
		pickle loaded database as gzipped dump
		"""
		with gzip.open(file, "wb", compresslevel) as fp:
			# added this since '<stdout>'
			fn = (os.path.abspath(fp.name) if fp.name != "<stdout>" else fp.name)
			print("pickling: %s" % fn, file = sys.stderr)
			pickle.dump(self, fp)
		return

	@classmethod
	def from_pickle(cls, file):
		with gzip.open(file, "rb") as fp:
			print("unpickling: %s" % os.path.abspath(fp.name), file = sys.stderr)
			ret = pickle.load(fp)
		assert isinstance(ret, NCBITaxonomyDB)
		return ret

	############################################################################
	# test
	def self_verify(self):
		for node in self.values():
			assert isinstance(node, NCBITaxonomyNode), type(node).mro()
			node.self_verify()
		return


################################################################################
# build database, if used directly (as __main__ module)
################################################################################
class DownloadFromNCBIFTP(argparse.Action):
	taxdump_url = r"ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
	def __call__(self, parser, namespace, values, option_string):
		if not values:
			return
		cmd = ["wget", "-O", values, self.taxdump_url]
		if subprocess.call(cmd):
			print("system call to %s had non-zero return value\n"
				"try manually download file from '%s'"\
				% (str(cmd), self.taxdump_url), file = sys.stderr)
			parser.exit(1)
		return parser.exit(0)


class TestLoad(argparse.Action):
	def __call__(self, parser, namespace, values, option_string):
		if not values:
			return
		db = NCBITaxonomyDB.from_pickle(values)
		db.self_verify()
		return parser.exit(0)


def get_args():
	class CompressLevel(int):
		def __init__(self, *ka, **kw):
			super(CompressLevel, self).__init__(*ka, **kw)
			if (self < 1) or (self > 9):
				raise ValueError("compress level must between 1-9")
			return

	ap = argparse.ArgumentParser()
	ap.add_argument("-n", "--nodes-dump", type = str, required = True,
		metavar = "nodes.dmp",
		help = "specify nodes.dump file (required);")
	ap.add_argument("-a", "--names-dump", type = str, required = True,
		metavar = "names.dmp",
		help = "specify names.dump file (required);")
	ap.add_argument("-o", "--pickle", type = str,
		metavar = ".pkl.gz",
		help = "pickle output to this <file> instead of stdout")
	ap.add_argument("-l", "--compress-level", type = CompressLevel,
		metavar = "1-9", default = 9,
		help = "output compress level (default: 9)")
	ap.add_argument("--download", type = str, action = DownloadFromNCBIFTP,
		metavar = ".tar.gz",
		help = "download data from NCBI (%s) and exit;"\
			% DownloadFromNCBIFTP.taxdump_url)
	ap.add_argument("--test-load", type = str, action = TestLoad,
		metavar = ".pkl.gz",
		help = "test load a pickled database from <file> and exit; "
			"no other action will be performed")
	args = ap.parse_args()
	return args


if __name__ == "__main__":
	args = get_args()
	NCBITaxonomyDB.from_dumps(args.nodes_dump, args.names_dump)\
		.to_pickle(args.pickle or sys.stdout.buffer, args.compress_level)

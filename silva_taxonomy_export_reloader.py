#!/usr/bin/env python3
################################################################################
# silva_taxonomy_export_reloader.py
################################################################################
# SYNOPSIS
# load SILVA exported taxonomy database to a searchable form
################################################################################

import argparse
import collections
import functools
import os
import sys


class KeyNodeMap(dict):
	def add_node(self, key, node):
		if not isinstance(node, SilvaTaxonomyDBNode):
			raise TypeError("key-node map only accept SilvaTaxonomyDBNode as "
				"elements, got '%s'" % type(node))
		if key in self:
			raise ValueError("key '%s' already exists" % str(key))
		super(KeyNodeMap, self).__setitem__(key, node)
		return node

	@functools.wraps(add_node, assigned = ("__doc__"))
	def __setitem__(self, *ka, **kw):
		return self.add_node(*ka, **kw)


class SilvaTaxonomyDBNode(object):
	"""
	node in SilvaTaxonomyDB;
	each node can either be accessed via map from accession, scientific name
	and/or taxid;
	"""
	def __init__(self, taxid, parent, *ka, tax_level = None,
			scientific_name = None, accession = None, **kw):
		super(SilvaTaxonomyDBNode, self).__init__(*ka, **kw)
		if not isinstance(taxid, int):
			raise TypeError("taxid must be int")
		self.taxid = taxid
		self.parent = parent
		self.tax_level = tax_level
		if not isinstance(scientific_name, str):
			raise TypeError("scientific_name must be str")
		self.scientific_name = scientific_name
		self.accession = accession
		self.children = KeyNodeMap()
		return

	def add_child(self, child):
		"""
		add child to parent's children list, without back connection
		"""
		if not isinstance(child, SilvaTaxonomyDBNode):
			raise TypeError("child must be SilvaTaxonomyDBNode")
		self.children.add_node(child.scientific_name, child)
		return

	def set_parent(self, parent):
		"""
		set parent of a child, without back connection
		"""
		if not isinstance(parent, SilvaTaxonomyDBNode):
			raise TypeError("parent must be SilvaTaxonomyDBNode")
		self.parent = parent
		return

	@classmethod
	def connect(cls, *, parent, child):
		"""
		connect bidirectionally between parent and child
		"""
		parent.add_child(child)
		child.set_parent(parent)
		return

	def get_path(self) -> ["SilvaTaxonomyDBNode"]:
		"""
		get a path from root to this node
		"""
		path = list()
		current = self
		path.append(current)
		while current.parent:
			path.append(current.parent)
			current = current.parent
		return reversed(path)


class SilvaTaxonomyDB(object):
	"""
	SILVA taxonomy database

	reload SILVA taxonomy database from exported files
	"""
	@property
	def root(self):
		return self._root_node

	def __init__(self, *ka, **kw):
		super(SilvaTaxonomyDB, self).__init__(*ka, **kw)
		self.taxid_to_node = KeyNodeMap()
		self.acc_to_node = KeyNodeMap()
		self._add_root()
		return

	def _add_root(self):
		root = SilvaTaxonomyDBNode(1, None,
			tax_level = "root", scientific_name = "root", accession = "root")
		self._root_node = root
		self.taxid_to_node.add_node(key = root.taxid, node = root)
		self.acc_to_node.add_node(key = root.accession, node = root)
		return

	def path_walk(self, path: collections.deque, rela_node = None)\
			-> ("remain path", SilvaTaxonomyDBNode):
		"""
		walk down a path, continue if node already exists at each step; return
		the last node accessed, and the remaining path at that point;
		"""
		if rela_node is None:
			rela_node = self.root
		# recursive walk
		while bool(path) and (path[0] in rela_node.children):
			rela_node = rela_node.children[path.popleft()] # path changed here
		return path, rela_node

	def path_create(self, path: collections.deque, rela_node = None)\
			-> SilvaTaxonomyDBNode:
		"""
		walk down a path, continue if node already exists at each step, or
		create them if does not; return the last accessed or created node;
		"""
		# first walk down as far as node exists
		path, rela_node = self.path_walk(path, rela_node)
		# create the rest
		while path:
			new_node = SilvaTaxonomyDBNode(0, rela_node,
				scientific_name = path.popleft()) # path changed here
			rela_node.add_child(new_node)
			#assert new_node.scientific_name in rela_node.children
			#assert new_node.parent is rela_node
			rela_node = new_node
		return rela_node

	@classmethod
	def from_exports(cls, tax_path, acc_taxid):
		"""
		load SilvaTaxonomyDB from two SILVA export files

		ARGUMENTS (class method)
		tax_path:
		  exported txt of taxonomy node path (e.g. tax_slv_ssu_132.txt)
		acc_taxid:
		  exported accession to taxid map (e.g. tax_slv_ssu_132.acc_taxid)
		"""
		new = SilvaTaxonomyDB()
		new._load_tax_path_tree(tax_path)
		new._load_acc_taxid(acc_taxid)
		return new

	def _load_tax_path_tree(self, tax_path):
		"""
		build taxonomic tree using tax_path file
		"""
		with open(tax_path, "r") as fp:
			for line in fp:
				fields = line.strip("\n").split("\t")
				if len(fields) != 5:
					raise ValueError("invalid line format: '%s'" % str(fields))
				# parse the fields
				path, taxid, level, _, _ = fields # c#3, c#4 unknown
				# remove trailing ';' if exists
				path = collections.deque(path.strip(";").split(";"))
				assert len(path) >= 1, str(path)
				# add new node using parsed information
				node = self.path_create(path)
				node.taxid = int(taxid)
				node.tax_level = level
				# add to search key-node maps
				self.taxid_to_node.add_node(node.taxid, node)
		return

	def _load_acc_taxid(self, acc_taxid):
		with open(acc_taxid, "r") as fp:
			for line in fp:
				# it is two-column, 1st accession, 2nd taxid
				acc, taxid = line.strip("\n").split("\t")
				taxid = int(taxid)
				# update the taxid
				node = self.query(taxid = taxid)
				node.accession = acc
				self.acc_to_node.add_node(node.accession, node)
		return

	def query(self, taxid = None, *, accession = None) -> SilvaTaxonomyDBNode:
		"""
		make database query, using any of taxid or accession;
		if provided with multiple, lower piriority one(s) will be ignored;
		
		PRIORITY
		taxid > accession (default is taxid)
		"""
		if taxid is not None:
			return self.taxid_to_node[taxid]
		if accession is not None:
			return self.acc_to_node[accession]
		raise ValueError("must specify either of taxid or accession")
		return


if __name__ == "__main__":
	pass
	# currently for lite test
	#
	#db = SilvaTaxonomyDB()
	#db.from_exports(".dev/tax_slv_ssu_132.txt",
	#	".dev/tax_slv_ssu_132.acc_taxid")
	#path = db.query(accession = "AAAA02010377.14668.16277").get_path()
	#print([i.scientific_name for i in path])

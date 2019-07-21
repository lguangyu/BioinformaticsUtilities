#!/usr/bin/env python3
################################################################################
# jplace_tree.py
################################################################################
"""
parse the ref tree in jplace (pplacer output) as a Newick tree; uses
newick_parser_lite.py as base Newick tree parser library;

SYNOPSIS

tree = JplaceTree.load_string(<json *.jplace>["tree"])
# or
tree = JplaceTree()
tree.parse(<json *.jplace>["tree"])
# get the root
root = tree.root
"""

import functools
import numbers
import re
# custom import
from . import newick_parser_lite


class JplaceTreeFormatError(newick_parser_lite.NewickFormatError):
	pass


################################################################################
# general Jplace tree that parses and stores all the information from pplacer
# output
class JplaceTreeNode(newick_parser_lite.NewickTreeNodeBase,
		newick_parser_lite.tree_base.TreeNodeGeometryBase):
	@property
	def node_id(self):
		"""
		internal id of the node (integer)
		"""
		return getattr(self, "_nid", -1)

	@property
	def ref_name(self):
		return getattr(self, "_name", "")
	@ref_name.setter
	def ref_name(self, value):
		if not isinstance(value, str):
			raise TypeError("ref_name must be str")
		self._name = value
		return

	@property
	def parent_distance(self):
		return getattr(self, "_pdist", 0)
	@parent_distance.setter
	def parent_distance(self, value):
		if not isinstance(value, numbers.Real):
			raise TypeError("parent_distance must be real valued")
		self._pdist = value
		return

	def handler_bare_text(self, s):
		if not isinstance(s, str):
			raise TypeError("s must be str")
		try:
			name, props = s.split(":")
		except IndexError:
			raise JplaceTreeFormatError("'%s' expected to have format "
				"'name:props'" % s)
		self.ref_name = name
		m = re.match(r"([e.\-\d]*){(\d+)}(\[(\d+)\])?", props)
		if not m:
			raise JplaceTreeFormatError("bad format in node property string "
				"'%s'" % props)
		self._nid = int(m.group(2)) # directly _nid for RO property
		self.parent_distance = float(m.group(1))
		return

	def place_h(self, start_pos) -> "end_pos":
		"""
		find horizontal position for this node; if has no children, put itself
		on <start_pos>, increment by 1 and return it; if has children, put
		itself in the middle point of the left-most and right-most direct
		children, and return the value of <start_pos> unchanged;
		"""
		if not self.children:
			self.h_pos = start_pos
			return start_pos + 1
		else:
			self.h_pos = (self.child_hmin + self.child_hmax) / 2
			return start_pos # in this case no need to increment

	def place_v(self, parent_height):
		"""
		find vertical position for this node, place itself on <parent_height> +
		self.parent_distance; not recursive into children;
		"""
		self.v_pos = parent_height + self.parent_distance
		return

	def subtree_place_h(self, start_pos):
		"""
		find horizontal position for this node and all its children (if any),
		by recursively call place_h() method on all nodes in a bottom-up and
		left-right traversal;
		"""
		for node in self.children:
			start_pos = node.subtree_place_h(start_pos)
		return self.place_h(start_pos)

	def subtree_place_v(self, parent_height):
		"""
		find vertical position for this node, and all its children (if any),
		starting from 'parent_height' by recursively call place_v() methods on
		all nodes in a top-down traversal;
		"""
		self.place_v(parent_height)
		for node in self.children:
			node.subtree_place_v(self.v_pos)
		return


class JplaceTree(newick_parser_lite.NewickTreeBase,
		newick_parser_lite.tree_base.TreeGeometryBase):
	node_type = JplaceTreeNode

	def __init__(self, *ka, **kw):
		super(JplaceTree, self).__init__(*ka, **kw)
		self._id_map = dict()
		return

	@functools.wraps(newick_parser_lite.NewickTreeBase.parse)
	def parse(self, *ka, **kw):
		# this parse() method also stores internal node id for search
		ret = super(JplaceTree, self).parse(*ka, **kw)
		for i in self.iter_all_nodes:
			assert i.node_id not in self._id_map
			self._id_map[i.node_id] = i
		return ret

	def __getitem__(self, node_id):
		"""
		get node by internal node id
		"""
		return self._id_map[node_id]

	def place_nodes(self):
		"""
		place all nodes and assign their h_pos and v_pos values;
		"""
		self.root.subtree_place_h(0)
		self.root.subtree_place_v(0)
		return

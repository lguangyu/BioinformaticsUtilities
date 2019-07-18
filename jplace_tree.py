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
class JplaceTreeNode(newick_parser_lite.NewickTreeNodeBase):
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


class JplaceTree(newick_parser_lite.NewickTreeBase):
	node_t = JplaceTreeNode

	def __init__(self, *ka, **kw):
		super(JplaceTree, self).__init__(*ka, **kw)
		self._id_map = dict()
		return

	@functools.wraps(newick_parser_lite.NewickTreeBase.parse)
	def parse(self, *ka, **kw):
		# this parse() method also stores internal node id for search
		ret = super(JplaceTree, self).parse(*ka, **kw)
		for i in self.all_nodes:
			assert i.node_id not in self._id_map
			self._id_map[i.node_id] = i
		return ret

	def __getitem__(self, node_id):
		"""
		get node by internal node id
		"""
		return self._id_map[node_id]


################################################################################
# Jplace tree that implements geometry properties, some necessary in plotting
class JplaceTreeNodeGeo(JplaceTreeNode):
	@property
	def h_pos(self):
		"""
		horizontal position; the left-most leaf node has horizontal position 0,
		and the right-most has position #leaves - 1; each internal node will be
		placed in the middle of its left-most and right-most child, i.e.
		(min(children.h_pos) + max(children.h_pos)) / 2;
		"""
		return getattr(self, "_h_pos", None)
	@h_pos.setter
	def h_pos(self, value):
		if not isinstance(value, numbers.Real):
			raise TypeError("h_pos must be real valued")
		self._h_pos = value
		return

	@property
	def v_pos(self):
		"""
		vertical position; the root has vertical position 0, each other node
		has the cumulative value of parent_distances all the way to root;
		"""
		return getattr(self, "_v_pos", None)
	@v_pos.setter
	def v_pos(self, value):
		if not isinstance(value, numbers.Real):
			raise TypeError("v_pos must be real valued")
		self._v_pos = value
		return

	@property
	def radius(self):
		"""
		radius of the bulb
		"""
		return getattr(self, "_size", 0)
	@radius.setter
	def radius(self, value):
		if not isinstance(value, numbers.Real):
			raise TypeError("diameter must be real valued")
		self._size = value
		return

	def place_h(self, start_pos) -> "end_pos":
		"""
		find horizontal position for this node and all its children (if any);
		starting from 'start_pos' (left most), and return the right-most leaf's
		position + 1;
		this is essentially bottom-up and left->right traversal;
		"""
		if not self.children:
			self.h_pos = start_pos
			return start_pos + 1
		else:
			for node in self.children:
				start_pos = node.place_h(start_pos)
			self.h_pos = (self.child_hmin + self.child_hmax) / 2
			return start_pos # in this case no need to increment

	def place_v(self, parent_height):
		"""
		find vertical position for this node and all its children (if any);
		starting from 'parent_height';
		this is essentially top-down traversal (arbitrary horizontal order);
		"""
		self.v_pos = parent_height + self.parent_distance
		for node in self.children:
			node.place_v(self.v_pos)
		return

	@property
	def child_hmin(self):
		"""
		the h_pos of left-most direct child;
		if no children, return self.h_pos;
		"""
		if self.children:
			return self.children[0].h_pos
		return self.h_pos
	@property
	def child_hmax(self):
		"""
		the h_pos of right-most direct child;
		if no children, return self.h_pos;
		"""
		if self.children:
			return self.children[-1].h_pos
		return self.h_pos

	@property
	def subtree_hmin(self):
		"""
		the h_pos of left-most direct and indirect child;
		if no children, return self.h_pos;
		"""
		if self.children:
			return self.children[0].subtree_hmin
		return self.h_pos
	@property
	def subtree_hmax(self):
		"""
		the h_pos of right-most direct and indirect child;
		if no children, return self.h_pos;
		"""
		if self.children:
			return self.children[-1].subtree_hmax
		return self.h_pos

	@property
	def child_vmin(self):
		"""
		the minimal v_pos of direct child; if no children, return None;
		"""
		if self.children:
			return min([i.v_pos for i in self.children])
		return None
	@property
	def child_vmax(self):
		"""
		the minimal v_pos of direct child; if no children, return None;
		"""
		if self.children:
			return max([i.v_pos for i in self.children])
		return None

	@property
	def subtree_vmin(self):
		"""
		the minimal v_pos of self or any direct/indirect child;
		if no children, return self.v_pos;
		"""
		return self.v_pos # this is always true
	@property
	def subtree_vmax(self):
		"""
		the maximal v_pos of self or any direct/indirect child;
		if no children, return self.v_pos;
		"""
		v_poses = [i.v_pos for i in self.all_subtree_nodes]
		return max(v_poses)


class JplaceTreeGeo(JplaceTree):
	node_t = JplaceTreeNodeGeo

	@property
	def hmin(self):
		return self.root.subtree_hmin
	@property
	def hmax(self):
		return self.root.subtree_hmax
	@property
	def vmin(self):
		return self.root.subtree_vmin
	@property
	def vmax(self):
		return self.root.subtree_vmax

	def place_nodes(self):
		"""
		place all nodes and assign their h_pos and v_pos values;
		"""
		self.root.place_h(0)
		self.root.place_v(0)
		return


if __name__ == "__main__":
	import unittest

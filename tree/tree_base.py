#!/usr/bin/env python3
################################################################################
# tree_base.py
################################################################################
"""
light-weight tree structure classes

SYNOPSIS
"""
# TODO: complete the module-level docstr

import abc
import itertools
import numbers


class TreeNodeBase(object):
	"""
	base class of tree nodes; basic access of tree structure such as children,
	parent, etc.
	"""
	# TODO: complete the docstr
	@property
	def parent(self):
		return self.__parent

	@property
	def children(self):
		return self.__children
	@property
	def n_children(self):
		"""
		number of direct nodes
		"""
		return len(self.children)

	@property
	def n_subtree_nodes(self):
		"""
		number of all direct/indirect nodes in subtree
		"""
		return self.__n_subtree_nodes

	@property
	def all_subtree_nodes(self):
		"""
		traverse all nodes in the subtree rooted at current node;
		"""
		yield self
		for i in itertools.chain(*map(lambda x: x.all_subtree_nodes,
			self.children)):
			yield i

	def __init__(self, start = None, end = None, *ka, **kw):
		super(TreeNodeBase, self).__init__(*ka, **kw)
		self.__parent = None
		self.__children = list()
		self.__n_subtree_nodes = 0
		return

	def __repr__(self):
		return "<%s[0x%x] pos=%s:%s>" % (type(self).__name__, id(self),
			str(self.start), str(self.end))

	def __iter__(self):
		"""
		return the iterator of all direct children
		"""
		return iter(self.children)

	def _lazy_count_subtree_nodes(self):
		"""
		count substree nodes not recursively; simply caculate from all direct
		children; manually using this method may end up with error;
		"""
		self.__n_subtree_nodes =\
			sum([i.n_subtree_nodes for i in self.children]) + self.n_children
		return

	def sort(self, *, reverse = False):
		"""
		sort children in ascending order based on their total number of nodes in
		subtree; sort in descending order if reversed = True;
		"""
		if not self.children:
			return
		self.children.sort(key = lambda i: i.n_subtree_nodes, reverse = reverse)
		return

	def is_child_of(self, node):
		"""
		return True if <self> is a direct/indirect child of <node>;
		"""
		if not isinstance(node, TreeNodeBase):
			raise TypeError("node must be TreeNodeBase, not '%s'"\
				% type(node).__name__)
		trig = self.parent # avoid (self is node) case
		while trig is not None:
			if trig is node:
				return True
			trig = trig.parent
		return False

	def is_parent_of(self, node):
		"""
		return True if <self> is a direct/indirect parent of <node>;
		"""
		if not isinstance(node, TreeNodeBase):
			raise TypeError("node must be TreeNodeBase, not '%s'"\
				% type(node).__name__)
		return node.is_child_of(self)

	def _recount_subtree_nodes_recup(self):
		"""
		upward-recursion to re-calculate number of subtree nodes
		"""
		trig = self
		while trig is not None:
			trig._lazy_count_subtree_nodes()
			trig = trig.parent
		return

	def add_child(self, node):
		"""
		add a node to children list, also bind self as child node's parent;
		"""
		if not isinstance(node, TreeNodeBase):
			raise TypeError("node must be TreeNodeBase, not '%s'"\
				% type(node).__name__)
		self.children.append(node) # add node to parent's children list
		node.__parent = self # bind self to child's parent
		self._recount_subtree_nodes_recup()
		return


class TreeBase(object):
	"""
	base class of tree
	"""
	# derived class can override this attribute to use a different node factory
	# type (must inherit NewickTreeNodeBase class)
	node_type = TreeNodeBase

	@property
	def root(self):
		try:
			return self.__root
		except AttributeError:
			return None
	def force_set_root(self, root):
		if not isinstance(root, self.node_type):
			raise TypeError("root must be %s, not '%s'"\
				% (self.node_type.__name__, type(root).__name__))
		self.__root = root
		return

	@property
	def n_total_nodes(self):
		return self.root.n_subtree_nodes

	def __new__(cls, *ka, **kw):
		if getattr(cls, "node_type", None) is None:
			raise ValueError("can not instantiate derived tree class with "
				"unset 'node_type' class attribute")
		for bc in cls.mro():
			expect = getattr(bc, "node_type", None)
			if (expect) and (not issubclass(cls.node_type, expect)):
				raise TypeError("%s.node_type is expected to be subclass of "
					"'%s' by base class '%s'" % (cls.__name__, expect.__name__,
					bc.__name__))
		return super(TreeBase, cls).__new__(cls, *ka, **kw)

	def __iter__(self):
		return iter(self.root)

	@property
	def iter_all_nodes(self):
		"""
		iterator recursively walk through all nodes;
		"""
		return iter(self.root.all_subtree_nodes)

	def sort(self, *, reverse = False):
		"""
		sort each node's children in ascending order based on their total number
		of subtree nodes; sort in ascending order if reverse = True;
		"""
		for i in self.iter_all_nodes:
			i.sort(reverse = reverse)
		return


class TreeParserAbstract(abc.ABC):
	"""
	abstract base class of tree parser;
	"""
	@abc.abstractmethod
	def parse(self, s, *ka, **kw):
		"""
		parses a string 's' into a tree structure;
		"""
		pass


class TreeNodeGeometryBase(TreeNodeBase):
	"""
	geomertic properties of a tree node, including its location, the span of its
	children, etc;
	"""
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


class TreeGeometryBase(TreeBase):
	"""
	base class for tree that handling nodes with geometry properties
	"""
	node_type = TreeNodeGeometryBase

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

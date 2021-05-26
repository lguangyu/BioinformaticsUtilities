#!/usr/bin/env python3


class TreeNodeBase(object):
	def __init__(self, parent, label: str, *ka, **kw):
		super().__init__(*ka, **kw)
		self._set_parent(parent)
		self.label = label
		self.children = dict()
		return

	@property
	def parent(self):
		return self._parent
	# leave self.parent without setter
	def _set_parent(self, parent):
		if parent is None:
			self._parent = None
			self._height = 0
		elif isinstance(parent, TreeNodeBase):
			self._parent = parent
			self._height = parent.height + 1
		else:
			# only throw out the TreeNodeBase, hide None option;
			# parent=None is root node.
			raise TypeError("parent must be TreeNodeBase, not '%s'"\
				% type(parent).__name__)
		return

	@property
	def is_root(self):
		return (self.parent is None)

	@property
	def height(self):
		return self._height

	@property
	def is_leaf(self):
		return not self.child

	def create_child(self, label, *ka, factory = None, **kw):
		# if _factory is None, use the same type of nodes as self
		# *ka and **kw are passed to the factory
		factory = type(self) if factory is None else factory
		child = factory(parent = self, label = label, *ka, **kw)
		self.children[label] = child
		return child

	def get_label_path(self) -> list:
		if self.is_root:
			ret = list()
		else:
			ret = self.parent.get_taxon_path()
			ret.append(self.label)
		return ret

	def traverse(self, *, depth_first = True):
		if not depth_first:
			yield self
		for child in self.children:
			yield from child.traverse(depth_first = depth_first)
		if depth_first:
			yield self
		return


class TreeNodeNumCountMixin(object):
	def __init__(self, *ka, count = 0, **kw):
		super().__init__(*ka, **,kw)
		self.count = count
		return

	def sum_subtree_count(self):
		# subtree total count = self.count + subtree count for each child
		ret = self.count
		for child in self.children.values():
			ret += child.sum_subtree_count()
		return ret


class TreeNodeOtuMixin(object):
	def __init__(self, *ka, **kw):
		super().__init__(*ka, **kw)
		self.otus = list()
		return

	def add_otu(self, otu: str):
		self.otus.append(otu)
		return


class TaxTreeNode(TreeNodeOtuMixin, TreeNodeNumCountMixin, TreeNodeBase):
	pass

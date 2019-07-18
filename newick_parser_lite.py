#!/usr/bin/env python3
################################################################################
# newick_parser_lite.py
################################################################################
"""
light-weight Newick tree parser in pure python implementation

SYNOPSIS
"""

import abc
import warnings


class NewickParseError(RuntimeError):
	pass


class NewickTreeNodeBase(abc.ABC):
	@property
	def parent(self):
		return self.__parent

	@property
	def children(self):
		return self.__children
	@property
	def n_children(self):
		return len(self.children)

	def __init__(self, start = None, end = None, *ka, **kw):
		super(NewickTreeNodeBase, self).__init__(*ka, **kw)
		self.__parent	= None
		self.__children	= list()
		self.start		= start # position in buf
		self.end		= end # position in buf
		self.__ready_for_next_node = True
		return

	def __repr__(self):
		return "<%s[0x%x] pos=%s:%s>" % (type(self).__name__, id(self),
			str(self.start), str(self.end))

	def add_child(self, child):
		"""
		add a node to children list, also bind self as child's parent
		"""
		if not isinstance(child, NewickTreeNodeBase):
			raise TypeError("child must be NewickTreeNodeBase")
		self.children.append(child) # add child to children list
		child.__parent = self # bind self to child's parent
		return
			

	############################################################################
	# these methods should only be used by parser
	def parser_add_child(self, child):
		"""
		add a child in parsing process; extra logic and checks are done than
		bare adding a child
		"""
		if (not isinstance(child, NewickTreeNodeBase))\
			or (child.start is None):
			raise ValueError("child must be NewickTreeNodeBase, its 'start' "\
				"must be correctly set before adding as a child")
		# in parsing, node and separator are necessary to come one after another
		if not self.__ready_for_next_node:
			raise NewickParseError("expected separator between two nodes at c: "
				"%d" % child.start)
		self.add_child(child)
		self.__ready_for_next_node = False
		return

	def parser_add_separator(self):
		self.__ready_for_next_node = True
		return

	def parser_add_bare_text(self, pos, s):
		if self.__ready_for_next_node:
			# in this case, parse the text as a child node and add as child
			child = type(self).bare_text_as_node(s)
			child.start, child.end = pos, pos + len(s)
			self.parser_add_child(child)
			return
		#elif self.children:
		# safe since if self.__ready_for_next_node is False there must be at
		# least one child in children list
		else:
			# treat the text as trailing text of the last added child node
			self.children[-1].add_trailing_text(s)
		return

	############################################################################
	# these methods should only be used by parser
	@classmethod
	@abc.abstractmethod
	def bare_text_as_node(cls, s):
		pass

	@abc.abstractmethod
	def add_trailing_text(self, s):
		pass


class NewickTreeNode(NewickTreeNodeBase):
	@classmethod
	def bare_text_as_node(cls, s, *ka, **kw):
		if not isinstance(s, str):
			raise TypeError("s must be str")
		new = cls(*ka, **kw)
		return new

	def add_trailing_text(self, s):
		if not isinstance(s, str):
			raise TypeError("s must be str")
		return


class NewickTree(object):
	# derived class can override this attribute to use a different node factory
	# or type; however, the final type must inherit NewickTreeNodeBase class
	node_t = NewickTreeNode

	@property
	def root(self):
		return self.__root

	def __init__(self, *ka, **kw):
		super(NewickTree, self).__init__(*ka, **kw)
		self.__root = None
		return

	@classmethod
	def from_string(cls, s, *ka, **kw):
		# parser local variables
		if not isinstance(s, str):
			raise TypeError("s must be str")
		# create tree
		tree = cls(*ka, **kw)
		tree.__root = tree.node_t()
		# parser local variables
		stack = list([tree.root]) # used for parenthese matching
		# keep tracking the current node
		tree.root.start = last_pos = 0 # last_pos used to slice bare string
		# parsing
		for pos, c in enumerate(s):
			assert stack
			top = stack[-1]
			if c == "(":
				if pos > last_pos:
					junk_start = last_pos
					warnings.warn("junk '%s' discarded at c: %d:%d"\
						% (s[junk_start:pos], junk_start, pos))
				# open a new node
				new_node = tree.node_t(start = pos)
				top.parser_add_child(new_node)
				# parser work
				stack.append(new_node)
				last_pos = pos + 1
			elif c == ",":
				# this may pass empty string to top.parser_add_bare_text()
				top.parser_add_bare_text(pos, s[last_pos:pos])
				top.parser_add_separator()
				last_pos = pos + 1
			elif c == ")":
				if top is tree.root:
					raise NewickParseError("orphan ')' encountered at c: %d"\
						% pos)
				top.end = pos + 1
				# this may pass empty string to top.parser_add_bare_text()
				top.parser_add_bare_text(pos, s[last_pos:pos])
				stack.pop() # now can pop the stack
				last_pos = pos + 1
		# check if stack is clean
		top = stack[-1] # this is safe, we must at least have tree.root inside
		# otherwise error raised in c == ')' case
		if top is not tree.root:
			# the stack is not clean -> must have ummatched parenthese
			raise NewickParseError("expected ')' to close '(' at c: %d"\
				% top.start)
		# this may pass empty string to top.parser_add_bare_text()
		top.parser_add_bare_text(pos, s[last_pos:])
		tree.root.end = len(s)
		return tree


if __name__ == "__main__":
	import unittest
	t = NewickTree.from_string("12(aaa,cc(b,3):asd),(),,,")

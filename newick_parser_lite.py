#!/usr/bin/env python3
################################################################################
# newick_parser_lite.py
################################################################################
"""
light-weight Newick tree parser in pure python implementation

SYNOPSIS

class MyNewickTreeNode(NewickTreeNodeBase):
	def handler_bare_text(self, s):
		# logics on how to parse bare text encountered, to info of current node
		...

class MyNewickTree(NewickTreeBase):
	# must specify a derived class of node to use
	node_t = MyNewickTreeNode

tree = MyNewickTree.load_string(<input>)
# or
tree = MyNewickTree()
tree.parse(<input>)
# get the root
root = tree.root
"""

import abc
#import functools
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
		add a node to children list, also bind self as child's parent;
		"""
		if not isinstance(child, NewickTreeNodeBase):
			raise TypeError("child must be NewickTreeNodeBase")
		self.children.append(child) # add child to children list
		child.__parent = self # bind self to child's parent
		return

	############################################################################
	# these methods should only be used during parsing
	# not encouraged for derived classes to override
	def parser_add_child(self, child):
		"""
		add a child during parsing; extra logic and checks are done than simply
		adding a node; these checks are related to format checking, while not
		required in other cases;
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
		"""
		called when parser encounters a separator ',';
		a separator is expected between two nodes, otherwise raise error when
		trying adding the second node;
		"""
		self.__ready_for_next_node = True
		return

	def parser_put_bare_text(self, pos, s):
		"""
		called when parser encounters a substring looks like bare text; bare
		texts are any characters other than controlling chars '(', ')' and ',';

		parser_put_bare_text() will first check locally to find a correct node
		which should accpet this data (or create one if necessary), then call
		that node's handler_bare_text() to digest the string; this method is not
		encouraged to be overriden in derived classes;

		if a new node is created, its type is by default the same as type(self)
		"""
		if self.__ready_for_next_node:
			# in this case, parse the text as a new node and add as child
			# note by default the type of new node is same as type(self)
			new = type(self)()
			new.start, new.end = pos, pos + len(s)
			new.handler_bare_text(s)
			self.parser_add_child(new)
			return
		else:
			# safe to not use 'elif self.children' here
			# since if self.__ready_for_next_node is False, then there must be
			# at least one node in self.children
			self.children[-1].handler_bare_text(s)
		return

	############################################################################
	# these methods should only be used during parsing
	# derived classes must override these methods (of base class)
	@abc.abstractmethod
	def handler_bare_text(self, s) -> None:
		"""
		handler of parsing bare text as extra node information; in general all
		characters other than the sequence controlling '(', ')' and ',' are bare
		texts; example:
		(foo,bar)baz -> baz are trailing text, after a node group '(...)' is
		closed

		this handler determines how these texts are parsed and stored as node
		information locally; note it is not the same as parser_put_bare_text()
		method, which also finds the correct node to put input bare text, though
		eventually parser_put_bare_text() calls handler_bare_text() internally
		on the node where it finds to put the bare texts;

		unlike parser_put_bare_text() method, handler_bare_text() is encouraged
		to be overridden in derived classes; note that overriding method must
		accept calling signature (self, s), where s is the input text, and any
		return value will be discarded;
		"""
		pass


class NewickTreeBase(object):
	# derived class can override this attribute to use a different node factory
	# type (must inherit NewickTreeNodeBase class)
	node_t = NewickTreeNodeBase

	@property
	def root(self):
		return self.__root

	def __init__(self, *ka, **kw):
		super(NewickTreeBase, self).__init__(*ka, **kw)
		self.__root = None
		return

	def parse(self, s):
		"""
		parse the content of string s (in Newick format) as a tree; the tree
		instance before parsing must be empty;
		"""
		if not isinstance(s, str):
			raise TypeError("s must be str")
		if self.root is not None:
			raise RuntimeError("use parse() on a non-emptry tree is prohibited")
		# create root node
		root = self.__root = self.node_t()
		# parser local variables
		root.start = last_pos = 0 # last_pos is used to slice bare string
		# keep tracking the top node
		# top comes from the old approach using stack; since each node knows its
		# parent node (parent node is unique), then popping the stack is equiv.
		# to traverse upward to the parent;
		top = root
		# parsing
		for pos, c in enumerate(s):
			if c == "(":
				# encounter a group opening '(' means should initialize a new
				# parser and replace 'top' with it
				# OLD: push the stack
				if pos > last_pos:
					junk_start = last_pos
					warnings.warn("junk '%s' discarded at c: %d:%d"\
						% (s[junk_start:pos], junk_start, pos))
				# open a new node
				new_node = self.node_t(start = pos)
				top.parser_add_child(new_node)
				top = new_node
				last_pos = pos + 1
			elif c == ",":
				# this may pass empty string to top.parser_put_bare_text(), and
				# same to all below parser_put_bare_text() calls
				top.parser_put_bare_text(pos, s[last_pos:pos])
				top.parser_add_separator()
				last_pos = pos + 1
			elif c == ")":
				# encounter a group closing ')' means should finalize the top
				# parser and replace 'top' with its parent
				# OLD: pop the stack
				if top is root:
					# should not reach root before the buffer string exhausts
					raise NewickParseError("orphan ')' encountered at c: %d"\
						% pos)
				# finalize the top parser
				top.end = pos + 1
				top.parser_put_bare_text(pos, s[last_pos:pos])
				top = top.parent
				last_pos = pos + 1
		# check if top is root; if not, must have ummatched parenthese
		# OLD: check if stack is clean
		if top is not root:
			raise NewickParseError("expected ')' to close '(' at c: %d"\
				% top.start)
		root.parser_put_bare_text(pos, s[last_pos:])
		root.end = len(s)
		return self

	@classmethod
	def load_string(cls, s, *ka, **kw):
		"""
		load and parse a string as a tree; keyargs/keywords are passed to the
		tree factory/initializer;
		"""
		# create tree
		tree = cls(*ka, **kw)
		tree.parse(s)
		return tree


################################################################################
# example newick tree classes
class NewickTreeLiteNode(NewickTreeNodeBase):
	@property
	def text(self):
		return self._text
	@text.setter
	def text(self, value):
		if not isinstance(value, str):
			raise TypeError("text must be str")
		self._text = value
		return

	def handler_bare_text(self, s):
		self.text = s # type check done in text.setter
		return


class NewickTreeLite(NewickTreeBase):
	node_t = NewickTreeLiteNode


if __name__ == "__main__":
	#import unittest
	#t = NewickTreeLite.load_string("12(aaa,cc(b,3):asd),(),,,")
	pass

#!/usr/bin/env python3

import argparse
import io
import itertools
import matplotlib
import matplotlib.patches
import matplotlib.pyplot
import matplotlib.style
import numpy
import re
import sys


class Char(str):
	def __new__(cls, *ka, **kw):
		new = super(Char, cls).__new__(cls, *ka, **kw)
		if len(new) != 1:
			raise ValueError("Char must be single character")
		return new


class PositiveInt(int):
	def __new__(cls, *ka, **kw):
		new = super(PositiveInt, cls).__new__(cls, *ka, **kw)
		if new <= 0:
			raise ValueError("PositiveInt must be positive")
		return new


# globals
TAX_LIST = [
	"kingdom",
	"phylum",
	"class",
	"order",
	"family",
	"genus",
	"species",
]


def get_args():
	ap = argparse.ArgumentParser()
	ap.add_argument("input", type = str, nargs = "?", default = "-",
		metavar = "count-table",
		help = "OTU count table in mothur output, a.k.a. *.shared file "
			"(default: read from stdin)")
	ap.add_argument("-t", "--tax", "--otu-tax", type = str, required = True,
		metavar = "<tax>",
		help = "OTU taxonomy mothur output, a.k.a. *.tax file (required)")
	# output arguments
	ag = ap.add_argument_group("output")
	ag.add_argument("-O", "--output-prefix", type = str, required = True,
		metavar = "prefix",
		help = "prefix of outputs stdout (required)")
	ag.add_argument("-l", "--level", type = str, default = "genus",
		choices = TAX_LIST,
		help = "taxonomic level to report (default: genus)")
	ag.add_argument("-d", "--delimiter", type = Char, default = "\t",
		metavar = "char",
		help = "delimiter in the output table (default: <tab>)")
	ag.add_argument("-p", "--with-plot", action = "store_true",
		help = "include a plot of the relative abundance table (default: off)")
	ag.add_argument("--plot-taxons", type = PositiveInt, default = 20,
		metavar = "int",
		help = "number of top abundant taxons to draw in the plot "
			"(default: 20); ignored if --with-plot not used")
	ag.add_argument("--plot-title", type = str, default = "", metavar = "str",
		help = "show as title in plot, ignored if --with-plot not used")
	# parse and refine args
	args = ap.parse_args()
	if args.input == "-":
		args.input = sys.stdin
	return args


################################################################################
# misc
################################################################################
def get_fp(file, mode = "r", *ka, factory = open, **kw):
	"""
	file accepts both filename or fp
	"""
	if isinstance(file, str):
		return factory(file, mode, *ka, **kw)
	elif isinstance(file, io.IOBase):
		if file.mode != mode:
			raise ValueError("expected mode %s, got '%s'" % (mode, file.mode))
		return file
	else:
		raise TypeError("file must be str or io.IOBase, not '%s'"\
			% type(file).__name__)
	return


################################################################################
# parse otu table
################################################################################
class OTU(object):
	@property
	def display_name(self):
		return self.otu

	def __init__(self, otu: str, size: int, tax_list: list):
		self.otu	= str(otu)
		self.size	= int(size)
		if not isinstance(tax_list, list):
			raise TypeError("tax must be list, not '%s'"\
				% type(tax_list).__name__)
		self.tax_list	= tax_list
		return

	def get_taxonomy(self, level):
		"""
		return the taxonomy at given level;
		if otu unclassified at given level, return empty string
		level can be either interger (kingdom=0, species=6) or a string;
		"""
		if isinstance(level, int):
			if level < 0:
				raise ValueError("level must be non-negative")
			if level < len(self.tax_list):
				tax = self.tax_list[level]
			else:
				tax = "" # unclassified
		elif isinstance(level, str):
			if level not in TAX_LIST:
				raise ValueError("level as str must be one of: %s, got '%s'"\
					% (str(TAX_LIST), level))
			tax = self.tax_list[TAX_LIST.index(level)]
		else:
			raise TypeError("level must be str or int, not '%s'"\
				% type(level).__name__)
		return tax

	@classmethod
	def from_otu_taxonomy_line(cls, line: str, delimiter = "\t"):
		"""
		parse otu information from single line in mothur output taxonomy file
		"""
		fields = line.split(delimiter)
		if len(fields) < 3:
			raise ValueError("bad format: %s" % str(fields))
		otu, size, tax = fields
		# further parse tax list
		tax_list = re.sub("\(\d+\)", "", tax).split(";") # remove all '(...)'
		return cls(otu, size, tax_list)


class OTUCollection(list):
	@classmethod
	def from_otu_taxonomy_file(cls, file, *, delimiter = "\t", skip_line = 1):
		with get_fp(file, "r") as fp:
			lines = fp.read().splitlines()
		lines = lines[skip_line:] # discard first #skip_line lines
		# read data
		new = cls()
		for line in lines:
			new.append(OTU.from_otu_taxonomy_line(line, delimiter = delimiter))
		return new

	def get_otu_tax_map(self, level):
		return {i.otu: i.get_taxonomy(level) for i in self}


################################################################################
# count table
################################################################################
class CountTableBase(object):
	def __init__(self, row_tags, col_tags, cnt_table, *ka, **kw):
		super(CountTableBase, self).__init__(*ka, **kw)
		self._row_tags	= row_tags
		self._col_tags	= col_tags
		self._cnt_table	= numpy.asarray(cnt_table)
		if self._cnt_table.shape != (len(row_tags), len(col_tags)):
			raise ValueError("row/column tags does not match count table shape")
		return

	@property
	def rela_abunds(self):
		return self._cnt_table / self._cnt_table.sum(axis = 1, keepdims = True)

	def sort_columns(self, method = "average_rank"):
		"""
		sort columns in table based on method;

		METHODS
		-------
		average_rank (default):
			first sort each column in each row, then calculate their average
			rank across all rows; finally sort by their average rank;
		average_value:
			first normalize by row sum, then calculate each column's average
			value across rows; sort by the average value;
		"""
		nrow, ncol = self._cnt_table.shape
		if method == "average_rank":
			rarg	= self._cnt_table.argsort(axis = 1)
			trank	= numpy.zeros(ncol, dtype = int)
			for p in rarg:
				trank[p] += numpy.arange(ncol)
			index	= trank.argsort()
		elif method == "average_value":
			mval	= self.rela_abunds.mean(axis = 0)
			index	= mval.argsort()
		else:
			raise ValueError("unrecognized method '%s'" % method)
		# reverse index, we need descending order
		#index = numpy.flip(index) # numpy<=1.14: filp(x, axis) axis is required
		index = numpy.flip(index, 0)
		self._col_tags = numpy.take(self._col_tags, index).tolist()
		self._cnt_table = self._cnt_table[:, index]
		return self

	def save_as_text(self, file, fmt = "%f", delimiter = "\t"):
		with get_fp(file, "w") as fp:
			# header
			fp.write(delimiter.join([""] + self._col_tags) + "\n")
			for tag, cnt in zip(self._row_tags, self._cnt_table):
				cnt_text = [fmt % i for i in cnt]
				fp.write(delimiter.join([tag] + cnt_text) + "\n")
		return


################################################################################
# otu count table, loaded from mothur output
################################################################################
class OTUCountTable(CountTableBase):
	@property
	def groups(self):
		return self._row_tags
	@property
	def otus(self):
		return self._col_tags
	@property
	def counts(self):
		return self._cnt_table

	def __init__(self, groups, otus, counts, *ka, **kw):
		super(OTUCountTable, self).__init__(groups, otus, counts, *ka, **kw)
		return

	@classmethod
	def from_otu_count_table_file(cls, file, delimiter = "\t"):
		"""
		load count table from mothur output .shared file
		"""
		text	= numpy.loadtxt(file, delimiter = delimiter, dtype = object)
		# parse table
		groups	= text[1:, 1].tolist()
		otus	= text[0, 3:].tolist()
		counts	= text[1:, 3:].astype(int)
		return cls(groups, otus, counts)

	def get_tax_rela_abund_table(self, otu_list: OTUCollection, level):
		"""
		return a TaxonRelaAbundTable, with columns as taxons
		"""
		if not isinstance(otu_list, OTUCollection):
			raise TypeError("otu_list must be OTUCollection, not '%'"\
				% type(otu_list).__name__)
		# prepare otu->tax info
		groups = self.groups # samples
		otu2tax	= otu_list.get_otu_tax_map(level)
		# sorted list of occurred taxons, remove unclassified
		taxons	= sorted(set(otu2tax.values()).difference({""}))
		# tax->column.id map
		tax2id	= {k: i for i, k in enumerate(taxons)}
		# relative abundance of otus
		otu_rela_abund	= self.rela_abunds
		tax_rela_abund	= numpy.zeros((len(groups), len(taxons)), dtype = float)
		# tax rela abundance calc.
		for otu_id, otu in enumerate(self.otus):
			tax = otu2tax[otu]
			if tax: # only if classified
				tax_id = tax2id[tax]
				# tax abund is sum of all associated otu abunds
				tax_rela_abund[:, tax_id] += otu_rela_abund[:, otu_id] # columns
		return TaxonRelaAbundTable(groups, taxons, tax_rela_abund)


################################################################################
# taxonomy analysis
################################################################################
class TaxonRelaAbundTable(CountTableBase):
	@property
	def groups(self):
		return self._row_tags
	@property
	def taxons(self):
		return self._col_tags
	@property
	def abunds(self):
		return self._cnt_table

	def __init__(self, groups, taxons, abunds, *ka, **kw):
		super(TaxonRelaAbundTable, self).__init__(groups, taxons, abunds,
			*ka, **kw)
		return


################################################################################
# plot
################################################################################
def setup_layout(figure, nrow, ncol):
	layout = dict(figure = figure)

	# margins
	left_margin_inch	= 3.0
	right_margin_inch	= 0.5
	top_margin_inch		= 0.6
	bottom_margin_inch	= 1.6

	# heatmap dims
	cell_width_inch		= 0.4
	cell_height_inch	= 0.2
	heatmap_width_inch	= cell_width_inch * ncol
	heatmap_height_inch	= cell_height_inch * nrow

	# figure size
	figure_width_inch	= left_margin_inch + heatmap_width_inch\
		+ right_margin_inch
	figure_height_inch	= bottom_margin_inch + heatmap_height_inch\
		+ top_margin_inch
	figure.set_size_inches(figure_width_inch, figure_height_inch)

	# heatmap axes
	heatmap_left	= left_margin_inch / figure_width_inch
	heatmap_bottom	= bottom_margin_inch / figure_height_inch
	heatmap_width	= heatmap_width_inch / figure_width_inch
	heatmap_height	= heatmap_height_inch / figure_height_inch
	heatmap_axes	= figure.add_axes([heatmap_left, heatmap_bottom,
		heatmap_width, heatmap_height])
	layout["heatmap"] = heatmap_axes

	# style axes
	for sp in heatmap_axes.spines.values():
		sp.set_visible(False)
	heatmap_axes.tick_params(
		left = False, labelleft = True,
		right = False, labelright = False,
		top = False, labeltop = False,
		bottom = False, labelbottom = True)

	# colorbar
	colorbar_width_inch		= 0.75 * left_margin_inch
	colorbar_height_inch	= 0.20 * bottom_margin_inch
	colorbar_width	= colorbar_width_inch / figure_width_inch
	colorbar_height	= colorbar_height_inch / figure_height_inch
	colorbar_left	= (left_margin_inch / figure_width_inch\
		- colorbar_width) / 2
	colorbar_bottom	= (bottom_margin_inch / figure_height_inch\
		- colorbar_height) / 2
	colorbar_axes = figure.add_axes([colorbar_left, colorbar_bottom,
		colorbar_width, colorbar_height])
	layout["colorbar"] = colorbar_axes

	return layout


def plot(png, tax_abund: TaxonRelaAbundTable, use_num_taxons, title = ""):
	if not isinstance(tax_abund, TaxonRelaAbundTable):
		raise TypeError("tax_abund must be TaxonRelaAbundTable, not '%s'"\
			% type(tax_abund).__name__)
	# gather info
	groups = tax_abund.groups
	taxons = tax_abund.taxons
	abunds = tax_abund.abunds.T # need transpose as rows not are taxons
	nrow, ncol = abunds.shape
	# futher process taxons; if too many taxons, combine everthing too low rank
	if use_num_taxons < nrow:
		nrow		= use_num_taxons + 1
		plot_taxons	= taxons[:use_num_taxons] + ["all others"]
		plot_abunds = numpy.vstack([abunds[:use_num_taxons],
			abunds[use_num_taxons:].sum(axis = 0, keepdims = True)])
	else:
		plot_taxons = taxons
		plot_abunds = abunds

	# layout
	figure = matplotlib.pyplot.figure()
	layout = setup_layout(figure, nrow, ncol)

	# plot table heatmap
	axes = layout["heatmap"]
	cmap = matplotlib.pyplot.get_cmap("Spectral_r")
	heatmap = axes.pcolor(plot_abunds, cmap = cmap, vmin = 0, vmax = 1)
	# add text on heatmap
	for r, c in itertools.product(range(nrow), range(ncol)):
		val = plot_abunds[r, c]
		text = ("" if val == 0 else "%.2f" % val)
		color = ("#000000" if (val <= 0.7) and (val >= 0.2) else "#FFFFFF")
		axes.text(x = c + 0.5, y = r + 0.5, s = text, fontsize = 8,
			color = color,
			horizontalalignment = "center", verticalalignment = "center")
	# add lines
	grid_props = dict(linestyle = "-", linewidth = 0.5, color = "#FFFFFF",
		clip_on = False)
	for i in numpy.arange(nrow + 1):
		axes.axhline(i, **grid_props)
	for i in numpy.arange(ncol + 1):
		axes.axvline(i, **grid_props)
	# misc
	xticks = numpy.arange(ncol) + 0.5
	axes.set_xticks(xticks)
	axes.set_xticklabels(groups, family = "sans-serif",
		rotation = 90, fontsize = 12, fontweight = "medium",
		horizontalalignment = "center", verticalalignment = "top")
	axes.set_xlim(0, ncol)
	yticks = numpy.arange(nrow) + 0.5
	axes.set_yticks(yticks)
	axes.set_yticklabels(plot_taxons,
		fontsize = 10,
		horizontalalignment = "right", verticalalignment = "center")
	axes.set_ylim(nrow, 0)

	# colorbar
	axes = layout["colorbar"]
	colorbar = figure.colorbar(heatmap, cax = axes, orientation = "horizontal")
	colorbar.set_label("Abundance (%)")
	colorbar.outline.set_visible(False)

	# title
	figure.suptitle(title, fontsize = 18, fontweight = "medium",
		horizontalalignment = "center", verticalalignment = "top")
	# save
	matplotlib.pyplot.savefig(png, dpi = 300)
	matplotlib.pyplot.close()
	return


def main():
	args = get_args()
	# load data
	otu_list	= OTUCollection.from_otu_taxonomy_file(args.tax)
	cnt_table	= OTUCountTable.from_otu_count_table_file(args.input)
	tax_abund	= cnt_table.get_tax_rela_abund_table(otu_list, args.level)
	tax_abund.sort_columns("average_value")
	# save table
	tax_abund.save_as_text(args.output_prefix + ".tsv", "%.4f", args.delimiter)
	if args.with_plot:
		plot(args.output_prefix + ".png", tax_abund, args.plot_taxons,
			title = args.plot_title)
	return


if __name__ == "__main__":
	main()

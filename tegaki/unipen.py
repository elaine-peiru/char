#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 The Tegaki project contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Contributors to this file:
# - Mathieu Blondel
# - Paul Adrian Titei titei.pa@gmail.com

# Incomplete unipen format parser
# See http://hwr.nici.kun.nl/unipen/unipen.def for the format specification

import re
import os

from tegaki.character import Point, Stroke, Writing, Character
from tegaki.charcol import CharacterCollection


class UnipenSegmentDelineationRange(object):
	"""
		See unipen segment delineation format definition
		This class defines only one range from a complete delineation.
		[A[:M]]-[B[:N]] becomes:
		A, B -> start_comp, end_comp (+1)
		M, N -> start_point, end_point (+1)
	"""

	def __init__(self, delimit_range):
		"""
			subdelimit - a [A[:M]]-[B[:N]] formated string
			[A[:M]]-[B[:N]]
			More flexible representation to
			delineate segments of data
			by breaking components. A and B are
			component numbers, M and N are point
			numbers in the component.
		"""
		self.start_point = 0  # default to first point in component
		self.end_point = -1  # defaults to last point in component

		if delimit_range.find('-') == -1:
			self.start_comp = int(delimit_range)
			self.end_comp = int(delimit_range) + 1
			return

		start_colon_pair, end_colon_pair = delimit_range.split('-')

		self.start_comp = int(start_colon_pair.split(':')[0])
		if start_colon_pair.find(':') != -1:
			self.start_point = int(start_colon_pair.split(':')[1])
		# print self.start_point

		self.end_comp = int(end_colon_pair.split(':')[0]) + 1
		if end_colon_pair.find(':') != -1:
			self.end_point = int(end_colon_pair.split(':')[1]) + 1
		# print self.end_point

	def __str__(self):
		return str(self.start_comp) + ':' + str(self.start_point) + '-' + str(self.end_comp) + ':' + str(self.end_point)


class UnipenEventParser(object):
	"""SAX-like event-based parser"""

	KEYWORD_LINE_REGEXP = re.compile(r"^\.[A-Z]+")

	def __init__(self):
		self._parsed_file = None
		self._nested_includes = 0  # current depth of nested includes
		self._include_file = None  # name of include file we are currently parsing
		self._include_dir = None

	def parse_file(self, path, include_dir):
		self._parsed_file = path
		self._include_dir = include_dir
		f = open(path)

		keyword, args = None, None
		for line in f.readlines():
			if self._is_keyword_line(line):
				if keyword is not None and args is not None:
					self._handle_keyword(keyword.strip(), args.strip())
					keyword, args = None, None

				arr = line.split(" ", 1)

				keyword = arr[0][1:]
				if len(arr) == 1:
					args = ""
				else:
					args = arr[1]

			elif keyword is not None and args is not None:
				args += line

		if keyword is not None and args is not None:
			self._handle_keyword(keyword, args)

		f.close()

		self._handle_eof()

		self._parsed_file = None

	def _handle_keyword(self, keyword, args):
		# default keyword handler
		if keyword == "INCLUDE":
			if not self._parsed_file: return

			include_name = args.upper()
			include = os.path.join(self._include_dir[-1], include_name)

			print "INCLUDE ", include_name

			if os.path.exists(include):
				parser = UnipenProxyParser(self._handle_keyword)
				parser.parse_file(include, None)
			else:
				print include, " does not exist"


	def _handle_eof(self):
		# default end-of-file handler
		# print "end of file"
		pass

	def _is_keyword_line(self, line):
		return self.KEYWORD_LINE_REGEXP.match(line) is not None


class UnipenProxyParser(UnipenEventParser):
	def __init__(self, redirect):
		UnipenEventParser.__init__(self)
		self._redirect = redirect

	def _handle_keyword(self, keyword, args):
		self._redirect(keyword, args)

	def _handle_eof(self):
		pass


class UnipenParser(UnipenEventParser):
	"""
	"""

	def __init__(self):
		UnipenEventParser.__init__(self)
		self._strokes = []  # aka components: .PEN_DOWN .PEN_UP
		self._strokes_type = []  # addition info for _strokes; origin: : "PEN_DOWN" or "PEN_UP".
		self._delineations = []  # .SEGMENT
		self._labels = []  # .SEGMENT
		self.width = None  # .X_DIM
		self.height = None  # .Y_DIM


	def _add_character_writing(self):
		if self._writing:
			character = Character()
			character.set_writing(self._writing)
			self._characters.append(character)


	def _handle_SEGMENT(self, args):
		seg_type, delimit, quality, label = args.split()
		if seg_type == "CHARACTER":
			delineation = []
			for delimit_range in delimit.split(','):
				delineation.append(UnipenSegmentDelineationRange(delimit_range.strip()))
			self._delineations.append(delineation)
			label = label.strip()[1:-1]
			self._labels.append(label)

	def _handle_X_DIM(self, args):
		self.width = int(args.strip())

	def _handle_Y_DIM(self, args):
		self.height = int(args.strip())

	def _handle_eof(self):
		pass

	def _handle_PEN_DOWN(self, args):
		"""
			Handles a list of x y coords
			FIXME: handle coords as defined by .COORD
		"""
		points = [[int(word) for word in line.split()]
		          for line in args.strip().split("\n") if line]
		stroke = Stroke()
		for point_tuple in points:
			x = point_tuple[0]
			y = point_tuple[1]
			stroke.append_point(Point(x, y))
		if len(stroke) > 0:
			self._strokes.append(stroke)
			self._strokes_type.append('PEN_DOWN')

	def _handle_PEN_UP(self, args):
		points = [[int(word) for word in line.split()]
		          for line in args.strip().split("\n") if line]
		stroke = Stroke()
		for x, y in points:
			stroke.append_point(Point(x, y))
		if len(stroke) > 0:
			self._strokes.append(stroke)
			self._strokes_type.append('PEN_UP')

	def _handle_INCLUDE(self, args):
		"""
			args: TEXT
		"""
		if not self._parsed_file: return

		include_name = args
		include = os.path.join(self._include_dir, include_name)
		if not os.path.exists(include):
			current_dir = os.path.split(self._include_file)[0]
			include = os.path.join(current_dir, include_name)

		if os.path.exists(include):
			print "include ", include
			self._nested_includes += 1
			self._include_file = include

			parser = UnipenProxyParser(self._handle_keyword)
			parser.parse_file(include, None)

			self._nested_includes -= 1
			if self._nested_includes == 0:
				self._include_file = None
		else:
			print include, " does not exist"


	def _handle_keyword(self, keyword, args):
		try:
			func = getattr(self, "_handle_" + keyword)
		except AttributeError:
			pass
		else:
			func(args)

	def get_character_collection(self):
		charcol = CharacterCollection()

		# group characters with the same label into sets
		sets = {}
		for i in range(len(self._labels)):
			# Create Character
			writing = Writing()
			if self.height and self.width:
				writing.set_height(self.height)
				writing.set_width(self.width)

			for delin_range in self._delineations[i]:
				if delin_range.start_comp == (delin_range.end_comp - 1):
					stroke_points = self._strokes[delin_range.start_comp][delin_range.start_point:delin_range.end_point]
					writing.append_stroke(Stroke.from_list(stroke_points))
				else:
					# add first stroke to writing
					start_stroke_points = self._strokes[delin_range.start_comp][delin_range.start_point:-1]
					if len(start_stroke_points) > 0:
						writing.append_stroke(Stroke.from_list(start_stroke_points))

					# add last stroke to writing
					end_stroke_points = self._strokes[delin_range.end_comp - 1][0:delin_range.end_point]
					if len(end_stroke_points) > 0:
						writing.append_stroke(Stroke.from_list(end_stroke_points))

					# add the remaining strokes to writing
					for stroke in self._strokes[delin_range.start_comp + 1:delin_range.end_comp - 1]:
						writing.append_stroke(stroke)

			character = Character()
			character.set_writing(writing)

			utf8 = self._labels[i]
			character.set_utf8(utf8)

			sets[utf8] = sets.get(utf8, []) + [character]

		charcol.add_sets(sets.keys())

		for set_name, characters in sets.items():
			charcol.append_characters(set_name, characters)

		return charcol

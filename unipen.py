__author__ = 'Paul Adrian Titei'

import re
import os


class DefaultUnipenParser:
	"""Abstract unipen format file parser"""

	KEYWORD_LINE_REGEXP = re.compile(r"^\.[A-Z]+")

	def __init__(self):
		self._parsed_file = None

	def parse_file(self, path):
		self._parsed_file = path
		f = open(path)

		keyword, args = None, None
		for line in f.readlines():
			if self._is_keyword_line(line):
				if keyword is not None and args is not None:
					self.handle_keyword(keyword.strip(), args.strip())
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
			self.handle_keyword(keyword, args)

		f.close()

		self.handle_eof()

		self._parsed_file = None

	def handle_keyword(self, keyword, args):
		# default keyword handler
		print keyword, args

	def handle_eof(self):
		# default end-of-file handler
		print "end of file"

	def _is_keyword_line(self, line):
		return self.KEYWORD_LINE_REGEXP.match(line) is not None


class UnipenParser(DefaultUnipenParser):
	""""""

	def __init__(self):
		super(UnipenParser, self).__init__()
		self._labels = []
		self._characters = []
		self._char = None

	def _handle_SEGMENT(self, args):
		seg_type, delimit, quality, label = args.split(" ")
		if seg_type == "CHARACTER":
			label = label.strip()[1:-1]
			self._labels.append(label)

	def _handle_START_BOX(self, args):
		if self._char:
			self._characters.append(self._char)
		self._char = Character()

	def _handle_PEN_DOWN(self, args):
		writing = self._char.get_writing()
		points = [[int(p_) for p_ in p.split(" ")] \
		          for p in args.strip().split("\n")]
		stroke = Stroke()
		for x, y in points:
			stroke.append_point(Point(x, y))
		writing.append_stroke(stroke)

	def _handle_INCLUDE(self, args):
		if not self._parsed_file: return

		include_filename = args.upper()
		currdir = os.path.dirname(os.path.abspath(self._parsed_file))

		# FIXME: don't hardcode include paths
		include1 = os.path.join(currdir, "INCLUDE")
		include2 = os.path.join(currdir, "..", "INCLUDE")

		for include in (include1, include2, currdir):
			path = os.path.join(include, include_filename)
			if os.path.exists(path):
				parser = UnipenProxyParser(self.handle_keyword)
				parser.parse_file(path)
				break

	def handle_keyword(self, keyword, args):
		try:
			func = getattr(self, "_handle_" + keyword)
		except AttributeError:
			pass
		else:
			func(args)

	def get_character_collection(self):
		charcol = CharacterCollection()
		assert (len(self._labels) == len(self._characters))

		# group characters with the same label into sets
		sets = {}
		for i in range(len(self._characters)):
			utf8 = self._labels[i]
			self._characters[i].set_utf8(utf8)
			sets[utf8] = sets.get(utf8, []) + [self._characters[i]]

		charcol.add_sets(sets.keys())

		for set_name, characters in sets.items():
			charcol.append_characters(set_name, characters)

		return charcol



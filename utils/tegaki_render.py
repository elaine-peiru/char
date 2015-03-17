# -*- coding: utf-8 -*-

# Copyright (C) Paul Adrian Titei
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
# - Paul Adrian Titei

from PyQt4.QtGui import *
from PyQt4.QtCore import *


class WritingRender(object):
	"""
		A utility class for converting tegaki.Writing objects to images.
	"""

	def __init__(self, writing):
		self._writing = writing
		self.pixmap = QPixmap(writing.get_width(), writing.get_height())
		self.pixmap.fill()
		self._painter = QPainter(self.pixmap)
		self._pen = QPen(Qt.black, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
		self._pen2 = QPen(Qt.darkRed, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
		self._painter.setPen(self._pen)

		# self._drawWriting()

	def _drawWriting(self):
		for stroke in self._writing.get_strokes():
			# TODO: give unique color to each stroke
			qpoints = [QPoint(p[0], self._writing.get_height() - p[1]) for p in stroke]
			if len(qpoints) <= 1:
				print 'lone wanderer'
			# self._painter.setPen(self._pen)
			# self._painter.drawPolyline(*qpoints)
			# self._painter.setPen(self._pen2)
			self._painter.drawPoints(*qpoints)

	def save(self, file):
		self.pixmap.save(file, 'PNG')
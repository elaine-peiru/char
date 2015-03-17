#!/usr/bin/env python


#############################################################################
##
## Copyright (C) 2010 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################


import os

from PyQt4 import QtCore, QtGui
import matplotlib.pyplot as plt
import numpy as np

from recognition.feature_extractor import FeatureExtractor
from tegaki.charcol import CharacterCollection
from tegaki.character import *
from tools.tegaki_render import WritingRender


class ImageViewer(QtGui.QMainWindow):
	def __init__(self):
		super(ImageViewer, self).__init__()

		self.printer = QtGui.QPrinter()
		self.scaleFactor = 0.0

		self.imageLabel = QtGui.QLabel()
		self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
		self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored,
		                              QtGui.QSizePolicy.Ignored)
		self.imageLabel.setScaledContents(True)

		self.scrollArea = QtGui.QScrollArea()
		self.scrollArea.setBackgroundRole(QtGui.QPalette.Dark)
		self.scrollArea.setWidget(self.imageLabel)
		self.setCentralWidget(self.scrollArea)

		self.labelLabel = QtGui.QLabel()
		labelDock = QtGui.QDockWidget()
		labelDock.setWidget(self.labelLabel)
		self.addDockWidget(QtCore.Qt.TopDockWidgetArea, labelDock)

		self.createActions()
		self.createMenus()

		self.setWindowTitle("Image Viewer")
		self.resize(500, 400)

		self.char_gen = None  # used for self.random
		self.utf8 = None
		self.writing = None  # writing(unmodified) of currently displayed character
		self.norm_writing = None  # writing(normalized) of currently displayed character
		self.activeWriting = None  # "unmodified" or "normalized"
		self.extractor = FeatureExtractor(arc_len = 20)
		char = Character()
		char.read("test_char.xml")
		self.display_char(char)


	def open(self):
		fileName = QtGui.QFileDialog.getOpenFileName(self, "Open File",
		                                             QtCore.QDir.currentPath())
		if fileName:
			image = QtGui.QImage(fileName)
			if image.isNull():
				QtGui.QMessageBox.information(self, "Image Viewer",
				                              "Cannot load %s." % fileName)
				return

			self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(image))
			self.scaleFactor = 1.0

			self.printAct.setEnabled(True)
			self.fitToWindowAct.setEnabled(True)
			self.updateActions()

			if not self.fitToWindowAct.isChecked():
				self.imageLabel.adjustSize()

	def plotWriting(self):
		for pen_up, stroke in self.pen_up_strokes:
			points = self.extractor.unique_points(stroke.get_coordinates())

			xs, ys = zip(*points)
			xs, ys = np.array(xs), np.array(ys)

			plt.plot(xs, ys, 'bo')

		for stroke in self.norm_writing.get_strokes(full = True):
			points = self.extractor.unique_points(stroke.get_coordinates())
			xs, ys = zip(*points)
			xs, ys = np.array(xs), np.array(ys)

			plt.plot(xs, ys, 'ro')
		plt.show()

	def display_char(self, char):
		self.utf8 = char.get_utf8()
		self.writing = char.get_writing()
		self.writing.crop_to_mbr()
		self.norm_writing = self.writing.copy()
		self.activeWriting = "normalized"

		self.norm_writing.fit_to_box(300, 300)
		self.norm_writing.normalize_position()
		self.norm_writing.smooth()

		# annotated_points = self.extractor.connect_stroke_endpoints(self.extractor.resample_strokes(self.norm_writing.get_strokes(full=True)))
		# wr = Writing()
		# for xs, ys in strokes:
		# 	s = Stroke()
		# 	for x, y in zip(xs, ys):
		# 		s.append_point(Point(x, y))
		# 	wr.append_stroke(s)
		#
		# wr.crop_to_mbr()
		# self.norm_writing = wr

		# strokes = self.norm_writing.get_strokes(full = True)
		# self.pen_up_strokes = self.extractor.connect_stroke_endpoints(strokes)

		self.displayWriting(self.norm_writing, self.utf8)
		# self.plotWriting()

	def random(self):
		if self.char_gen is None:
			QtGui.QMessageBox.information(self, 'Request failed', 'No database set.')
			return
		rand_char = next(self.char_gen)
		self.display_char(rand_char)


	def displayWriting(self, writing, utf8):
		char_drawer = WritingRender(writing)

		self.labelLabel.setText(utf8)

		self.imageLabel.setPixmap(char_drawer.pixmap)
		self.scaleFactor = 1.0

		self.printAct.setEnabled(True)
		self.fitToWindowAct.setEnabled(True)
		self.updateActions()

		if not self.fitToWindowAct.isChecked():
			self.imageLabel.adjustSize()

	def switchWriting(self):
		print self.activeWriting
		if self.writing is None or self.norm_writing is None:
			QtGui.QMessageBox.information(self, 'Request failed', 'Writing is None.')
			return
		if self.activeWriting == "normalized":
			self.activeWriting = "unmodified"
			self.displayWriting(self.writing, self.utf8)
		elif self.activeWriting == "unmodified":
			self.activeWriting = "normalized"
			self.displayWriting(self.norm_writing, self.utf8)

	def saveImg(self):
		fName = QtGui.QFileDialog.getSaveFileName(self, "Save writing as PNG file", "Save writing as new file", self.tr("Text Files (*.png)"))
		if fName.isEmpty() == False:
			char_drawer = WritingRender(self.norm_writing)
			annotated_points = self.extractor.connect_stroke_endpoints(self.extractor.resample_strokes(self.norm_writing.get_strokes(full=True)))
			for pen_down, x, y in annotated_points:
				if pen_down:
					char_drawer._painter.setPen(char_drawer._pen)
				else:
					char_drawer._painter.setPen(char_drawer._pen2)
				qp = QtCore.QPoint(x, self.norm_writing.get_height() - y)
				char_drawer._painter.drawPoint(qp)
			char_drawer.save(fName)

	def print_(self):
		dialog = QtGui.QPrintDialog(self.printer, self)
		if dialog.exec_():
			painter = QtGui.QPainter(self.printer)
			rect = painter.viewport()
			size = self.imageLabel.pixmap().size()
			size.scale(rect.size(), QtCore.Qt.KeepAspectRatio)
			painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
			painter.setWindow(self.imageLabel.pixmap().rect())
			painter.drawPixmap(0, 0, self.imageLabel.pixmap())


	def zoomIn(self):
		self.scaleImage(1.25)


	def zoomOut(self):
		self.scaleImage(0.8)


	def normalSize(self):
		self.imageLabel.adjustSize()
		self.scaleFactor = 1.0


	def fitToWindow(self):
		fitToWindow = self.fitToWindowAct.isChecked()
		self.scrollArea.setWidgetResizable(fitToWindow)
		if not fitToWindow:
			self.normalSize()

		self.updateActions()


	def about(self):
		QtGui.QMessageBox.about(self, "About Image Viewer",
		                        "<p>The <b>Image Viewer</b> example shows how to combine "
		                        "QLabel and QScrollArea to display an image. QLabel is "
		                        "typically used for displaying text, but it can also display "
		                        "an image. QScrollArea provides a scrolling view around "
		                        "another widget. If the child widget exceeds the size of the "
		                        "frame, QScrollArea automatically provides scroll bars.</p>"
		                        "<p>The example demonstrates how QLabel's ability to scale "
		                        "its contents (QLabel.scaledContents), and QScrollArea's "
		                        "ability to automatically resize its contents "
		                        "(QScrollArea.widgetResizable), can be used to implement "
		                        "zooming and scaling features.</p>"
		                        "<p>In addition the example shows how to use QPainter to "
		                        "print an image.</p>")


	def createActions(self):
		self.openAct = QtGui.QAction("&Open...", self, shortcut="Ctrl+O",
		                             triggered=self.open)

		self.randomAct = QtGui.QAction("&Random...", self, shortcut="Ctrl+R",
		                               triggered=self.random)

		self.switchWritingAct = QtGui.QAction("&Switch Writing...", self, shortcut="Ctrl+S",
		                                      triggered=self.switchWriting)

		self.openDbAct = QtGui.QAction("Open &Database...", self, shortcut="Ctrl+D",
		                               triggered=self.changeDatabase)

		self.printAct = QtGui.QAction("&Print...", self, shortcut="Ctrl+P",
		                              enabled=False, triggered=self.print_)

		self.saveAct = QtGui.QAction("&Save...", self,
		                              enabled=False, triggered=self.saveImg)

		self.exitAct = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q",
		                             triggered=self.close)

		self.zoomInAct = QtGui.QAction("Zoom &In (25%)", self,
		                               shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)

		self.zoomOutAct = QtGui.QAction("Zoom &Out (25%)", self,
		                                shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)

		self.normalSizeAct = QtGui.QAction("&Normal Size", self,
		                                   shortcut="Ctrl+N", enabled=False, triggered=self.normalSize)

		self.fitToWindowAct = QtGui.QAction("&Fit to Window", self,
		                                    enabled=False, checkable=True, shortcut="Ctrl+F",
		                                    triggered=self.fitToWindow)

		self.aboutAct = QtGui.QAction("&About", self, triggered=self.about)

		self.aboutQtAct = QtGui.QAction("About &Qt", self,
		                                triggered=QtGui.qApp.aboutQt)


	def createMenus(self):
		self.fileMenu = QtGui.QMenu("&File", self)
		self.fileMenu.addAction(self.openAct)
		self.fileMenu.addAction(self.randomAct)
		self.fileMenu.addAction(self.switchWritingAct)
		self.fileMenu.addAction(self.openDbAct)
		self.fileMenu.addAction(self.printAct)
		self.fileMenu.addAction(self.saveAct)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exitAct)

		self.viewMenu = QtGui.QMenu("&View", self)
		self.viewMenu.addAction(self.zoomInAct)
		self.viewMenu.addAction(self.zoomOutAct)
		self.viewMenu.addAction(self.normalSizeAct)
		self.viewMenu.addSeparator()
		self.viewMenu.addAction(self.fitToWindowAct)

		self.helpMenu = QtGui.QMenu("&Help", self)
		self.helpMenu.addAction(self.aboutAct)
		self.helpMenu.addAction(self.aboutQtAct)

		self.menuBar().addMenu(self.fileMenu)
		self.menuBar().addMenu(self.viewMenu)
		self.menuBar().addMenu(self.helpMenu)


	def updateActions(self):
		self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
		self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
		self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())
		self.saveAct.setEnabled(True)

	def scaleImage(self, factor):
		self.scaleFactor *= factor
		self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

		self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
		self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

		self.zoomInAct.setEnabled(self.scaleFactor < 4.0)
		self.zoomOutAct.setEnabled(self.scaleFactor > 0.25)


	def adjustScrollBar(self, scrollBar, factor):
		scrollBar.setValue(int(factor * scrollBar.value()
		                       + ((factor - 1) * scrollBar.pageStep() / 2)))

	def changeDatabase(self):
		db_file = QtGui.QFileDialog.getOpenFileName(self, "Open database",
		                                            QtCore.QDir.currentPath())
		db_file = str(db_file)
		if db_file and os.path.splitext(db_file)[1] == '.chardb':
			charcol = CharacterCollection(db_file);
			print "chars in db:", charcol.get_total_n_characters()
			self.char_gen = charcol.get_random_characters_gen(charcol.get_total_n_characters())
			self.random()
		else:
			self.char_gen = None


if __name__ == '__main__':
	import sys

	app = QtGui.QApplication(sys.argv)
	imageViewer = ImageViewer()
	imageViewer.show()
	sys.exit(app.exec_())
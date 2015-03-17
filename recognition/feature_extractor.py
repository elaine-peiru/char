import math
from collections import deque

import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

from tegaki.character import *


class FeatureExtractor():
	def __init__(self, arc_len=30, curve_length_num=500, vecinity_reach=3):
		self.arc_len = arc_len
		self.curve_length_num = curve_length_num
		self.vecinity_reach = vecinity_reach
		self.feature_order = ['pen_down', 'x', 'y',
		                      'wr_cos', 'wr_sin',
		                      'curv_cos', 'curv_sin',
		                      'v_aspect', 'v_slope_cos', 'v_slope_sin',
		                      'v_curliness', 'v_liniarity']
		self.active_features = {}
		for feature_name in self.feature_order:
			self.active_features[feature_name] = True

	def set3f(self):
		"""
		Activate only the 3 basic features: pen_down, x and y.
		"""
		basic_features = ['pen_down', 'x', 'y']
		for feature_name in self.feature_order:
			if feature_name in basic_features:
				self.active_features[feature_name] = True
			else:
				self.active_features[feature_name] = False

	def set7f(self):
		"""
		Activate all features except the vecinity ones.
		"""
		features = ['pen_down', 'x', 'y',
		            'wr_cos', 'wr_sin',
                    'curv_cos', 'curv_sin']
		for feature_name in self.feature_order:
			if feature_name in features:
				self.active_features[feature_name] = True
			else:
				self.active_features[feature_name] = False

	def curve_length(self, x, y):
		"""
		Length of the curve determined by the points.
		TODO: there might be a better algorithm for computing this...

		@type x, y: np.array of ints
		"""
		if len(x) > 3:
			tck, u = interpolate.splprep([x, y], s=0.0)
			x_i, y_i = interpolate.splev(np.linspace(0, 1, self.curve_length_num), tck)
			x, y = x_i, y_i
		length = 0
		for i in range(len(x) - 1):
			length += math.sqrt((x[i] - x[i + 1]) ** 2 + (y[i] - y[i + 1]) ** 2)

		return int(length)

	def resample_points(self, x, y):
		"""
		Resample the points at equal arc length.

		@type x, y: np.array of ints
		"""
		num = int(self.curve_length(x, y) / self.arc_len)
		if len(x) > 3:
			tck, u = interpolate.splprep([x, y], s=0.0)
			x_i, y_i = interpolate.splev(np.linspace(0, 1, num), tck)
			x, y = x_i, y_i
		elif len(x) == 3:
			xs = np.linspace(x[0], x[1], num + 2, endpoint=True).tolist()
			ys = np.linspace(y[0], y[1], num + 2, endpoint=True).tolist()
			xs.extend(np.linspace(x[1], x[2], num + 2, endpoint=True).tolist()[1:])
			ys.extend(np.linspace(y[1], y[2], num + 2, endpoint=True).tolist()[1:])
			x, y = np.array(xs), np.array(ys)
		elif len(x) == 2:
			xs = np.linspace(x[0], x[1], num + 2, endpoint=True)
			ys = np.linspace(y[0], y[1], num + 2, endpoint=True)
			x, y = xs, ys

		return x, y

	def resample_strokes(self, strokes):
		"""
		Resample each stroke.

		@type strokes: L{tegaki.Stroke}
		@rtype: list of (xs, ys) for each stroke
		"""
		strokes_coords = []
		for stroke in strokes:
			# remove duplicate points in stroke
			p_set = set()  # set of points
			p_uniq = []
			for point in stroke:
				point = point.get_coordinates()
				if point not in p_set:
					p_set.add(point)
					p_uniq.append(point)

			xs, ys = map(np.array, zip(*p_uniq))
			xs, ys = self.resample_points(xs, ys)
			strokes_coords.append((xs.tolist(), ys.tolist()))

		return strokes_coords


	def connect_stroke_endpoints(self, strokes_coords):
		"""
		Connects the endpoints of strokes with a continuous line.
		The lines are split in equal segments(of arc_length) and put
		inbetween the original strokes.

		@rtype: list of annotated points (pen_down, x, y).
		pen_down = 1 if point is from original stroke
		           0 if added.
		"""
		connected_strokes = []
		for i in range(len(strokes_coords) - 1):
			xs_cur, ys_cur = strokes_coords[i]
			xs_next, ys_next = strokes_coords[i + 1]
			x1, y1 = xs_cur[-1], ys_cur[-1]  # end of current stroke
			x2, y2 = xs_next[0], ys_next[0]  # start of next stroke

			# interpolate points between endpoints
			d = math.sqrt(float((x1 - x2) ** 2 + (y1 - y2) ** 2))
			num = int(d / self.arc_len)  # number of added points
			added_xs = np.linspace(x1, x2, num + 1, endpoint=False)[1:].tolist()
			added_ys = np.linspace(y1, y2, num + 1, endpoint=False)[1:].tolist()

			# add current stroke
			ones = [1 for _ in range(len(xs_cur))]
			connected_strokes.extend(zip(ones, xs_cur, ys_cur))

			#add interp points
			if len(added_xs) > 0:
				zeros = [0 for _ in range(len(added_xs))]
				connected_strokes.extend(zip(zeros, added_xs, added_ys))

		# add last stroke
		xs_last, ys_last = strokes_coords[-1]
		ones = [1 for _ in range(len(xs_last))]
		connected_strokes.extend(zip(ones, xs_last, ys_last))

		return connected_strokes

	@staticmethod
	def writing_direction(x1, y1, x2, y2):
		"""
		Compute the writing direction.
		return cos and sin of angle between the line
		determined by the given points and the 0x line.
		"""
		if x2 is None or y2 is None:
			# assume angle is 0
			return 1.0, 0.0
		dx = abs(x2 - x1)
		dy = abs(y2 - y1)
		d = math.sqrt(float(dx ** 2 + dy ** 2))
		if d != 0:
			cos_wr = float(dx) / d
			sin_wr = float(dy) / d
		else:
			cos_wr, sin_wr = 0, 0
		return cos_wr, sin_wr

	@staticmethod
	def curvature(x_a, y_a, x_b, y_b, x_c, y_c):
		"""
			Return sin and cos of the curvature(angle)
			between the 3 points with a being the vertex.
		"""
		if x_b is None or y_b is None or y_c is None or x_c is None:
			# assume angle 0
			return 1.0, 0.0
		dx_ab = abs(x_a - x_b)
		dy_ab = abs(y_a - y_b)
		dx_ac = abs(x_a - x_c)
		dy_ac = abs(y_a - y_c)
		dx_bc = abs(x_b - x_c)
		dy_bc = abs(y_b - y_c)
		d_ab = math.sqrt(float(dx_ab ** 2 + dy_ab ** 2))
		d_ac = math.sqrt(float(dx_ac ** 2 + dy_ac ** 2))
		d_bc = math.sqrt(float(dx_bc ** 2 + dy_bc ** 2))

		if d_ab != 0 and d_ac != 0:
			cos_curv = (d_ab ** 2 + d_ac ** 2 - d_bc ** 2) / float((2 * d_ab * d_ac))
		else:
			cos_curv = 1.0
		try:
			ang = math.acos(cos_curv)
		except ValueError:
			ang = math.pi
			cos_curv = 1.0
		sin_curv = math.sin(ang)
		return cos_curv, sin_curv

	@staticmethod
	def dist_point_to_line(x0, y0, x1, y1, x2, y2):
		"""
		Compute distance from (x0, y0) to line
		determined by points (x1, y1) and (x2, y2)
		"""
		d = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
		if d != 0:
			return abs((x2 - x1) * (y1 - y0) - (x1 - x0) * (y2 - y1)) / d
		return 0


	@staticmethod
	def vecinity_features(v):
		"""
		Compute features of the given vecinity points.
		The extracted vecinity features are:
		aspect - (delta_y(t) - delta_x(t)) / (delta_y(t) + delta_x(t))
		slope - cosine and sine the angle alpha(t) of the straight line
				from the first to the last vecinity point
		curliness - length of trajectory / max(delta_x(t), delta_y(t)
		linearity - mean(square distance from each point to the straight line)
		@type v: coordinates array (list of 2-tuples)
		@returns 5 tuple = (aspect, cos_slope, sin_slope, curliness, liniarity)
		"""
		dx = abs(v[-1][0] - v[0][0])
		dy = abs(v[-1][1] - v[0][1])
		line_len = math.sqrt(dx ** 2 + dy ** 2)

		if dy + dx != 0:
			aspect = (dx - dy) / (dy + dx)
		else:
			aspect = 0
		if line_len != 0:
			sin_slope = dy / line_len
			cos_slope = dx / line_len
		else:
			sin_slope, cos_slope = 0, 0

		trajectory_len = 0
		liniarity = 0
		for i in range(len(v) - 1):
			trajectory_len += math.sqrt((v[i][0] - v[i + 1][0]) ** 2 +
			                            (v[i][1] - v[i + 1][1]) ** 2)
			liniarity += FeatureExtractor.dist_point_to_line(v[i][0], v[i][1],
			                                                 v[0][0], v[0][1],
			                                                 v[-1][0], v[-1][1])
		if max(dx, dy) != 0:
			curliness = trajectory_len / max(dx, dy)
		else:
			curliness = 0
		liniarity /= len(v)
		return aspect, cos_slope, sin_slope, curliness, liniarity

	def extract(self, writing):
		"""
		Extract feature vector sequence.
		Will not modify writing, but instead use a copy.
		@type character: tegaki.character.Writing
		"""
		writing = writing.copy()

		#normalize
		writing.crop_to_mbr()
		writing.fit_to_box(300, 300)
		writing.normalize_position()
		writing.smooth()

		#resample and connect stroke endpoints
		strokes = writing.get_strokes(full=True)
		annotated_points = self.connect_stroke_endpoints(self.resample_strokes(strokes))

		feature_vector = []  # list of point-level features
		x, y = None, None
		# wr_cos, wr_sin = 1, 0
		# curv_cos, curv_sin = 1, 0
		vecinity = deque(annotated_points[0:self.vecinity_reach + 1])

		for i in range(len(annotated_points)):
			x_prev, y_prev = x, y
			pen_down, x, y = annotated_points[i]
			if i + 1 < len(annotated_points):
				_, x_next, y_next = annotated_points[i + 1]
			else:
				x_next, y_next = None, None

			# check to see if points overlap!

			features = [pen_down, x, y]  # features for current point
			features.extend(FeatureExtractor.writing_direction(x, y, x_next, y_next))
			features.extend(FeatureExtractor.curvature(x, y, x_next, y_next, x_prev, y_prev))
			features.extend(FeatureExtractor.vecinity_features(list(vecinity)))

			feature_vector.append(self.filter_active_features(features))

			# update vecinity
			if i + self.vecinity_reach + 1 < len(annotated_points):
				vecinity.append(annotated_points[i + self.vecinity_reach])
			if len(vecinity) > 2 * self.vecinity_reach + 1:
				vecinity.popleft()

		return feature_vector

	def filter_active_features(self, features):
		filtered_features = []
		for i in range(len(features)):
			feature_name = self.feature_order[i]
			if self.active_features[feature_name] == True:
				filtered_features.append(features[i])
		return filtered_features


if __name__ == "__main__":
	extractor = FeatureExtractor(arc_len=20)

	writing = Writing()
	stroke1 = Stroke()
	stroke1.append_point(Point(1, 1))
	stroke1.append_point(Point(1.5, 2))
	writing.append_stroke(stroke1)
	stroke2 = Stroke()
	stroke2.append_point(Point(3, 3))
	stroke2.append_point(Point(4, 3))
	writing.append_stroke(stroke2)
	stroke3 = Stroke()
	writing.append_stroke(stroke3)
	stroke4 = Stroke()
	stroke4.append_point(Point(4, 4))
	stroke4.append_point(Point(5, 5))
	stroke4.append_point(Point(6, 4))
	writing.append_stroke(stroke4)

	writing.remove_empty_strokes()
	for stroke in writing.get_strokes():
		print stroke

	feature_vector = extractor.extract(writing)

	for f in feature_vector:
		print f
	plt.show()

# pen_up = extractor.connect_stroke_endpoints(writing.get_strokes(full = True))
# for stroke in pen_up:
# 	for p in stroke:
# 		print p.x, p.y


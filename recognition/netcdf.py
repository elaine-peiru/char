import string
import traceback

import numpy as np
import netcdf_helpers

from feature_extractor import FeatureExtractor
from tegaki.charcol import CharacterCollection


class NetCDFBuilder:
	def __init__(self, labels, feature_extractor):
		"""
		RNNLIB nc files builder for a spefific sequence classification problem:
		@param labels: array of label strings

		@param feature_extractor: recognition.feature_extractor.FeatureExtractor
		"""
		self.feature_extractor = feature_extractor
		self.labels = labels

	@staticmethod
	def save_to_ncFile(ncFilename, labels, inputs, targetStrings, seqLengths, seqDims, seqTags=None):
		"""
		Builds the nc file from the given variables.
		"""
		#create a new .nc file
		file = netcdf_helpers.NetCDFFile(ncFilename, 'w')

		#create the dimensions
		netcdf_helpers.createNcDim(file, 'numSeqs', len(seqLengths))
		netcdf_helpers.createNcDim(file, 'numTimesteps', len(inputs))
		netcdf_helpers.createNcDim(file, 'inputPattSize', len(inputs[0]))
		netcdf_helpers.createNcDim(file, 'numDims', 1)
		netcdf_helpers.createNcDim(file, 'numLabels', len(labels))

		#create the variables
		if seqTags is not None:
			netcdf_helpers.createNcStrings(file, 'seqTags', seqTags, ('numSeqs', 'maxSeqTagLength'), 'sequence tags')
		netcdf_helpers.createNcStrings(file, 'labels', labels, ('numLabels', 'maxLabelLength'), 'labels')
		if targetStrings is not None:
			netcdf_helpers.createNcStrings(file, 'targetStrings', targetStrings, ('numSeqs', 'maxTargStringLength'),
			                               'target strings')
		netcdf_helpers.createNcVar(file, 'seqLengths', seqLengths, 'i', ('numSeqs',), 'sequence lengths')
		netcdf_helpers.createNcVar(file, 'seqDims', seqDims, 'i', ('numSeqs', 'numDims'), 'sequence dimensions')
		netcdf_helpers.createNcVar(file, 'inputs', inputs, 'f', ('numTimesteps', 'inputPattSize'), 'input patterns')

		#write the data to disk
		print "closing file", ncFilename
		file.close()

	def convert_writing(self, writing, ncFilename):
		# ignore empty characters
		writing.remove_empty_strokes()
		if writing.empty():
			print "empty writing"
			return

		seq_inputs = self.feature_extractor.extract(writing)

		inputs = seq_inputs
		seqLengths = [len(seq_inputs)]
		seqDims = [[len(seq_inputs)]]
		# targetStrings = [char.get_utf8()]
		targetStrings = None

		NetCDFBuilder.save_to_ncFile(ncFilename, self.labels, inputs, targetStrings, seqLengths, seqDims)

	def _create_dataset(self, chars, ds_size, ncFilename):
		"""
		Extracts features from chars generator and builds the nc variables.
		Also saves to file those variables.
		@param ds_size: the number of chars to use for this dataset
		"""
		malformed_chars = 0
		empty_chars = 0

		inputs = []
		targetStrings = []
		seqLengths = []
		seqDims = []

		print 'Extracting features...'
		try:
			for i in range(ds_size):
				if i != 0 and i % 500 == 0:
					print 'at char', i
				char = chars.next()

				# ignore empty characters
				char.remove_empty_strokes()
				if char.empty():
					empty_chars += 1
					continue

				# ignore malformed characters
				try:
					seq_inputs = self.feature_extractor.extract(char.get_writing())
				except Exception:
					traceback.print_exc()
					malformed_chars += 1
					continue

				inputs += seq_inputs
				seqLengths.append(len(seq_inputs))
				seqDims.append([len(seq_inputs)])
				targetStrings.append(char.get_utf8())
		except StopIteration:
			pass

		print "malformed chars:", malformed_chars
		print "empty chars:", empty_chars
		NetCDFBuilder.save_to_ncFile(ncFilename, self.labels, inputs, targetStrings, seqLengths, seqDims)

	def create_datasets(self, db_name, dir_prefix, train_percent=0.6, validation_percent=0.2, test_percent=0.2):
		"""
		Splits into train, test and validation datasets and builds them.
		From the given tegaki database name.
		@precondition(train_percent + validation_percent + test_percent == 1.0)
		"""
		db_file = "unipen_db/" + db_name + ".chardb"
		charcol = CharacterCollection(db_file)

		num_chars = charcol.get_total_n_characters()
		print "total chars", num_chars
		chars = charcol.get_random_characters_gen(num_chars)

		train_size = int(num_chars * train_percent)
		validation_size = int(num_chars * validation_percent)
		if (train_percent + validation_percent + test_percent) == 1.0:
			# all the db is used
			test_size = num_chars - train_size - validation_size
		else:
			# only a fraction of the db is used
			test_size = int(num_chars * test_percent)

		print 'train set size:', train_size
		self._create_dataset(chars, train_size, dir_prefix + '_train_' + str(int(train_percent * 100)) + '.nc')
		print 'validation set size:', validation_size
		if validation_percent != 0.0:
			self._create_dataset(chars, validation_size,
			                     dir_prefix + '_validation_' + str(int(validation_percent * 100)) + '.nc')
		print 'test set size:', test_size
		if test_percent != 0.0:
			self._create_dataset(chars, test_size, dir_prefix + '_test_' + str(int(test_percent * 100)) + '.nc')

	@staticmethod
	def convert_pybrain_dataset(ds, ncFilename):
		"""
		Build RNNLIB netcdf file from pybrain dataset.
		@type ds: pybrain.datasets.SequentialDataSet
		"""
		numSeqs = ds.getNumSequences()
		inputs = []
		seqDims = []
		seqLengths = []
		labels = map(None, string.digits)
		targetStrings = []

		for i, seq in enumerate(ds):
			seqLengths.append(ds.getSequenceLength(i))
			seqDims.append([seqLengths[-1]])
			targetString = None
			ds.gotoSequence(i)
			for inpt, target in list(seq):
				# print inpt, string.digits[np.where(target == 1)[0][0]]
				inputs.append(inpt)
				if targetString is None:
					targetString = string.digits[np.where(target == 1)[0][0]]
					targetStrings.append(targetString)
				# inputs = inputs + inpt.tolist()

		numTimesteps = len(inputs)
		inputPattSize = len(inputs[0])
		numLabels = len(labels)
		print "sequences", numSeqs
		print "numPattSize", inputPattSize
		print "timesteps", numTimesteps

		NetCDFBuilder.save_to_ncFile(ncFilename, labels, inputs, targetStrings, seqLengths, seqDims)


if __name__ == '__main__':
	# train_ds = SequentialDataSet.loadFromFile("datasets/7best3f.ds")
	# test_ds = SequentialDataSet.loadFromFile("datasets/3best3f.ds")
	# NetCDFBuilder.convert_pybrain_dataset(train_ds, "datasets/7best3f.nc")
	# NetCDFBuilder.convert_pybrain_dataset(test_ds, "datasets/3best3f.nc")

	digits = map(None, string.digits)
	up_letters = map(None, string.ascii_uppercase)
	low_letters = map(None, string.ascii_lowercase)
	feature_extractor = FeatureExtractor(arc_len=20)
	# feature_extractor.set7f()
	nc_builder = NetCDFBuilder(up_letters, feature_extractor)
	nc_builder.create_datasets(db_name='1b/best_1b', dir_prefix='datasets/1b/12f', train_percent=0.6, validation_percent=0.2,
	                           test_percent=0.2)
__author__ = 'Paul Adrian Titei'

from tegaki.unipen import *
from tegaki.charcol import CharacterCollection

digits_dir = "/run/media/titei/AC108D4F108D2206/Workspace/licenta/unipen/train_r01_v07/data/1c"
include_dir = "/run/media/titei/AC108D4F108D2206/Workspace/licenta/unipen/train_r01_v07/include"


def unipen_to_sqlite():
	"""
	Loads the unipen training set and saved each db to an sqlite file.
	"""
	databases = {}  # databases(charcol) indexed by their name. {db_name(str): charcol(CharacterCollection), ..}
	skipped_files = []
	for root, dirs, files in os.walk(digits_dir):
		# print root
		for file in files:
			if os.path.splitext(file)[1] != ".dat":
				continue

			filepath = os.path.join(root, file)

			db_name = os.path.relpath(root, digits_dir).replace(os.sep, ".")

			# add database entry if it doesn't exist
			if db_name not in databases:
				databases[db_name] = CharacterCollection()

			print 'parsing', filepath
			up = UnipenParser()
			up.parse_file(filepath, include_dir)
			try:
				charcol = up.get_character_collection()
				databases[db_name].merge([charcol])
			except IndexError:
				skipped_files.append(filepath)

	for file in skipped_files:
		print file

	# merge db's from the same source, eg. apa01-apa20 ==> apa
	merged_databases = {}
	for db_name, db in databases.iteritems():
		if db_name.find('.') != -1:
			merged_db_name = db_name.split('.')[0]
			# add database entry if it doesn't exist
			if merged_db_name not in merged_databases:
				merged_databases[merged_db_name] = CharacterCollection()
			merged_databases[merged_db_name].merge([db])
	databases = dict(databases.items() + merged_databases.items())

	if not os.path.exists("unipen_db"):
		os.makedirs("unipen_db")
	for db_name, db in databases.iteritems():
		db_path = os.path.join("unipen_db", db_name) + ".chardb"
		print "creating", db_name
		db.save(db_path)


def group_unipen_db():
	"""
	Group dbs from the same contributor in folders.
	"""
	unipen_db_dir = os.path.abspath("unipen_db")

	for root, dirs, files in os.walk(unipen_db_dir):
		for file in files:
			if file.count('.') != 2:
				continue
			# file is a sub_db
			db_name = file.split('.')[0]
			dir_path = os.path.join(unipen_db_dir, db_name)
			if not os.path.exists(dir_path):
				os.makedirs(dir_path)

			src = os.path.join(root, file)
			dst = os.path.join(dir_path, file)
			os.rename(src, dst)


def group_best():
	best_1a = ['aga', 'apa', 'apb', 'app',
	            'art', 'ced', 'gmd', 'ibm',
	            'ipm', 'pri', 'syn', 'uqb',
	            'val']
	best_1b = ['aga', 'apa', 'apb', 'app', 'art',
	           'ced', 'ibm', 'kai', 'lou', 'pri',
	           'syn', 'tos', 'upb', 'val',
	           'cea', 'ceb']
	best_1c = ['aga', 'apa', 'apb', 'app', 'art',
	           'cea', 'ceb', 'ced', 'gmd',
	           'ibm', 'imp', 'kai', 'lav',  'lou',
	           'mot', 'pri', 'sie',
	           'syn', 'tos', 'val']
	best_dbs = best_1c

	charcols = []
	for db_name in best_dbs:
		db_file = 'unipen_db/' + db_name + '.chardb'
		charcol = CharacterCollection(db_file)
		# print db_name, charcol.get_total_n_characters()
		charcols.append(charcol)

	charcol_best = CharacterCollection()
	charcol_best.merge(charcols)
	print charcol_best.get_total_n_characters()
	charcol_best.save("unipen_db/best_1c.chardb")

# unipen_to_sqlite()
# group_unipen_db()
# group_best()
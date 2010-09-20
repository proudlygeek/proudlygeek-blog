class Config(object):
	DATABASE = '/tmp/blog.db'
	DEBUG = False
	TESTING = False
	SECRET_KEY = 'development key'

class ProductionConfig(Config):
	DATABASE_URI = 'mysql://user@localhost/foo'

class DevelopmentConfig(Config):
	DEBUG = True

class TestinConfig(Config):
	TESTING = True

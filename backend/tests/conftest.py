import os,tempfile
_fd,_path=tempfile.mkstemp(suffix='.db');os.close(_fd);os.unlink(_path)
os.environ['DATABASE_URL']='sqlite:///'+_path
os.environ['REDIS_URL']='redis://127.0.0.1:6379/15'
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'

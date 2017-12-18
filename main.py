import signal
import pickle
from util import s3
from threading import Timer

import redis
import os

from stylelens_feature.feature_extract import ExtractFeature
from stylelens_object.objects import Objects
from bluelens_spawning_pool import spawning_pool
from bluelens_log import Logging

STR_BUCKET = "bucket"
STR_STORAGE = "storage"
STR_CLASS_CODE = "class_code"
STR_NAME = "name"

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

SPAWN_ID = os.environ['SPAWN_ID']
REDIS_SERVER = os.environ['REDIS_SERVER']
REDIS_PASSWORD = os.environ['REDIS_PASSWORD']
RELEASE_MODE = os.environ['RELEASE_MODE']
# DATA_SOURCE = os.environ['DATA_SOURCE']
DATA_SOURCE_QUEUE = 'REDIS_QUEUE'
DATA_SOURCE_DB = 'DB'

REDIS_OBJECT_FEATURE_QUEUE = 'bl:object:feature:queue'
REDIS_OBJECT_INDEX_QUEUE = 'bl:object:index:queue'

options = {
  'REDIS_SERVER': REDIS_SERVER,
  'REDIS_PASSWORD': REDIS_PASSWORD
}
log = Logging(options, tag='bl-object-indexer')
rconn = redis.StrictRedis(REDIS_SERVER, port=6379, password=REDIS_PASSWORD)
feature_extractor = ExtractFeature(use_gpu=True)
storage = s3.S3(AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY)

heart_bit = True
object_api = Objects()

def start_index():
  log.info('start_index')
  def items():
    while True:
      yield rconn.blpop([REDIS_OBJECT_INDEX_QUEUE])

  def request_stop(signum, frame):
    log.info('stopping')
    rconn.connection_pool.disconnect()
    log.info('connection closed')

  signal.signal(signal.SIGINT, request_stop)
  signal.signal(signal.SIGTERM, request_stop)

  for item in items():
    key, obj_data = item
    obj = pickle.loads(obj_data)
    log.debug(obj)

    if obj['feature'] == None:
      try:
          file = download_image(obj)
      except Exception as e:
        log.error(str(e))
        continue
      feature = feature_extractor.extract_feature(file)
      log.debug(feature)
      obj['feature'] = feature.tolist()
      save_object_to_db(obj)
      rconn.lpush(REDIS_OBJECT_FEATURE_QUEUE, pickle.dumps(obj, protocol=2))

    global  heart_bit
    heart_bit = True

def save_object_to_db(obj):
  log.info('save_object_to_db')
  global object_api
  try:
    api_response = object_api.update_object(obj)
    log.debug(api_response)
  except Exception as e:
    log.warn("Exception when calling update_object: %s\n" % e)

def check_health():
  global  heart_bit
  log.info('check_health: ' + str(heart_bit))
  if heart_bit == True:
    heart_bit = False
    Timer(120, check_health, ()).start()
  else:
    delete_pod()

def delete_pod():
  log.info('delete_pod: ' + SPAWN_ID)

  data = {}
  data['namespace'] = RELEASE_MODE
  data['id'] = SPAWN_ID
  spawn = spawning_pool.SpawningPool()
  spawn.setServerUrl(REDIS_SERVER)
  spawn.setServerPassword(REDIS_PASSWORD)
  spawn.delete(data)

def download_image(obj):
  TMP_CROP_IMG_FILE = './tmp.jpg'
  key = os.path.join(RELEASE_MODE, obj[STR_CLASS_CODE], obj[STR_NAME]+ '.jpg')
  log.debug('Try download : ' + str(key))
  storage.download_file_from_bucket(obj[STR_BUCKET], TMP_CROP_IMG_FILE, key)
  return TMP_CROP_IMG_FILE

if __name__ == "__main__":
  Timer(120, check_health, ()).start()
  start_index()

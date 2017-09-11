import re
import time
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from kafka import KafkaProducer
from kafka import KafkaConsumer
import pymongo
from bson.objectid import ObjectId

from parser.settings import *

module = __import__('parser.parser.parser', globals(), locals(),['Parser', 'ACMParser'])

consumer = KafkaConsumer(KAFKA_RESULT_TOPIC, group_id=KAFKA_CONSUMER_GROUP, bootstrap_servers=KAFKA_HOST)

connection = pymongo.MongoClient(MONGODB_SERVER, MONGODB_PORT)
db = connection[MONGODB_DB]
resultCollection = db[MONGODB_COLLECTION_RESULT]

rules = [
	{'pattern': r'http://example\.com', 'parser': 'ACMParser'},
	{'pattern': r'.*', 'parser': 'Parser'}
]

def creatInstace(className):
	instance = getattr(module, className)
	return instance()

def parseResult(rules, result):
	for item in rules:
		if re.search(item['pattern'], result['url']):
			parser = creatInstace(item['parser'])
			parser.parse(result['result'])
			# print time.strftime('parse complete %Y-%m-%d %H:%M:%S', time.localtime(time.time()))
			return
			
def main():
	for msg in consumer:
		mongoId = msg.value
		record = resultCollection.find_one({'_id':ObjectId(mongoId)})
		parseResult(rules, record)
		

if __name__ == "__main__":
	main()

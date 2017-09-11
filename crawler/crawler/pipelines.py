# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from kafka import KafkaProducer
from scrapy.conf import settings
import pymongo

class TutorialPipeline(object):
	# def open_spider(self, spider):
    #     # self.producer = KafkaProducer(bootstrap_servers='192.168.1.20:9092')
    #     pass
    def __init__(self):
        connection = pymongo.MongoClient(
            settings['MONGODB_SERVER'],
            settings['MONGODB_PORT']
        )
        db = connection[settings['MONGODB_DB']]
        self.collection = db[settings['MONGODB_COLLECTION']]
        kafkaServer = settings['KAFKA_HOST']
        self.resultTopic = settings['KAFKA_RESULT_TOPIC']
        self.producer = KafkaProducer(bootstrap_servers=kafkaServer)

    def process_item(self, item, spider):
        resultId = self.collection.insert(item)
        future = self.producer.send(self.resultTopic, str(resultId))
        future.get(timeout=60)
        return item

    def close_spider(self, spider):
        # self.producer.close()
        pass
        
    

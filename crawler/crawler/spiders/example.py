# -*- coding: utf-8 -*-
import scrapy
from scrapy.conf import settings
from scrapy import signals

from kafka import KafkaProducer
from kafka import KafkaConsumer

from ..kafka_spider.spider import ListeningKafkaSpider



class ExampleSpider(ListeningKafkaSpider):
    name = "example"

    def process_kafka_message(self, message):
        print '______________' + '---------------------'
        return message.value
        
    def parse(self, response):
        print response.text
        yield {
            'url': response.request.url,
            'result': response.text
        }

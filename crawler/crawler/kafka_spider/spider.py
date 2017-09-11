import scrapy
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.log import logger

from kafka.consumer import KafkaConsumer


class ListeningKafkaSpider(scrapy.Spider):
    """
    Spider that reads urls from a useless topic when idle.
    This spider will exit only if stopped, otherwise it keeps
    listening to messages on the given topic
    Specify the topic to listen to by setting the spider's `kafka_topic`.
    Messages are assumed to be URLS, one by message. To do custom
    processing of useless messages, override the spider's `process_kafka_message`
    method
    """

    """
    Mixin class to implement reading urls from a useless queue.
    :type kafka_topic: str
    """
	
    def process_kafka_message(self, message):
        """"
        Tell this spider how to extract urls from a useless message. This method should be overwritten.
        :param message: A Kafka message object
        :type message: useless.common.OffsetAndMessage
        :rtype: str or None
        """
        if not message:
            return None

        return message.value

    def setup_kafka(self, settings):
        """Setup kafka connection and idle signal.
        This should be called after the spider has set its crawler object.
        :param settings: The current Scrapy settings being used
        :type settings: scrapy.settings.Settings
        """
        topic = settings.get('KAFKA_SOURCE_TOPIC', 'test')
        kafka_host = settings.get('KAFKA_HOST', 'localhost:9092')
        group = settings.get('KAFKA_CONSUMER_GROUP','scrapy-kafka')
        self.consumer = KafkaConsumer(topic, group_id=group, bootstrap_servers=kafka_host, enable_auto_commit=True)
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        self.crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        logger.info("Reading URLs from kafka topic '%s'" % topic)

    def next_request(self):
        """
        Returns a request to be scheduled.
        :rtype: str or None
        """
        message = next(self.consumer)
        url = self.process_kafka_message(message)
        if not url:
            return None
        return self.make_requests_from_url(url)

    def schedule_next_request(self):
        """Schedules a request if available"""
        req = self.next_request()
        if req:
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        self.schedule_next_request()
        raise DontCloseSpider

    def item_scraped(self, *args, **kwargs):
        """Avoids waiting for the spider to  idle before scheduling the next request"""
        self.schedule_next_request()

    @classmethod
    def from_crawler(cls, crawler):
        spider = super(ListeningKafkaSpider, cls).from_crawler(crawler)
        spider.setup_kafka(crawler.settings)
        return spider

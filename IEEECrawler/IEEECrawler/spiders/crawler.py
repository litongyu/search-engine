import scrapy
import pymongo
from scrapy.selector import Selector
from scrapy.conf import settings
import re
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
import json
import math
import traceback

class IEEESpider(scrapy.Spider): #get conference list
	name = 'spider_1'
	
	base_url = "http://ieeexplore.ieee.org"
	
	recordsPerPage = 500.0
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
		'Accept': 'application/json, text/plain, */*',
		'Accept-Encoding': 'gzip,deflate',
		'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
		'Connection': 'keep-alive',
		'Content-Type': 'application/json;charset=UTF-8',
		'Referer':'http://ieeexplore.ieee.org/browse/conferences/title/'
	}
	
	def __init__(self):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
		
	def start_requests(self):
		site = self.base_url + '/rest/publication?reload=true'
		data = {'contentType':'conferences','tabId':'title','publisher':'','collection':''}
		yield scrapy.http.Request(url=site, method="POST", headers=self.hdr, body=json.dumps(data), callback=self.parse)
		
	def parse(self, response):
		print response.text
		print response.body
		totalRecords = json.loads(response.text)['totalRecords']
		pages = int(math.ceil(totalRecords / self.recordsPerPage))
		site = self.base_url + '/rest/publication?reload=true'
		data = {"contentType":"conferences","tabId":"title","publisher":"","collection":"","rowsPerPage":self.recordsPerPage}
		for i in range(1, pages + 1):
			data['pageNumber'] = i
			yield scrapy.http.Request(url=site, method="POST", headers=self.hdr, body=json.dumps(data), callback=self.parseConfList)
			
	def parseConfList(self, response):
		records = json.loads(response.text)['records']
		for record in records:
			if not record.has_key('titleHistory'):
				temp = {
					'title': record['title'],
					'id': record['id'],
					'url': self.base_url + record['publicationLink'],
					'confTitle': record['title'],
					'confUrl': self.base_url + record['publicationLink']
				}
				self.collection.insert(temp)
			else:
				for item in record['titleHistory']:
					temp = {
						'title': item['title'],
						'id': item['publicationNumber'],
						'url': self.base_url + item['publicationLink'],
						'confTitle': record['title'],
						'confUrl': self.base_url + record['publicationLink']
					}
					self.collection.insert(temp)
					

class IEEEPaperListSpider(scrapy.Spider): #get paper list of each conference
	name = 'spider_2'
	
	base_url = "http://ieeexplore.ieee.org"
	
	rowsPerPage = 10000
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
		'Accept': 'application/json, text/plain, */*',
		'Accept-Encoding': 'gzip,deflate',
		'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
		'Connection': 'keep-alive',
		'Content-Type': 'application/json;charset=UTF-8'
	}
	
	def __init__(self, startIndex, crawlCount):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
		self.startIndex = startIndex
		self.crawlCount = crawlCount
		
	def start_requests(self):
		startIndex = int(self.startIndex)
		crawlCount = int(self.crawlCount)
		print "startIndex: " + self.startIndex + "  crawlCount: " + self.crawlCount
		if not startIndex is None and not crawlCount is None:
			records = self.collection.find({}, no_cursor_timeout=True).skip(startIndex).limit(crawlCount)
		else:
			records = self.collection.find({}, no_cursor_timeout=True)
		
		for record in records:
			url = record['url'] + '&pageNumber=1&rowsPerPage=' + str(self.rowsPerPage)
			yield scrapy.http.Request(url=url, headers=self.hdr, callback=self.parse)
			
	def parse(self, response):
		lis = response.xpath('//*[@id="results-blk"]/div/ul/li')
		paperList = []
		for li in lis:
			title = li.xpath('./div[@class="txt"]/h3/a/span/text()').extract_first()
			if not title is None:
				url = self.base_url + li.xpath('./div[@class="txt"]/h3/a/@href').extract_first()
				paperList.append({
					'title': title,
					'url': url
				})
		print response.request.url
		pattern = r'punumber=([0-9A-Za-z]+)'
		punumber = re.findall(pattern, response.request.url)[0]
		record = self.collection.find_one({'id':punumber})
		record['paperList'] = paperList
		self.collection.save(record)

class IEEEPaperDetail1Spider(scrapy.Spider): #get keywords abstract authors pdfUrl of each paper
	name = 'spider_3'
	
	base_url = "http://ieeexplore.ieee.org"
	
	hdr = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36',
		'Accept': 'application/json, text/plain, */*',
		'Accept-Encoding': 'gzip,deflate',
		'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
		'Connection': 'keep-alive',
		'Content-Type': 'application/json;charset=UTF-8'
	}
	
	def __init__(self, startIndex, crawlCount):
		connection = pymongo.MongoClient(
			settings['MONGODB_SERVER'],
			settings['MONGODB_PORT']
		)
		db = connection[settings['MONGODB_DB']]
		self.collection = db[settings['MONGODB_COLLECTION']]
		self.startIndex = startIndex
		self.crawlCount = crawlCount
	
	def start_requests(self):
		startIndex = int(self.startIndex)
		crawlCount = int(self.crawlCount)
		records = self.collection.find({}, no_cursor_timeout=True).skip(startIndex).limit(crawlCount)
		for record in records:
			for paper in record['paperList']:
				yield scrapy.http.Request(url=paper['url'], headers=self.hdr, callback=self.parse)

	def parse(self, response):
		pattern = r'global\.document\.metadata=(\{.*\});'
		scriptsStr = json.dumps(response.xpath('//script[@type="text/javascript"]').extract())
		metadataString = re.findall(pattern, scriptsStr)[0]
		temp = re.sub(r'\\(?=")', '', metadataString)
		temp = re.sub(r'\\\\(?=")', r'\\', temp) # process \\" in metadataString
		metadata = json.loads(temp)
		abstract = metadata["abstract"]
		pdfUrl = self.base_url + metadata['pdfUrl']
		authors = []
		for item in metadata['authors']:
			authors.append(item['name'])
		keywords = []
		for item in metadata['keywords']:
			if 'Author Keywords' in item['type']:
				keywords = item['kwd']
				break
		articleId = metadata['articleId']
		referenceSite = self.base_url + '/rest/document/' + articleId + '/references'
		citationSite = self.base_url + '/rest/document/' + articleId + '/citations'
		yield scrapy.http.Request(url=referenceSite, headers=self.hdr, callback=self.parseReferences)
		yield scrapy.http.Request(url=citationSite, headers=self.hdr, callback=self.parseCitations)
		record = self.collection.find_one({'paperList':{'$elemMatch':{'url':{'$regex': '[^0-9]' + articleId + '[^0-9]'}}}})
		for item in record['paperList']:
			if articleId in item['url']:
				item['abstract'] = abstract
				item['pdfUrl'] = pdfUrl
				item['authors'] = authors
				item['keywords'] = keywords
				item['articleId'] = articleId
				self.collection.save(record)
				break
				
	def parseReferences(self, response):
		data = json.loads(response.text)
		references = []
		if data.has_key('references'):
			for item in data['references']:
				temp = {
					"title": "",
					"url": ""
				}
				if item.has_key('title'):
					temp['title'] = item['title']
				else:
					temp['title'] = item['text']
				if item.has_key('links') and item['links'].has_key('documentLink'):
					temp['url'] = self.base_url + item['links']['documentLink']
				references.append(temp)
		record = self.collection.find_one({'paperList': {'$elemMatch': {'url': {'$regex': '[^0-9]' + data['articleNumber'] + '[^0-9]'}}}})
		for item in record['paperList']:
			if data['articleNumber'] in item['url']:
				item['references'] = references
				self.collection.save(record)
				break
				
	def parseCitations(self, response):
		pattern = r'document/(\d*)/citations'
		articleId = re.findall(pattern, response.request.url)[0]
		data = json.loads(response.text)
		citations = []
		if data.has_key('paperCitations') and data['paperCitations'].has_key('ieee'):
			for item in data['paperCitations']['ieee']:
					temp = {
						"title": item['title'],
						"url": ""
					}
					if item.has_key('links') and item['links'].has_key('documentLink'):
						temp['url'] = self.base_url + item['links']['documentLink']
					citations.append(temp)
		if data.has_key('paperCitations') and data['paperCitations'].has_key('nonIeee'):
			for item in data['paperCitations']['nonIeee']:
					temp = {
						"title": item['title'],
						"url": ""
					}
					if item.has_key('links') and item['links'].has_key('crossRefLink'):
						temp['url'] = self.base_url + item['links']['crossRefLink']
					citations.append(temp)
		record = self.collection.find_one({'paperList': {'$elemMatch': {'url': {'$regex': '[^0-9]' + articleId + '[^0-9]'}}}})
		for item in record['paperList']:
			if articleId in item['url']:
				item['citations'] = citations
				self.collection.save(record)
				break

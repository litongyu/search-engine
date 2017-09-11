from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092')
while(True):
	input = raw_input()
	producer.send('urls', input)
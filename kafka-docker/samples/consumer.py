from kafka import KafkaConsumer
import sys
topic = sys.argv[1]
consumer = KafkaConsumer(str(topic), bootstrap_servers='127.0.0.1:9092')
for msg in consumer:
	print(msg)

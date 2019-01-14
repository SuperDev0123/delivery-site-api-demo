import redis

redis_host = "localhost"
redis_port = 6379
redis_password = ""

def redis_con():
	try:
		redisCon = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password)
	except:
		print('Redis DB connection error!')
		exit(1)

	return redisCon

def save2Redis(key, value):
	redisCon = redis_con()
	redisCon.set(key, value)

def clearFileCheckHistory(filename):
	redisCon = redis_con()
	errorCnt = redisCon.get(filename)
	redisCon.delete(filename)

	if errorCnt is not None:
		for index in range(int(errorCnt)):
			redisCon.delete(filename + str(index))

def getFileCheckHistory(filename):
	redisCon = redis_con()
	errorCnt = redisCon.get(filename)
	errors = []

	if errorCnt is None:
		return 0
	else:
		if int(errorCnt) > 0:
			for index in range(int(errorCnt)):
				errors.append(redisCon.get(filename + str(index)).decode("utf-8"))
		elif int(errorCnt) == 0:
			return 'success'

		return errors
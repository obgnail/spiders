import requests
from requests import ConnectionError
import re
from multiprocessing import Pool

def request_xhr_json(url):
	headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
		AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
	try:
		response = requests.get(url,headers=headers)
		if response.status_code == 200:
			return response.json()
		else:
			print('requests index error',response.status_code)
	except ConnectionError:
		print('index ConnectionError',response.status_code)

def parse_xhr_json(data):
	images = data.get('images')[0]

	url = images.get('url')
	name = images.get('copyright')
	imge_name = re.search(r'(.*?) \(©',name,re.S).group(1)
	
	return url,imge_name
	
def request_pic(url):
	headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
		AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
	try:
		response = requests.get(url,headers=headers)
		if response.status_code == 200:
			return response.content
		else:
			print('requests pic error',response.status_code)
	except ConnectionError:
		print('pic ConnectionError',response.status_code)

def save_pic(data,name):
	fileurl = 'pic\\{}.jpg'.format(name)
	with open(fileurl,'wb') as f:
		if f.write(data):	
			print('save successful',name)
		else:
			print('save fail',name)

def main(idx):
	url = 'https://cn.bing.com/HPImageArchive.aspx?format=js&idx={}&n=1&pid=hp'.format(idx) # ajax请求链接
	base_url = 'https://cn.bing.com'  # 图片链接前半部
	html = request_xhr_json(url)
	if html:
		partial_url,pic_name = parse_xhr_json(html)
		pic_url = base_url + partial_url  # 完整的图片链接
		bindata = request_pic(pic_url)
		if bindata:
			save_pic(bindata,pic_name)

if __name__ == '__main__':
	pool = Pool()
	pool.map(main,range(0,8))
	pool.close()


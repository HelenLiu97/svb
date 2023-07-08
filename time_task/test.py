import time
import requests

url = 'http://www.google.com.hk'

print(time.strftime('%Y-%m-%d %H:%M:%S'))
try:
    html = requests.get(url, timeout=5).text
    print('success')
except requests.exceptions.RequestException as e:
    print(e)

print(time.strftime('%Y-%m-%d %H:%M:%S'))
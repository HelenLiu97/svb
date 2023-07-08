import json
import pymysql
import time
from hashlib import sha256
import hmac
import requests


class SVB(object):
    '''
    SVB 是集成所有api的类，方便使用调用
    '''

    def __init__(self):
        # api_key, 构建请求头的关键参数之一
        self.api_key = 'Bearer live_xFfK9rfdW08vkIIF0PJHJd9BNFwdksRm'
        # hmac_key, 构建请求头的关键参数之一
        self.hmac_key = 'uNhcm1Ab3422+f002PZGagSRlkHrEHEwSvY9BY/7+7jXafjPFs7iPJ5ha06v8tXh'
        # 请求资源的基础地址(根据不同的资源拼接成不同的请求地址)
        self.base_url = 'https://api.svb.com'

        self.requests = requests.session()
        self.requests.keep_alive = False

    def create_header(self, method, path, params="", body=""):
        '''
        :param method: 请求资源的方法(POST, GET, DELETE, PATCH)
        :param path: 请求资源的路径https://api.svb.com, 后面的路径
        :param params: 请求资源的参数，默认舍弃'?',例：show_card_number=true
        :param body: 请求资源的body参数，例：'{"data": {"total_card_amount": 12345, "valid_ending_on": "2018-12-25"}}'
        :return: 详细说明请查看：https://www.svb.com/developers/authentication
        '''

        # HMAC签名的KEY
        secret = self.hmac_key
        timestamp = str(int(time.time()))
        message = "\n".join([timestamp, method, path, params, body])
        signature = hmac.new(bytes(secret, 'utf-8'), bytes(message, 'utf-8'), sha256).hexdigest()

        # 构建请求头(需根据不同请求构建不同请求头)
        headers = {'Authorization': self.api_key,
                   'Content-Type': 'application/json',
                   'X-Signature': signature,
                   'X-Timestamp': str(int(time.time()))}

        return headers

    def valid_ending_on(self):
        now_time = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        year = now_time.split('-')[0]
        month = now_time.split('-')[1]
        day = now_time.split('-')[2]
        last_year = int(year) + 3
        last_time = str(last_year) + "-" + month + "-" + day
        return last_time

    def create_card(self, cents):
        '''
        rcn_id 是真实的卡的id， rcn_alias 是对应的卡名， supplier_id 是商户id (详情见api文档)
        :return:
        '''
        path = "/v1/virtualcards"
        method = "POST"
        url = self.base_url + path
        data = {
            "data": {
                "total_card_amount": cents,
                "emails": [],
                "transactions_max": 0,  # 卡的最大交易次数默认1000
                "valid_ending_on": self.valid_ending_on(),
                "mastercard_data": {},
                "metadata": {
                    "purchase_number": "801b"
                },
                "rcn_id": 42708,
                "rcn_alias": "OPOICE API",
                "supplier_id": 142426
            },
            "show_card_number": True
        }
        try:
            body = json.dumps(data)
            resp = self.requests.post(url, headers=self.create_header(method, path, body=body), data=body, timeout=60)
            if resp.status_code == 200:
                data = resp.json().get('data')
                return data
            else:
                return {}
        except Exception as e:
            return {}


class SqlData(object):
    def __init__(self):
        host = "127.0.0.1"
        port = 3306
        user = "root"
        # password = "gute123"
        password = "admin"
        database = "svb"
        self.connect = pymysql.Connect(
            host=host, port=port, user=user,
            passwd=password, db=database,
            charset='utf8'
        )
        self.cursor = self.connect.cursor()

    def close_connect(self):
        if self.cursor:
            self.cursor.close()
        if self.connect:
            self.connect.close()

    def __del__(self):
        self.close_connect()

    def search_card_num(self, amount, status):
        sql = "SELECT COUNT(*) FROM new_card WHERE balance = {} AND status='{}'".format(amount, status)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        return rows[0]

    def insert_card(self, card_number, balance, cvc, expiry, card_id, valid_start_on, valid_end_on, last4):
        sql = "INSERT INTO new_card(card_number, balance, cvc, expiry, card_id, valid_start_on, valid_end_on, last4) " \
              "VALUES ('{}',{},'{}','{}',{},'{}','{}','{}')".format(card_number, balance, cvc, expiry, card_id,
                                                                    valid_start_on, valid_end_on, last4)
        print(sql)
        try:
            self.cursor.execute(sql)
            self.connect.commit()
        except Exception as e:
            self.connect.rollback()
            return False
        return True


sqldata = SqlData()

if __name__ == '__main__':
    # 记录开始时间，在200s后停止开卡，避免再次开卡使用相同卡名重复卡名
    before_t = time.time()

    card_amount = 10
    # 根据需求创建缓存卡
    user_card_num = sqldata.search_card_num(card_amount, '')
    create_num = 1
    new_card = 10 - user_card_num

    while create_num <= new_card:
        if time.time() > before_t + 100:
            break
        # 卡余额放大了100倍，所以20是2000
        data = SVB().create_card(card_amount * 100)
        if data:
            card_number = data.get('card_number')
            available_balance = data.get('available_balance')
            cvc = data.get('cvc')
            expiry = data.get('expiry')
            card_id = data.get('id')
            last4 = data.get('last4')
            valid_starting_on = data.get('valid_starting_on')
            valid_ending_on = data.get('valid_ending_on')
            sqldata.insert_card(card_number, available_balance/100, cvc, expiry, card_id, valid_starting_on, valid_ending_on, last4)
            create_num += 1

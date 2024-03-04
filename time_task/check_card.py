"""
coding:utf-8
@software:PyCharm
@Time:2023/11/9 14:58
@Author:Helen
"""
import hmac
import json
import logging
import time
from hashlib import sha256

import requests
import pymysql
from requests.adapters import HTTPAdapter


class SqlData(object):
    def __init__(self):
        host = "3.17.178.128"
        port = 3306
        user = "root"
        password = "liuxiao@140922"
        database = 'svb'
        self.connect = pymysql.Connect(
            host=host, port=port, user=user,
            passwd=password, db=database,
            charset='utf8',
            connect_timeout=10)
        self.cursor = self.connect.cursor()

    def __del__(self):
        self.close_connect()

    def search_user_id(self, user_name):
        sql = "SELECT id FROM user_info WHERE `name`='{}'".format(user_name)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        if not rows:
            return False
        return rows[0]

    def search_card_data(self, user_id):
        sql = "select card_id, card_number from card_info where user_id={}".format(user_id)
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        return tuple(reversed(rows))

    def search_card_data_set(self, alias):
        sql = "select card_info.alias, card_info.card_id, card_info.card_number, user_info.name from card_info join user_info on card_info.user_id=user_info.id where  card_info.alias = '{}'".format(
            alias)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        return rows

    def search_card_top(self, card_no):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND trans_type='支出' AND  do_type !='开卡' AND  do_type !='手续费'".format(
            card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        return rows[0]

    def search_card_refund(self, card_no):
        sql = "SELECT IFNULL(SUM(do_money),0) FROM user_trans WHERE card_no='{}' AND trans_type='收入'".format(
            card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        return rows[0]

    def search_card_info(self):
        sql = "SELECT card_info.card_id, card_info.card_number, user_info.name FROM card_info join user_info on card_info.user_id=user_info.id WHERE card_info.card_status='T'".format()
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        return rows

    def close_connect(self):
        if self.cursor:
            self.cursor.close()
        if self.connect:
            self.connect.close()


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
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100, pool_maxsize=100)
        self.requests.mount('https://', adapter)
        self.requests.keep_alive = True

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

    def real_card(self):
        path = '/v1/realcards'
        method = 'GET'
        url = self.base_url + path
        resp = self.requests.get(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())

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
                card_number = data.get('card_number')
                available_balance = data.get('available_balance')
                cvc = data.get('cvc')
                expiry = data.get('expiry')
                card_id = data.get('id')
                last4 = data.get('last4')
                valid_starting_on = data.get('valid_starting_on')
                valid_ending_on = data.get('valid_ending_on')
                # rcn_id = data.get('rcn_id')
                # rcn_alias = data.get('rcn_alias')
                # supplier_id = data.get('supplier_id')
                result = {'card_number': card_number, 'cvc': cvc, 'expiry': expiry, 'card_id': card_id,
                          'valid_start_on': valid_starting_on, 'valid_end_on': valid_ending_on, 'last4': last4}
                return result
            else:
                return False
        except Exception as e:
            logging.error("create_card_api_error:" + str(e))
            return False

    def card_detail(self, card_id):
        path = "/v1/virtualcards/{}".format(card_id)
        method = "GET"
        params = 'show_card_number=true&show_realtime_auths=true'
        url = self.base_url + path + "?" + params
        try:
            resp = self.requests.get(url, headers=self.create_header(method, path, params=params), timeout=60)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {}
        except requests.exceptions.RequestException as e:
            logging.error("card_detail_api_error:" + str(e))
            return False

    def all_virtualcards(self):
        path = '/v1/virtualcards'
        method = 'GET'
        url = self.base_url + path
        resp = self.requests.get(url, headers=self.create_header(method, path), timeout=60)
        return resp.json()

    def delete_card(self, card_id):
        path = '/v1/virtualcards/{}'.format(card_id)
        method = 'DELETE'
        url = self.base_url + path
        try:
            resp = self.requests.delete(url, headers=self.create_header(method, path), timeout=60)
            status = resp.status_code
            if status == 204:
                return True
            else:
                return False
        except Exception as e:
            logging.error("delete_card_api_error:" + str(e))
            return self.delete_card(card_id)

    def update_card(self, card_id, cents):
        path = '/v1/virtualcards/{}'.format(card_id)
        method = 'PATCH'
        data = {
            'data': {
                'total_card_amount': cents,
                'per_transaction_max': cents
            }
        }
        url = self.base_url + path
        body = json.dumps(data)
        try:
            resp = self.requests.patch(url, data=body, headers=self.create_header(method, path, body=body), timeout=60)
            status = resp.status_code
            if status == 200:
                resp_data = resp.json()
                available_balance = resp_data.get('data').get('total_card_amount')
                if available_balance == cents:
                    return True, resp_data.get('data').get('available_balance')
                return False
            else:
                return False
        except Exception as e:
            logging.error("update_card_api_error:" + str(e))
            return False

    def card_admin(self):
        path = '/v1/admin/virtualcard'
        method = 'GET'
        url = self.base_url + path
        resp = self.requests.get(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())

    def card_event(self):
        path = '/v1/events/8904371'
        method = 'GET'
        url = self.base_url + path
        resp = self.requests.get(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())

    def create_hook(self):
        path = '/v1/webhooks'
        method = 'POST'
        url = self.base_url + path
        resp = self.requests.post(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())


sqlData = SqlData()
svb = SVB()


def main(card_id, card_number, user_name):
    card_detail = svb.card_detail(card_id)
    if not card_detail:
        return
    available_balance = card_detail.get('data').get('available_balance')
    available_balance = float(available_balance / 100)
    clearings = card_detail.get('data').get('clearings')
    pend_money = 0
    for clear in clearings:
        clearing_type = clear.get('clearing_type')
        billing_amount = clear.get('billing_amount')
        if clearing_type == 'CREDIT':
            trans_money = float(billing_amount / 100)
        else:
            trans_money = -float(billing_amount / 100)
        pend_money += trans_money
    sum_top = sqlData.search_card_top(card_number)
    sum_refund = sqlData.search_card_refund(card_number)
    remain = sum_top - sum_refund
    remain = round(remain, 2)
    pend_money = round(pend_money, 2)

    theory_refund = round(remain + pend_money, 2)
    if theory_refund != available_balance:
        differ = round(theory_refund - available_balance, 2)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write('{},{},{},{},{},{},{}'.format(card_number, card_id, sum_top, sum_refund, available_balance, pend_money, differ) + "\n")


if __name__ == "__main__":
    res = sqlData.search_card_info()
    file_path = './ALL.txt'
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write('卡号,卡ID,系统消费,系统退款,卡余额,卡消费,差额,用户' + "\n")
    for z in res:
        card_id, card_number, user_name = z
        print(card_number)
        with open('./search.txt', 'a', encoding='utf-8') as f:
            f.write('{},'.format(card_number))
        main(card_id, card_number, user_name)

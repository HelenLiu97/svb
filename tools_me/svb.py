import json
import logging
import requests
from hashlib import sha256
import hmac
import time


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
        resp = requests.get(url, headers=self.create_header(method, path), timeout=60)
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
            resp = requests.post(url, headers=self.create_header(method, path, body=body), data=body, timeout=60)
            if resp.status_code == 200:
                data = resp.json().get('data')
                card_number = data.get('card_number')
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
            resp = requests.get(url, headers=self.create_header(method, path, params=params), timeout=60)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {}
        except Exception as e:
            logging.error("card_detail_api_error:" + str(e))
            return False

    def all_virtualcards(self):
        path = '/v1/virtualcards'
        method = 'GET'
        url = self.base_url + path
        resp = requests.get(url, headers=self.create_header(method, path), timeout=60)
        return resp.json()

    def delete_card(self, card_id):
        path = '/v1/virtualcards/{}'.format(card_id)
        method = 'DELETE'
        url = self.base_url + path
        try:
            resp = requests.delete(url, headers=self.create_header(method, path), timeout=60)
            status = resp.status_code
            if status == 204:
                return True
            else:
                return False
        except Exception as e:
            logging.error("delete_card_api_error:" + str(e))
            return False

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
            resp = requests.patch(url, data=body, headers=self.create_header(method, path, body=body), timeout=60)
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
        resp = requests.get(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())

    def card_event(self):
        path = '/v1/events/8904371'
        method = 'GET'
        url = self.base_url + path
        resp = requests.get(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())

    def create_hook(self):
        path = '/v1/webhooks'
        method = 'POST'
        url = self.base_url + path
        resp = requests.post(url, headers=self.create_header(method, path), timeout=60)
        print(resp.json())


svb = SVB()

if __name__ == '__main__':
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
    res = svb.card_detail(38152080)
    print(res)
    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))

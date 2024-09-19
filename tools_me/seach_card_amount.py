"""
coding:utf-8
@software:PyCharm
@Time:2023/9/16 10:12
@Author:Helen
"""
# (dabao) H:\bento_web_version2\tools_me>pyinstaller.exe -F -i search.ico new_bento.py -p H:\bento_web_version2\dabao\Lib\site-packages\


from requests.adapters import HTTPAdapter
import pymysql
import threading
from threading import Lock
import json
import logging
import requests
from hashlib import sha256
import hmac
import time


lock = Lock()


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


class SqlData(object):
    def __init__(self):
        host = "18.218.121.63"
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
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND trans_type='支出' AND  do_type !='开卡'".format(
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

    def close_connect(self):
        if self.cursor:
            self.cursor.close()
        if self.connect:
            self.connect.close()


svb = SVB()


def remain_trans(card_id, card_number, user_name):
    try:
        print("开始查询卡号：{}".format(card_number))
        card_detail = svb.card_detail(card_id)
        available_balance = card_detail.get('data').get('available_balance')
        trans = card_detail.get('data').get('clearings')
        if available_balance is None:
            available_balance = 0

        card_real_pay = 0
        if len(trans) > 0:
            for tran in trans:
                clearing_type = tran.get('clearing_type')
                billing_amount = float(float(tran.get("billing_amount")) / 100)
                if clearing_type == 'CREDIT':
                    trans_money = billing_amount
                else:
                    trans_money = -billing_amount
                card_real_pay += trans_money
        sum_top = SqlData().search_card_top(card_number)
        # print('充值', sum_top)
        sum_refund = SqlData().search_card_refund(card_number)
        # print('退款', sum_refund)
        remain = sum_top - sum_refund
        remain = round(remain, 2)
        available_balance = round(available_balance / 100, 2)
        card_real_pay = round(card_real_pay, 2)
        # print(remain)

        if round(remain + card_real_pay, 2) != available_balance:
            diff = round(remain + card_real_pay - available_balance, 2)
            s = '{},{},{},{},{},{},{},{}'.format(available_balance, card_real_pay, sum_top, sum_refund, card_number,
                                              user_name, diff, card_id)
            text_name = user_name + ".txt"
            with open(text_name, 'a', encoding='utf-8') as f:
                f.write(s + "\n")


    except Exception as e:
        text_name = user_name + "查询失败的卡信息.txt"
        print(e)
        with open(text_name, 'a', encoding='utf-8') as f:
            f.write('卡号: {} 异常,查询失败！查询交易记录失败'.format(card_number) + "\n")
    return


def main():
    username = input('请输入需要查询的用户名:')
    # username = 'TKA04'
    user_id = SqlData().search_user_id(username)
    if not user_id:
        print('无该用户，请核实后重试！')
        time.sleep(3)
        return
    # 按时间段查询操作过得卡
    data = SqlData().search_card_data(user_id)
    card_ = list()
    for i in data:
        card_.append(i)
    card_int = len(card_)
    print(card_)
    print("共计卡量 [" + str(card_int) + "] 张。")
    # return
    text_name = str(username) + ".txt"
    with open(text_name, 'a', encoding='utf-8') as f:
        f.write('卡余额,卡总支出,卡总充值,总退款,卡号,用户,差额,卡ID' + "\n")
    card_info = list(card_)
    print('开始校验余额.........')
    while True:
        loops_len = len(card_info)
        num = 20
        if loops_len < 20:
            num = loops_len
        threads = []
        for i in range(num):
            card_one = card_info.pop()
            card_id = card_one[0]
            card_number = card_one[1]
            # username = ''
            t = threading.Thread(target=remain_trans, args=(card_id, card_number, username))
            threads.append(t)
        for i in threads:  # start threads 此处并不会执行线程，而是将任务分发到每个线程，同步线程。等同步完成后再开始执行start方法
            i.start()
        for i in threads:  # jion()方法等待线程完成
            i.join()
        no_check = len(card_info)
        checked = card_int - no_check
        res = checked / card_int
        bb = "%.2f%%" % (res * 100)
        print("已完成：" + bb)
        if len(card_info) == 0:
            print('即将退出程序........')
            time.sleep(5)
            break


if __name__ == "__main__":
    # res = SqlData().search_card_refund('5563386772995206')
    # print(res)
    main()

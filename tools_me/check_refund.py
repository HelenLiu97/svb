import threading
import pymysql
import time
from hashlib import sha256
import hmac
import requests


card_info = list()


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

    def card_detail(self, card_id):
        path = "/v1/virtualcards/{}".format(card_id)
        method = "GET"
        params = 'show_card_number=true&show_realtime_auths=true'
        url = self.base_url + path + "?" + params
        try:
            resp = self.requests.get(url, headers=self.create_header(method, path, params=params), timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {}
        except Exception as e:
            return False


class SqlSvb(object):
    def __init__(self):
        host = "47.115.94.77"
        port = 3306
        user = "root"
        password = "baocui123"
        database = 'svb'
        self.connect = pymysql.Connect(
            host=host, port=port, user=user,
            passwd=password, db=database,
            charset='utf8',
                )
        self.cursor = self.connect.cursor()

    def __del__(self):
        self.close_connect()

    def close_connect(self):
        if self.cursor:
            self.cursor.close()
        if self.connect:
            self.connect.close()

    def search_del_card(self, user_id):
        sql = "SELECT card_id, card_number FROM card_info WHERE user_id={}".format(user_id)
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['card_id'] = i[0]
            info_dict['card_number'] = i[1]
            info_list.append(info_dict)
        return info_list

    def search_card_top(self, card_no):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND (do_type='充值' OR do_type='批量充值')".format(card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        return rows[0]

    def search_card_gap(self, card_no):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND do_type='注销差额'".format(card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        if not rows[0]:
            return 0
        return rows[0]

    def search_user_id(self, user_name):
        sql = "SELECT id FROM user_info WHERE `name`='{}'".format(user_name)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        if not rows:
            return False
        return rows[0]

    def search_card_refund(self, card_no):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND trans_type='收入'".format(card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        if not rows[0]:
            return 0
        return rows[0]

    def search_pay_money(self, card_no):
        sql = "SELECT SUM(billing_amount) FROM card_trans WHERE card_no='{}' AND status='T' AND mcc != '7999'".format(card_no)
        self.cursor.execute(sql)
        rows = self.cursor.fetchone()
        if not rows[0]:
            return 0
        return rows[0]


SqlData = SqlSvb()
svb = SVB()


def remain_trans(card_no, card_id, user_name, sum_top, gap, sum_refund):
    card_detail = svb.card_detail(card_id)
    if not card_detail:
        # ext_name = str(user_name) + "查询失败的卡信息.txt"
        # s = "{}, 查询失败".format(card_no)
        # with open(ext_name, 'a+') as f:
        #     f.write(s+'\n')
        global card_info
        card_info.append({'card_id': card_id, 'card_number': card_no})
        return
    balance = card_detail.get('data').get('available_balance')
    if balance is None:
        balance = 0
    else:
        balance = balance/100
    remain = sum_top - sum_refund + gap - balance
    authorizations = card_detail.get('data').get('authorizations')
    pend_money = 0
    for pend in authorizations:
        response = pend.get('issuer_response')
        mcc = pend.get('mcc')
        if "Decline" not in response and mcc != '7999':
            trans_money = float(pend.get("billing_amount") / 100)
            pend_money += trans_money
    remain = round(remain, 2)
    pend_money = round(pend_money, 2)
    if remain != pend_money:
        theory_refund = round(remain - pend_money, 2)
        s = "{},{},{},{},{},{},{}".format(card_no, sum_top, gap, sum_refund, balance, pend_money, theory_refund)
        ext_name = str(user_name) + "_PENDING.txt"
        with open(ext_name, 'a+') as f:
            f.write(s+'\n')

    clearings = card_detail.get('data').get('clearings')
    settle_money = 0
    for pend in clearings:
        trans_money = float(pend.get("billing_amount") / 100)
        settle_money += trans_money
    settle_money = round(settle_money, 2)
    if remain != settle_money:
        theory_refund = round(remain - settle_money, 2)
        s = "{},{},{},{},{},{},{}".format(card_no, sum_top, gap, sum_refund, balance, settle_money, theory_refund)
        ext_name = str(user_name) + "_SETTLE.txt"
        with open(ext_name, 'a+') as f:
            f.write(s + '\n')

    for i in clearings:
        billing_amount = i.get('billing_amount')/100
        billing_currency = i.get('billing_currency')
        billing_rate = i.get('exchange_rate')
        billing_mcc = i.get('mcc')
        authorization_date = i.get('authorization_date')
        merchant_name = i.get('merchant_name')
        settlement_date = i.get('settlement_date')
        s = "{},{},{},{},{},{},{},{}".format(card_no, billing_amount, billing_currency, billing_rate, billing_mcc, authorization_date, merchant_name, settlement_date)
        ext_name = str(user_name) + "settle_trans.txt"
        with open(ext_name, 'a+') as f:
            f.write(s + '\n')


def main():
    username = input('请输入用户名：')
    user_id = SqlData.search_user_id(username)
    if not user_id:
        print('无该用户，请核实后重试！')
        time.sleep(3)
        return
    global card_info
    card_info = SqlData.search_del_card(user_id)
    card_int = len(card_info)
    if card_int == 0:
        print('该用户没有卡！')
        return
    print("共计卡量 [" + str(card_int) + "] 张。")
    text_name = str(username) + "_PENDING.txt"
    with open(text_name, 'a', encoding='utf-8') as f:
        f.write('卡号,卡总充值,注销差额,总退款,卡余额,PENDING交易金额,差额' + "\n")

    with open(str(username) + "_SETTLE.txt", 'a', encoding='utf-8') as f:
        f.write('卡号,卡总充值,注销差额,总退款,卡余额,SETTLE交易金额,差额' + "\n")

    print('开始校验.........')
    while True:
        loops_len = len(card_info)
        num = 200
        if loops_len < num:
            num = loops_len
        threads = []
        for i in range(num):
            card_one = card_info.pop()
            card_id = card_one.get('card_id')
            card_number = card_one.get('card_number')
            sum_top = SqlData.search_card_top(card_number)
            gap = SqlData.search_card_gap(card_number)
            sum_refund = SqlData.search_card_refund(card_number)
            t = threading.Thread(target=remain_trans, args=(card_number, card_id, username, sum_top, gap, sum_refund))
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
    main()


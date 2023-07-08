import datetime
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

    def search_delete_card(self):
        sql = "select card_info.card_number, card_info.card_id, card_info.user_id, user_trans.do_date from card_info join user_trans on card_info.card_number = user_trans.card_no where card_info.status='F' and user_trans.do_type='注销';"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['card_number'] = i[1]
            info_dict['card_id'] = i[0]
            info_dict['user_id'] = i[2]
            info_dict['do_date'] = i[3]
            info_list.append(info_dict)
        return info_list

    def search_check_card(self):
        sql = "SELECT card_no FROM check_card"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        info_list = list()
        for i in rows:
            info_list.append(i[0])
        return info_list

    def insert_check_card(self, card_no, sum_top, gap, sum_refund, settle_money, differ, user_id):
        sql = "INSERT INTO check_card(card_no, sum_top, gap, sum_refund, settle_money, differ, user_id) VALUES('{}',{},{},{},{},{},{})".format(card_no, sum_top, gap, sum_refund, settle_money, differ, user_id)
        try:
            self.cursor.execute(sql)
            self.connect.commit()
        except Exception as e:
            self.connect.rollback()


SqlData = SqlSvb()
svb = SVB()


def remain_trans(card_no, card_id, user_id):
    card_detail = svb.card_detail(card_id)
    if not card_detail:
        global card_info
        card_info.append({'card_id': card_id, 'card_number': card_no, 'user_id': user_id})
        return
    sum_top = SqlSvb().search_card_top(card_no)
    gap = SqlSvb().search_card_gap(card_no)
    sum_refund = SqlSvb().search_card_refund(card_no)
    remain = round(sum_top - sum_refund + gap, 2)

    clearings = card_detail.get('data').get('clearings')
    settle_money = 0
    for pend in clearings:
        trans_money = float(pend.get("billing_amount") / 100)
        settle_money += trans_money
    settle_money = round(settle_money, 2)
    if remain != settle_money:
        differ = round(remain - settle_money, 2)
        s = "{},{},{},{},{},{}".format(card_no, sum_top, gap, sum_refund, settle_money, differ)
        print(s)
    else:
        SqlData.insert_check_card(card_no, sum_top, gap, sum_refund, settle_money, 0, user_id)


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def datatime_to_timenum(tss1):
    timeArray = time.strptime(tss1, "%Y-%m-%d %H:%M:%S")
    timeStamp = int(time.mktime(timeArray))
    s = time.time() - timeStamp
    if s > 60 * 60 * 24 * 3:
        return True
    return False


def main():
    global card_info
    card_info = SqlData.search_delete_card()
    checked_card = SqlData.search_check_card()
    for card in card_info:
        do_time = card.get('do_date')
        card_number = card.get('card_number')
        res = datatime_to_timenum(do_time)
        if not res or card_number in checked_card:
            card_info.remove(card)

    if len(card_info) == 0:
        return
    while True:
        loops_len = len(card_info)
        num = 100
        if loops_len < num:
            num = loops_len
        threads = []
        for i in range(num):
            card_one = card_info.pop()
            card_id = card_one.get('card_id')
            card_number = card_one.get('card_number')
            user_id = card_one.get('user_id')
            t = threading.Thread(target=remain_trans, args=(card_number, card_id, user_id))
            threads.append(t)
        for i in threads:  # start threads 此处并不会执行线程，而是将任务分发到每个线程，同步线程。等同步完成后再开始执行start方法
            i.start()
        for i in threads:  # jion()方法等待线程完成
            i.join()
        if len(card_info) == 0:
            break


if __name__ == "__main__":
    main()


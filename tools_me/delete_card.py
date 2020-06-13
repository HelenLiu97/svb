import datetime
import time
from tools_me.mysql_tools import SqlData
from tools_me.svb import svb


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def search_or_delete(card_number, card_id, first_time, status, user_id):
    if first_time is None:
        card_detail = svb.card_detail(card_id)
        if not card_detail:
            return
        available_balance = card_detail.get('data').get('available_balance')
        SqlData.update_delete_first(xianzai_time(), float(available_balance/100), card_number)
    else:
        timeArray = time.strptime(str(first_time), "%Y-%m-%d %H:%M:%S")
        t = int(time.mktime(timeArray)) + 600
        if time.time() > t and status != 'T':
            card_detail = svb.card_detail(card_id)
            if not card_detail:
                return
            available_balance = card_detail.get('data').get('available_balance')
            available_balance = float(available_balance/100)
            authorizations = card_detail.get('data').get('authorizations')
            pend_money = 0
            for pend in authorizations:
                response = pend.get('issuer_response')
                mcc = pend.get('mcc')
                if "Decline" not in response and mcc != '7999':
                    trans_money = float(pend.get("billing_amount") / 100)
                    pend_money += trans_money
            sum_top = SqlData.search_card_top(card_number)
            sum_refund = SqlData.search_card_refund(card_number)
            remain = sum_top - sum_refund
            remain = round(remain, 2)
            pend_money = round(pend_money, 2)
            differ = 0
            if remain - pend_money < available_balance:
                theory_refund = round(remain-pend_money, 2)
                differ = round(theory_refund - available_balance, 2)
            res = svb.delete_card(card_id)
            if res:
                before_balance = SqlData.search_user_field('balance', user_id)
                update_balance = available_balance
                SqlData.update_balance(update_balance, user_id)
                balance = SqlData.search_user_field("balance", user_id)
                SqlData.update_card_info_card_no('status', 'F', card_number)
                n_time = xianzai_time()
                SqlData.insert_account_trans(n_time, '收入', "注销", card_number,
                                             update_balance, before_balance, balance, user_id)
                if differ != 0:
                    before_balance = SqlData.search_user_field('balance', user_id)
                    SqlData.update_balance(differ, user_id)
                    balance = SqlData.search_user_field("balance", user_id)
                    SqlData.insert_account_trans(n_time, '支出', "注销差额", card_number,
                                                 abs(differ), before_balance, balance, user_id)

                SqlData.update_delete_second(n_time, available_balance, card_number)
        else:
            print('没执行')
        return


if __name__ == "__main__":
    before_t = time.time()
    info_list = SqlData.search_delete_card_info()
    for i in info_list:
        if time.time() > before_t + 90:
            break
        card_number = i.get('card_number')
        card_id = i.get('card_id')
        first_time = i.get('first_time')
        first_remain = i.get('first_remain')
        second_time = i.get('second_time')
        second_remain = i.get('second_remain')
        status = i.get('status')
        user_id = i.get('user_id')
        search_or_delete(card_number, card_id, first_time, status, user_id)

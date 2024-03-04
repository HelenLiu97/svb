import datetime
import sys
# 服务器部署打开注释，加入到绝对路径中执行脚本
# sys.path.append(r'/home/admin/556338/svb-master/')
from tools_me.mysql_tools import SqlData
from tools_me.svb import svb
from config import logging


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def update_trans_balance():
    card_info = SqlData.search_card_info_admin("WHERE card_number='5563386245379665'")
    for i in card_info:
        print(i)
        card_id = i.get('card_id')
        user_id = i.get('user_id')
        card_number = i.get('card_no').strip()
        user_name = SqlData.search_user_field('name', user_id)
        n = 0
        res = {}
        while n <= 5:
            res = svb.card_detail(card_id)
            if res:
                break
            else:
                n += 1
                continue
        t = xianzai_time()
        if res:
            available_balance = res.get('data').get('available_balance')
            if available_balance < 0:
                total_card_amount = res.get('data').get('total_card_amount')
                amount = available_balance / 100
                update_money = total_card_amount + abs(available_balance)
                res, card_balance = svb.update_card(card_id, update_money)
                if res:
                    before_balance = SqlData.search_user_field('balance', user_id)
                    SqlData.update_balance(amount, user_id)
                    balance = SqlData.search_user_field("balance", user_id)
                    SqlData.insert_account_trans(t, '支出', "充值", card_number,
                                                 abs(amount), before_balance, balance, user_id)
                    available_balance = card_balance

            # SqlData.update_card_balance(int(available_balance/100), card_id)
            authorizations = res.get('data').get('authorizations')
            for c in authorizations:
                acquirer_ica = c.get('acquirer_ica')
                approval_code = c.get('approval_code')
                billing_amount = float(c.get('billing_amount')/100)
                billing_currency = c.get('billing_currency')
                issuer_response = c.get('issuer_response')
                mcc = c.get('mcc')
                mcc_description = c.get('mcc_description').replace("'", '*')
                merchant_amount = float(c.get('merchant_amount')/100)
                merchant_currency = c.get('merchant_currency')
                merchant_id = c.get('merchant_id')
                merchant_name = c.get('merchant_name')
                transaction_date_time = c.get('transaction_date_time')
                transaction_type = c.get('transaction_type')
                vcn_response = c.get('vcn_response')
                if 'Decline' in issuer_response or 'Decline' in vcn_response:
                    status = 'F'
                else:
                    status = 'T'
                SqlData.insert_card_trans(card_number, acquirer_ica, approval_code, billing_amount, billing_currency, issuer_response, mcc, mcc_description, merchant_amount, merchant_currency, merchant_id, merchant_name, transaction_date_time, transaction_type, vcn_response, card_id, status, user_name, user_id)

            clearings = res.get('data').get('clearings')
            for td in clearings:
                acquirer_ica = td.get("acquirer_ica")
                approval_code = td.get("approval_code")
                billing_amount = float(td.get("billing_amount") / 100)
                billing_currency = td.get("billing_currency")
                clearing_type = td.get("clearing_type")
                mcc = td.get("mcc")
                mcc_description = td.get("mcc_description")
                merchant_amount = float(float(td.get("merchant_amount")) / 100)
                merchant_currency = td.get("merchant_currency")
                merchant_id = td.get("merchant_id")
                merchant_name = td.get("merchant_name")
                exchange_rate = td.get("exchange_rate")
                authorization_date = td.get("authorization_date")
                settlement_date = td.get("settlement_date")
                SqlData.insert_card_trans_settle(card_number, acquirer_ica, approval_code, authorization_date, billing_amount,
                                 billing_currency,
                                 clearing_type, exchange_rate, mcc,
                                 mcc_description, merchant_amount, merchant_currency, merchant_id, merchant_name,
                                 settlement_date, card_id, user_name, user_id)
        else:
            logging.error('定时查询卡交易失败，card_id: ' + str(card_id))
    t = xianzai_time()
    SqlData.update_admin_field('up_remain_time', t)


if __name__ == "__main__":
    update_trans_balance()



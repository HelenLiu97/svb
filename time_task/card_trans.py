import datetime

from tools_me.mysql_tools import SqlData
from tools_me.svb import svb
from config import logging


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def update_trans_balance():
    card_info = SqlData.search_card_info_admin("WHERE card_status='F'")
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
        if res:
            available_balance = res.get('data').get('available_balance')
            # SqlData.update_card_balance(int(available_balance/100), card_id)
            authorizations = res.get('data').get('authorizations')
            for c in authorizations:
                acquirer_ica = c.get('acquirer_ica')
                approval_code = c.get('approval_code')
                billing_amount = float(c.get('billing_amount')/100)
                billing_currency = c.get('billing_currency')
                issuer_response = c.get('issuer_response')
                mcc = c.get('mcc')
                mcc_description = c.get('mcc_description')
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
        else:
            logging.error('定时查询卡交易失败，card_id: ' + str(card_id))
    t = xianzai_time()
    SqlData.update_admin_field('up_remain_time', t)


if __name__ == "__main__":
    update_trans_balance()



import datetime

from tools_me.mysql_tools import SqlData
from tools_me.svb import svb
import logging


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def update_trans_balance():
    card_info = SqlData.search_card_info_admin("WHERE status='T'")
    for i in card_info:
        card_id = i.get('card_id')
        card_number = i.get('card_no').strip()
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
            SqlData.update_card_balance(int(available_balance/100), card_id)
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
                SqlData.insert_card_trans(card_number, acquirer_ica, approval_code, billing_amount, billing_currency,
                                          issuer_response, mcc, mcc_description, merchant_amount, merchant_currency,
                                          merchant_id, merchant_name, transaction_date_time, transaction_type,
                                          vcn_response, card_id, status)

            clearings = res.get('data').get('clearings')
            for n in clearings:
                acquirer_ica = n.get('acquirer_ica')
                approval_code = n.get('approval_code')
                authorization_date = n.get('authorization_date')
                billing_amount = float(n.get('billing_amount') / 100)
                billing_currency = n.get('billing_currency')
                clearing_type = n.get('clearing_type')
                exchange_rate = n.get('exchange_rate')
                mcc = n.get('mcc')
                mcc_description = n.get('mcc_description')
                merchant_amount = float(n.get('merchant_amount') / 100)
                merchant_currency = n.get('merchant_currency')
                merchant_id = n.get('merchant_id')
                merchant_name = n.get('merchant_name')
                settlement_date = n.get('settlement_date')
                SqlData.insert_card_trans_settle(card_number, acquirer_ica, approval_code, authorization_date, billing_amount,
                                          billing_currency, clearing_type, exchange_rate, mcc, mcc_description, merchant_amount,
                                          merchant_currency, merchant_id, merchant_name, settlement_date, card_id)
        else:
            logging.error('定时查询卡交易失败，card_id: ' + str(card_id))
    t = xianzai_time()
    SqlData.update_admin_field('up_remain_time', t)


def handing_fee():
    # 收取交易币种不是USD的手续费
    res = SqlData.search_settle_trans()
    for i in res:
        merchant_currency = i.get('merchant_currency')
        info_id = i.get('info_id')
        if merchant_currency == 'USD':
            SqlData.update_settle_handing(0, info_id)
        else:
            card_number = i.get('card_number')
            billing_amount = i.get('billing_amount')
            # 计算手续费
            hand_money = round(billing_amount * 0.02, 2)
            # 查询卡的归属客户
            user_id = SqlData.search_card_field('user_id', card_number)
            # 查询扣费前的账户余额
            before_balance = SqlData.search_user_field('balance', user_id)
            # 扣除手续费
            SqlData.update_balance(-hand_money, user_id)
            # 扣费后的余额
            balance = SqlData.search_user_field('balance', user_id)
            # 插入扣费记录
            n_time = xianzai_time()
            SqlData.insert_account_trans(n_time, '支出', '手续费', card_number,
                                         hand_money, before_balance, balance, user_id)

            # 更新扣费金额，表示该交易已扣费
            SqlData.update_settle_handing(hand_money, info_id)


if __name__ == "__main__":
    update_trans_balance()
    # handing_fee()
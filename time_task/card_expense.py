"""
coding:utf-8
@software:PyCharm
@Time:2023/10/18 14:45
@Author:Helen
计算扣除非USD的消费手续费(2%)
"""
import datetime

from tools_me.mysql_tools import SqlData


def xianzai_time():
    now_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now_datetime


def main():
    data = SqlData.search_admin_card_trans_settle('')
    for d in data:
        clearing_type = d.get('clearing_type')
        expense = d.get('expense')
        merchant_currency = d.get('merchant_currency')
        billing_amount = d.get('billing_amount')
        user_id = d.get('user_id')
        _id = d.get('_id')
        card_number = d.get('card_number').strip()

        if clearing_type != 'CREDIT' and expense == 0 and merchant_currency != 'USD':
            money = round(float(billing_amount) * 0.02, 2)
            if money == 0:
                money = 0.01
            print(f'需要扣费: {money}')
            before_balance = SqlData.search_user_field('balance', user_id)
            SqlData.update_balance(-money, user_id)
            balance = SqlData.search_user_field("balance", user_id)
            SqlData.update_settle_handing(money, _id)
            SqlData.insert_account_trans(xianzai_time(), '支出', '手续费', card_number,
                                         money, before_balance, balance, user_id)


if __name__ == "__main__":
    main()

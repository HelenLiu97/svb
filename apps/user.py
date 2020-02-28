import json
import datetime
import logging
import operator
import re
import time

from config import cache
from tools_me.other_tools import xianzai_time, login_required, check_float, account_lock, get_nday_list
from tools_me.parameter import RET, MSG, TRANS_TYPE, DO_TYPE
from tools_me.redis_tools import RedisTool
from tools_me.remain import get_card_remain
from tools_me.img_code import createCodeImage
from tools_me.des_code import ImgCode
from tools_me.svb import svb
from . import user_blueprint
from flask import render_template, request, jsonify, session, g, redirect
from tools_me.mysql_tools import SqlData

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s', filename="error.log")


@user_blueprint.route('/del_vice/', methods=['GET'])
@login_required
@account_lock
def del_vice():
    vice_id = request.args.get('vice_id')
    SqlData.del_vice(int(vice_id))
    RedisTool.hash_del('svb_vice_auth', int(vice_id))
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@user_blueprint.route('/up_auth/', methods=['GET'])
@login_required
@account_lock
def up_auth():
    '处理正在使用的客户被删除的问题'
    vice_id = request.args.get('vice_id')
    field = request.args.get('field')
    check = request.args.get('check')
    value = request.args.get('value')
    if check:
        field_status = ''
        if check == "true":
            field_status = 'T'
        elif check == 'false':
            field_status = 'F'
        SqlData.update_vice_field(field, field_status, int(vice_id))
        res = SqlData.search_one_acc_vice(vice_id)
        RedisTool.hash_set('svb_vice_auth', res.get('vice_id'), res)
        return jsonify({'code': RET.OK, 'msg': MSG.OK})
    if value:
        if field == "v_account":
            if SqlData.search_value_in('vice_account', value, field):
                return jsonify({'code': RET.SERVERERROR, 'msg': '用户名已存在,请重新命名！'})
        SqlData.update_vice_field(field, value, int(vice_id))
        return jsonify({'code': RET.OK, 'msg': MSG.OK})


@user_blueprint.route('/vice_info/', methods=['GET', 'POST'])
@login_required
@account_lock
def vice_info():
    if request.method == 'GET':
        user_id = g.user_id
        res = SqlData.search_acc_vice(user_id)
        if res:
            resluts = dict()
            resluts['code'] = RET.OK
            resluts['msg'] = MSG.OK
            resluts['data'] = res
            return jsonify(resluts)
        else:
            return jsonify({"code": RET.OK, "msg": MSG.NODATA, "count": 0, "data": ""})


@user_blueprint.route('/update_vice/', methods=['GET', 'POST'])
@login_required
@account_lock
def update_vice():
    if request.method == 'GET':
        vice_id = g.vice_id
        if vice_id:
            return render_template('user/no_auth.html')
        return render_template('user/vice_acc_list.html')


@user_blueprint.route('/add_vice/', methods=['GET', 'POST'])
@login_required
@account_lock
def add_vice():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        return render_template('user/no_auth.html')
    if request.method == 'GET':
        return render_template('user/update_vice.html')
    if request.method == 'POST':
        user_id = g.user_id
        data = json.loads(request.form.get('data'))
        v_account = data.get('account')
        v_password = data.get('password')
        c_card = data.get('c_card')
        top_up = data.get('top_up')
        refund = data.get('refund')
        del_card = data.get('del_card')
        up_label = data.get('up_label')
        account = v_account.strip()
        password = v_password.strip()
        if len(account) < 6 or len(password) < 6:
            return jsonify({"code": RET.SERVERERROR, 'msg': '账号或密码长度小于6位！'})
        # 判断用户选择可哪些权限开启
        c_card_status = 'T' if c_card else 'F'
        top_up_status = 'T' if top_up else 'F'
        refund_status = 'T' if refund else 'F'
        del_card_status = 'T' if del_card else 'F'
        up_label_status = 'T' if up_label else 'F'
        res = SqlData.search_vice_count(user_id)
        # 判断是否已经添加子账号，已添加则更新
        if res < 3:
            if SqlData.search_value_in('vice_user', account, 'v_account'):
                return jsonify({'code': RET.SERVERERROR, 'msg': '用户名已存在,请重新命名！'})
            SqlData.insert_account_vice(account, password, c_card_status,  top_up_status,
                                        refund_status, del_card_status, up_label_status, user_id)
            vice_id = SqlData.search_vice_id(v_account)
            res = SqlData.search_one_acc_vice(vice_id)
            RedisTool.hash_set('svb_vice_auth', res.get('vice_id'), res)
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '您的账号已添加3个子账号，不可重复添加！'})


@user_blueprint.route('/refund/', methods=['POST'])
@login_required
@account_lock
def bento_refund():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
        if auth_dict is None:
            return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
        c_card = auth_dict.get('refund')
        if c_card == 'F':
            return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})

    # 参数获取
    data = request.form.get("data")
    card_number = request.form.get("card_number").strip()
    user_id = g.user_id

    # 金额的校验
    if "-" in str(data):
        return jsonify({"code": RET.SERVERERROR, 'msg': "请输入正确金额!"})
    if "." in str(data):
        if len(str(data).split(".")[1]) > 2:
            return jsonify({"code": RET.SERVERERROR, 'msg': "精度不大于两位小数!"})

    # 校验卡状态(注销无法更新)
    card_status = SqlData.search_one_card_status(card_number)
    if not card_status:
        return jsonify({'code': RET.SERVERERROR, 'msg': "该卡已注销,不支持此操作！"})

    # 查询卡余额，校验退款金额大小
    card_id = SqlData.search_card_field('card_id', card_number)
    card_detail = svb.card_detail(card_id)
    if not card_detail:
        return jsonify({"code": RET.SERVERERROR, 'msg': "网络繁忙,请稍后重试！"})
    available_balance = card_detail.get('data').get('available_balance')
    refund_money = float(data) * 100
    if refund_money >= available_balance:
        return jsonify({"code": RET.SERVERERROR, 'msg': "卡余额不足!当前卡余额:$" + str(available_balance/100)})

    # 减少当前额度则是减少余额
    total_card_amount = card_detail.get('data').get('total_card_amount')

    # 更新卡余额
    update_money = int(total_card_amount - refund_money)
    res, card_balance = svb.update_card(card_id, update_money)

    # 成功则更新账户余额
    if res:
        before_balance = SqlData.search_user_field('balance', user_id)
        SqlData.update_balance(float(data), user_id)
        balance = SqlData.search_user_field("balance", user_id)
        n_time = xianzai_time()
        SqlData.insert_account_trans(n_time, TRANS_TYPE.IN, "退款", card_number,
                                     float(data), before_balance, balance, user_id)

        return jsonify({"code": RET.OK, "msg": '退款成功！当前卡余额:$'+str(card_balance/100)})
    else:
        return jsonify({"code": RET.SERVERERROR, 'msg': "网络繁忙,请稍后重试！"})


# svb在交易信息需要爬取
@user_blueprint.route('/all_trans/', methods=['GET'])
@login_required
@account_lock
def all_trans():
    page = request.args.get("page")
    limit = request.args.get("limit")

    # 客户名
    acc_name = request.args.get("acc_name")
    # 卡的名字
    order_num = request.args.get("order_num")
    # 时间范围
    time_range = request.args.get("time_range")
    # 操作状态
    trans_status = request.args.get("trans_status")

    user_name = g.user_name
    # data = SqlDataNative.one_bento_alltrans(alias=user_name)
    data=[]
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(data) == 0:
        results["MSG"] = MSG.NODATA
        return jsonify(results)
    args_list = []
    new_data = []
    if acc_name:
        args_list.append(acc_name)
    if order_num:
        args_list.append(order_num)
    if trans_status:
        args_list.append(trans_status)

    if args_list and time_range == "":
        for d in data:
            if set(args_list) < set(d.values()):
                new_data.append(d)
    elif args_list and time_range != "":
        min_time = time_range.split(' - ')[0] + ' 00:00:00'
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        min_tuple = datetime.datetime.strptime(min_time, '%Y-%m-%d %H:%M:%S')
        max_tuple = datetime.datetime.strptime(max_time, '%Y-%m-%d %H:%M:%S')
        for d in data:
            dat = datetime.datetime.strptime(d.get("date"), '%Y-%m-%d %H:%M:%S')
            if (min_tuple < dat and max_tuple > dat) and set(args_list) < set(d.values()):
                new_data.append(d)
    elif time_range and len(args_list) == 0:
        min_time = time_range.split(' - ')[0] + ' 00:00:00'
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        min_tuple = datetime.datetime.strptime(min_time, '%Y-%m-%d %H:%M:%S')
        max_tuple = datetime.datetime.strptime(max_time, '%Y-%m-%d %H:%M:%S')
        for d in data:
            dat = datetime.datetime.strptime(d.get("date"), '%Y-%m-%d %H:%M:%S')
            if min_tuple < dat and max_tuple > dat:
                new_data.append(d)

    page_list = list()
    if new_data:
        data = sorted(new_data, key=operator.itemgetter("date"))
    data = sorted(data, key=operator.itemgetter("date"))
    data = list(reversed(data))
    for i in range(0, len(data), int(limit)):
        page_list.append(data[i: i + int(limit)])
    results["data"] = page_list[int(page) - 1]
    results["count"] = len(data)
    # results = {"code": RET.OK, "msg": MSG.OK, "count": len(data), "data": page_list[int(page)-1]}
    return jsonify(results)


@user_blueprint.route('/card_label/', methods=['GET', 'POST'])
@login_required
def change_card_name():
    '''
    更改卡姓名和标签信息
    :return:
    '''
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
        if auth_dict is None:
            return render_template('user/no_auth.html')
        c_card = auth_dict.get('refund')
        if c_card == 'F':
            return render_template('user/no_auth.html')

    if request.method == 'GET':
        card_number = request.args.get('card_number')
        context = dict()
        context['card_number'] = card_number
        return render_template('user/card_label.html', **context)
    if request.method == 'POST':
        try:
            data = json.loads(request.form.get('data'))
            card_number = data.get('card_number')
            card_label = data.get('card_label')
            card_number = card_number.strip()
            if card_label:
                SqlData.update_card_info_card_no('label', card_label, card_number)
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@user_blueprint.route('/card_remain/', methods=['GET'])
@account_lock
def card_remain():
    results = dict()
    try:
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        data = request.args.get('data')
        data = json.loads(data)
        info = get_card_remain(data)
        results['data'] = info
        results['count'] = len(info)
        return results
    except Exception as e:
        logging.error(str(e))
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@user_blueprint.route('/user_top/')
@login_required
def user_top_log():
    return render_template('user/user_top.html')


@user_blueprint.route('/pay_history/')
@login_required
def user_trans():
    return render_template('user/user_trans.html')


@user_blueprint.route('/account_trans/', methods=['GET'])
@login_required
@account_lock
def account_trans():
    page = request.args.get('page')
    limit = request.args.get('limit')

    time_range = request.args.get('time_range')
    card_num = request.args.get('card_num')
    do_type = request.args.get('do_type')
    trans_type = request.args.get('trans_type')
    time_sql = ""
    card_sql = ""
    do_sql = ""
    trans_sql = ""
    if time_range:
        min_time = time_range.split(' - ')[0]
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        time_sql = "AND do_date BETWEEN " + "'" + min_time + "'" + " and " + "'" + max_time + "'"
    if card_num:
        card_sql = "AND card_no LIKE '%{}%'".format(card_num)
    if do_type:
        do_sql = "AND do_type='" + do_type + "'"
    if trans_type:
        trans_sql = "AND trans_type='" + trans_type + "'"

    user_id = g.user_id
    task_info = SqlData.search_account_trans(user_id, card_sql, time_sql, type_sql=do_sql, do_sql=trans_sql)

    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return jsonify(results)
    page_list = list()
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return jsonify(results)


@user_blueprint.route('/card_delete/', methods=['DELETE'])
@login_required
@account_lock
def card_delete():
    if request.method == "DELETE":

        # 判断是否是子账号用户
        vice_id = g.vice_id
        if vice_id:
            auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
            if auth_dict is None:
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
            c_card = auth_dict.get('refund')
            if c_card == 'F':
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})

        card_number = request.args.get('card_number')
        card_status = SqlData.search_one_card_status(card_number)
        if card_status:
            card_id = SqlData.search_card_field('card_id', card_number)
            card_detail = svb.card_detail(card_id)
            if not card_detail:
                return jsonify({'code': RET.SERVERERROR, 'msg': '网络繁忙,请稍后重试！'})
            available_balance = card_detail.get('data').get('available_balance')
            res = svb.delete_card(card_id)
            if res:
                user_id = g.user_id
                before_balance = SqlData.search_user_field('balance', user_id)
                update_balance = float(available_balance/100)
                SqlData.update_balance(update_balance, user_id)
                balance = SqlData.search_user_field("balance", user_id)
                SqlData.update_card_info_card_no('status', 'F', card_number)
                n_time = xianzai_time()
                SqlData.insert_account_trans(n_time, TRANS_TYPE.IN, "注销", card_number,
                                             update_balance, before_balance, balance, user_id)

                return jsonify({"code": RET.OK, "msg": '注销成功！退回金额:$' + str(update_balance)})

        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '该卡已注销！'})


# 批量充值
@user_blueprint.route('/batch/', methods=['POST'])
@login_required
@account_lock
def card_batch():
    if request.method == 'POST':
        try:
            user_id = g.user_id
            money = request.form.get('money')
            card_info = json.loads(request.form.get('card_info'))
            # 校验充值金额是否为小数
            if not check_float(money):
                results = {"code": RET.SERVERERROR, "msg": "充值金额不能为小数!"}
                return jsonify(results)
            sum_out_money = len(card_info) * int(money)
            user_data = SqlData.search_user_index(user_id)
            before_balance = user_data.get('balance')

            # 校验账户余额是否充足
            if sum_out_money > before_balance:
                results = {"code": RET.SERVERERROR, "msg": "本次消费金额:" + str(sum_out_money) + ",账号余额不足!"}
                return jsonify(results)

            # 判断充值的卡中是否包含注销的卡
            logout_cards = SqlData.search_logout_card(user_id)
            card_list = list(card_info.keys())
            for i in card_list:
                if i.strip() in logout_cards:
                    results = {"code": RET.SERVERERROR, "msg": "本次充值中卡号:" + i + "。为注销卡,请排除注销卡后重试。"}
                    return jsonify(results)

            success_list = list()
            fail_list = list()
            for card in card_list:
                card_number = card.strip()
                card_id = SqlData.search_card_field('card_id', card_number)
                card_detail = svb.card_detail(card_id)
                if card_detail:
                    available_balance = card_detail.get('data').get('total_card_amount')
                    now_balance = available_balance + int(money) * 100
                    res, card_balance = svb.update_card(card_id, now_balance)
                    if res:
                        top_money = int(money)
                        top_money_do_money = top_money - top_money * 2
                        SqlData.update_balance(top_money_do_money, user_id)
                        n_time = xianzai_time()
                        balance = SqlData.search_user_field('balance', user_id)
                        SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.TOP_UP, card_number,
                                                     top_money, before_balance, balance, user_id)
                        success_list.append(card_number)
                    fail_list.append(card_number)
                else:
                    fail_list.append(card_number)
            balance = SqlData.search_user_field('balance', user_id)
            if len(success_list) == len(card_list):
                msg = "批量充值成功！当前账户余额：" + str(balance)
            else:
                s = ""
                for card_number in fail_list:
                    s += card_number + ", "
                msg = "部分充值成功！以下卡号充值失败：" + s + " 请重试！当前账户余额：" + str(balance)
            return jsonify({'code': RET.OK, 'msg': msg})
        except Exception as e:
            logging.error("批量充值异常：" + str(e))
            return jsonify({'code': RET.SERVERERROR, "msg": '网络超时，请稍后重试！'})


# 充值
@user_blueprint.route('/card_top/', methods=['GET', 'POST'])
@login_required
@account_lock
def top_up():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
        if auth_dict is None:
            return render_template('user/no_auth.html')
        c_card = auth_dict.get('top_up')
        if c_card == 'F':
            return render_template('user/no_auth.html')
    if request.method == 'GET':
        card_number = request.args.get('card_number')
        context = dict()
        context['card_number'] = card_number
        return render_template('user/card_top.html', **context)
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        user_id = g.user_id
        card_number = request.args.get('card_number')
        top_money = data.get('top_money')
        user_data = SqlData.search_user_index(user_id)
        before_balance = user_data.get('balance')
        if not check_float(top_money):
            results = {"code": RET.SERVERERROR, "msg": "充值金额不能为小数!"}
            return jsonify(results)
        if int(top_money) > before_balance:
            results = {"code": RET.SERVERERROR, "msg": "本次消费金额:" + str(top_money) + ",账号余额不足!"}
            return jsonify(results)
        card_status = SqlData.search_one_card_status(card_number)
        if not card_status:
            return jsonify({'code': RET.SERVERERROR, 'msg': "该卡已注销,不支持此操作！"})
        card_id = SqlData.search_card_field('card_id', card_number)
        card_detail = svb.card_detail(card_id)
        if card_detail:
            available_balance = card_detail.get('data').get('total_card_amount')
            now_balance = available_balance + int(top_money) * 100
            res, card_balance = svb.update_card(card_id, now_balance)
            if res:
                top_money = int(top_money)
                top_money_do_money = top_money - top_money * 2
                SqlData.update_balance(top_money_do_money, user_id)
                n_time = xianzai_time()
                balance = SqlData.search_user_field('balance', user_id)
                SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.TOP_UP, card_number,
                                             top_money, before_balance, balance, user_id)
                return jsonify({'code': RET.OK, 'msg': '充值成功！账户余额:$ ' + str(balance)+",卡余额:$ " + str(card_balance/100)})
            return jsonify({'code': RET.SERVERERROR, 'msg': '网络繁忙,请稍后重试！'})
        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '网络繁忙,请稍后重试！'})


@user_blueprint.route('/create_card/', methods=['GET', 'POST'])
@login_required
@account_lock
def create_card():
    if request.method == 'GET':
        user_id = g.user_id
        min_top = SqlData.search_user_field('min_top', user_id)
        create_price = SqlData.search_user_field('create_price', user_id)
        context = dict()
        context['min_top'] = min_top
        context['create_price'] = create_price
        return render_template('user/create_card.html', **context)
    if request.method == 'POST':
        # 判断是否是子账号用户
        vice_id = g.vice_id
        if vice_id:
            auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
            if auth_dict is None:
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
            c_card = auth_dict.get('c_card')
            if c_card == 'F':
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
        data = json.loads(request.form.get('data'))
        top_money = data.get('top_money')
        label = data.get('label')
        card_num = data.get('card_num')
        user_id = g.user_id
        user_data = SqlData.search_user_index(user_id)
        create_price = user_data.get('create_card')
        min_top = user_data.get('min_top')
        max_top = user_data.get('max_top')
        balance = user_data.get('balance')

        card_num = int(card_num)
        if card_num > 10:
            results = {"code": RET.SERVERERROR, "msg": "批量开卡数量不得超过10张!"}
            return jsonify(results)

        if not check_float(top_money):
            results = {"code": RET.SERVERERROR, "msg": "充值金额不能为小数!"}
            return jsonify(results)

        # 本次开卡需要的费用,计算余额是否充足
        money_all = (int(top_money) + create_price) * card_num
        if money_all > balance:
            results = {"code": RET.SERVERERROR, "msg": "本次消费金额:" + str(money_all) + ",账号余额不足!"}
            return jsonify(results)

        # 计算充值金额是否在允许范围
        # if not min_top <= int(top_money) <= max_top:
        if not min_top <= int(top_money):
            results = {"code": RET.SERVERERROR, "msg": "充值金额不在允许范围内!"}
            return jsonify(results)
        # 该处修改开卡
        try:
            data_list = []
            cents = int(top_money) * 100
            for i in range(card_num):
                data = svb.create_card(cents)
                if data:
                    # 开卡费用
                    n_time = xianzai_time()
                    card_number = data.get('card_number')
                    cvc = data.get('cvc')
                    expiry = data.get('expiry')
                    card_id = data.get('card_id')
                    last4 = data.get('last4')
                    valid_starting_on = data.get('valid_start_on')
                    valid_ending_on = data.get('valid_end_on')

                    # 插入卡信息
                    SqlData.insert_card(card_number, cvc, expiry, card_id, last4, valid_starting_on, valid_ending_on, label, 'T', int(top_money), user_id)

                    # 扣去开卡费用
                    before_balance = SqlData.search_user_field('balance', user_id)
                    create_price_do_money = float(create_price) - float(create_price) * 2
                    SqlData.update_balance(create_price_do_money, user_id)
                    balance = SqlData.search_user_field("balance", user_id)
                    # balance = before_balance - create_price
                    SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.CREATE_CARD, card_number,
                                                 create_price, before_balance, balance, user_id)

                    # 扣去充值费用
                    before_balance = SqlData.search_user_field('balance', user_id)
                    top_money = int(top_money)
                    top_money_do_money = top_money - top_money * 2
                    SqlData.update_balance(top_money_do_money, user_id)
                    balance = SqlData.search_user_field("balance", user_id)
                    n_time = xianzai_time()
                    SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.TOP_UP, card_number,
                                                 top_money, before_balance, balance, user_id)
                    data_list.append(card_num)
            if len(data_list) < 1:
                code = RET.SERVERERROR
            else:
                code = RET.OK
            return jsonify({"code": code, "msg": "成功开卡" + str(len(data_list)) + "张! 账户余额为: $"+str(balance)})

        except Exception as e:
            logging.error(str(e))
            return jsonify({"code": RET.SERVERERROR, "msg": "网络繁忙, 开卡失败, 请稍后再试"})


@user_blueprint.route('/top_history/', methods=['GET'])
@login_required
@account_lock
def top_history():
    page = request.args.get('page')
    limit = request.args.get('limit')
    user_id = g.user_id
    task_info = SqlData.search_top_history_acc(user_id)
    task_info = sorted(task_info, key=operator.itemgetter('time'))
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return jsonify(results)


@user_blueprint.route('/card_table/', methods=['GET'])
@login_required
def card_table():
    return render_template('user/card_table.html')


@user_blueprint.route('/password/', methods=['GET', 'POST'])
@login_required
def user_password():
    user_id = g.user_id
    vice_id = g.vice_id
    if user_id and not vice_id:
        password = SqlData.search_user_field('password', user_id)
        return jsonify({'code': RET.OK, 'msg': password})
    else:
        password = SqlData.search_one_acc_vice(vice_id).get('v_password')
        return jsonify({'code': RET.OK, 'msg': password})


@user_blueprint.route('/', methods=['GET'])
@login_required
@account_lock
def account_html():
    user_name = g.user_name
    if not user_name:
        return redirect('/user/logout/')
    context = dict()
    context['user_name'] = user_name
    return render_template('user/UserIndex.html', **context)


@user_blueprint.route('/change_phone', methods=['GET'])
@login_required
@account_lock
def change_phone():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        return jsonify({'code': RET.SERVERERROR, 'msg': '您没有权限操作！请切换主账号后重试！'})
    user_id = g.user_id
    phone_num = request.args.get('phone_num')
    results = dict()
    try:
        SqlData.update_user_field('phone_num', phone_num, user_id)
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


# 卡的交易记录
@user_blueprint.route('/one_card_detail', methods=['GET'])
@account_lock
@login_required
def one_detail():
    try:
        context = dict()
        card_number = request.args.get('card_number')
        card_status = SqlData.search_one_card_status(card_number)
        card_id = SqlData.search_card_field('card_id', card_number)
        card_detail = svb.card_detail(card_id)
        if not card_detail:
            return render_template('user/404.html')
        if card_status:
            available_balance = card_detail.get('data').get('available_balance')
            context['available_balance'] = available_balance/100
            context['card_status'] = "正常"
        else:
            context['available_balance'] = 0
            context['card_status'] = "已注销"
        info_list = list()
        authorizations = card_detail.get('data').get('authorizations')
        for td in authorizations:
            info_list.append({
                "acquirer_ica": td.get("acquirer_ica"),
                "approval_code": td.get("approval_code"),
                "billing_amount": float(td.get("billing_amount")/100),
                "billing_currency": td.get("billing_currency"),
                "issuer_response": td.get("issuer_response"),
                "mcc": td.get("mcc"),
                "mcc_description": td.get("mcc_description"),
                "merchant_amount": float(td.get("merchant_amount")/100),
                "merchant_currency": td.get("merchant_currency"),
                "merchant_id": td.get("merchant_id"),
                "merchant_name": td.get("merchant_name"),
                "transaction_date_time": td.get("transaction_date_time"),
                "vcn_response": td.get("vcn_response"),
            })
        context['pay_list'] = info_list
        return render_template('user/card_detail.html', **context)
    except Exception as e:
        logging.error((str(e)))
        return render_template('user/404.html')


@user_blueprint.route('/push_log/', methods=['GET'])
@login_required
def push_log():

    '''
    卡交易记录接口
    '''

    try:
        user_id = g.user_id
        page = request.args.get('page')
        limit = request.args.get('limit')
        card_number = request.args.get('card_no')
        trans_status = request.args.get('trans_status')

        if trans_status and card_number:
            sql = " AND card_trans.card_number LIKE '%{}%' AND card_trans.status = '{}'".format(card_number, trans_status)
        elif card_number:
            sql = " AND card_trans.card_number LIKE '%{}%'".format(card_number)
        elif trans_status:
            sql = " AND card_trans.status ='{}'".format(trans_status)
        else:
            sql = ''
        results = dict()
        results['msg'] = MSG.OK
        results['code'] = RET.OK
        info = SqlData.search_card_trans(user_id, sql)
        if not info:
            results['msg'] = MSG.NODATA
            return jsonify(results)
        task_info = info
        page_list = list()
        # task_info = list(reversed(task_info))
        for i in range(0, len(task_info), int(limit)):
            page_list.append(task_info[i:i + int(limit)])
        results['data'] = page_list[int(page) - 1]
        results['count'] = len(task_info)
        return jsonify(results)
    except Exception as e:
        logging.error('查询卡交易推送失败:' + str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@user_blueprint.route('/card_trans/', methods=['GET'])
@login_required
def card_trans():
    return render_template('user/card_trans.html')


@user_blueprint.route('/change_detail', methods=['GET'])
@login_required
@account_lock
def change_detail():
    return render_template('user/edit_account.html')


# 余额
@user_blueprint.route('/card_info/', methods=['GET'])
@login_required
@account_lock
def card_info():
    try:
        limit = request.args.get('limit')
        page = request.args.get('page')
        card_num = request.args.get('card_num')
        label = request.args.get('label')
        card_status = request.args.get('card_status')
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        user_id = g.user_id

        if card_status == "hide":
            status = "F"
        else:
            status = ''

        if not card_num and not label:
            data = SqlData.search_card_info(user_id, status, '', '')
            if len(data) == 0:
                results['code'] = RET.SERVERERROR
                results['msg'] = MSG.NODATA
                return jsonify(results)
            data = sorted(data, key=operator.itemgetter('id'))
        else:
            card_sql = ''
            if card_num:
                card_sql = "AND card_number LIKE '%" + card_num + "%'"
            label_sql = ''
            if label:
                label_sql = "AND label LIKE '%" + label + "%'"
            data = SqlData.search_card_info(user_id, status, card_sql, label_sql)
            if len(data) == 0:
                results['code'] = RET.SERVERERROR
                results['msg'] = MSG.NODATA
                return jsonify(results)
        page_list = list()
        info = list(reversed(data))
        for i in range(0, len(info), int(limit)):
            page_list.append(info[i:i + int(limit)])
        data = page_list[int(page) - 1]
        results['data'] = data
        results['count'] = len(info)
        return jsonify(results)
    except Exception as e:
        logging.error(e)
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@user_blueprint.route('/edit_user', methods=['GET'])
@login_required
@account_lock
def ch_pass_html():
    vice_id = g.vice_id
    if vice_id:
        return render_template('user/no_auth.html')
    return render_template('user/edit_user.html')


@user_blueprint.route('/change_pass/', methods=["GET", "POST"])
@login_required
@account_lock
def change_pass():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        return render_template('user/no_auth.html')

    if request.method == 'GET':
        user_name = g.user_name
        context = dict()
        context['user_name'] = user_name
        return render_template('user/changePwd.html', **context)
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        old_pass = data.get('old_pass')
        new_pass_one = data.get('new_pass_one')
        new_pass_two = data.get('new_pass_two')
        user_id = g.user_id
        pass_word = SqlData.search_user_field('password', user_id)
        results = {'code': RET.OK, 'msg': MSG.OK}
        res = re.match('(?!.*\s)(?!^[\u4e00-\u9fa5]+$)(?!^[0-9]+$)(?!^[A-z]+$)(?!^[^A-z0-9]+$)^.{8,16}$', new_pass_one)
        if not res:
            results['code'] = RET.SERVERERROR
            results['msg'] = '密码不符合要求！'
            return jsonify(results)
        if not (old_pass == pass_word):
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.PSWDERROR
            return jsonify(results)
        if not (new_pass_one == new_pass_two):
            results['code'] = RET.SERVERERROR
            results['msg'] = '两次密码输入不一致！'
            return jsonify(results)
        try:
            SqlData.update_user_field('password', new_pass_one, g.user_id)
            session.pop('user_id')
            session.pop('name')
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


@user_blueprint.route('/user_info', methods=['GET'])
@login_required
@account_lock
def user_info():
    user_name = g.user_name
    user_id = g.user_id
    dict_info = SqlData.search_user_detail(user_id)
    account = dict_info.get('account')
    phone_num = dict_info.get('phone_num')
    balance = dict_info.get('balance')
    context = {
        'user_name': user_name,
        'account': account,
        'balance': balance,
        'phone_num': phone_num,
    }
    return render_template('user/user_info.html', **context)


@user_blueprint.route('/line_chart/')
@login_required
def line_chart():
    # 展示近三十天开卡数量
    day_num = 30
    day_list = get_nday_list(day_num)
    user_id = g.user_id
    sum_day_money = list()
    sum_day_card = list()
    for d in day_list:
        start_t = d + " 00:00:00"
        end_t = d + " 23:59:59"
        day_money = SqlData.search_trans_money(start_t, end_t, user_sql='AND user_id={}'.format(user_id))
        if not day_money:
            day_money = 0
        sum_day_money.append(day_money)
        sql = "WHERE do_type='开卡' AND do_date BETWEEN '{}' AND '{}' AND user_id={}".format(start_t, end_t, user_id)
        card_num = SqlData.search_value_count('user_trans', sql=sql)
        sum_day_card.append(card_num)
    money_dict = {'name': '充值金额', 'type': 'column', 'yAxis': 1, 'data': sum_day_money, 'tooltip': {'valueSuffix': ' $'}}
    card_dict = {'name': '开卡数量', 'type': 'spline', 'data': sum_day_card, 'tooltip': {'valueSuffix': ' 张'}}
    # 以下是数据结构
    '''
    [{
            name: '充值金额',
            type: 'column',
            yAxis: 1,
            data: [49.9, 71.5, 106.4, 129.2, 144.0, 176.0, 135.6, 148.5, 216.4, 194.1, 95.6, 54.4,980,98,98],
            tooltip: {
                valueSuffix: ' $'
            }
        }, {
            name: '开卡数量',
            type: 'spline',
            data: [7.0, 6.9, 9.5, 14.5, 18.2, 21.5, 25.2, 26.5, 23.3, 18.3, 13.9, 9.6],
            tooltip: {
                valueSuffix: ' 张'
            }
        }]'''
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    results['data'] = [money_dict, card_dict]
    results['xAx'] = day_list
    return jsonify(results)


@user_blueprint.route('/notice/', methods=['GET'])
@login_required
def notice():
    notice = SqlData.search_admin_field('notice')
    note_list = notice.split("!@#")
    note = note_list[0]
    date = note_list[1]
    s = '<html><body><div style="padding-left:20px; color:red;">公告时间：{}</div><div style="padding:15px 20px; text-align:justify; line-height: 22px; text-indent:2em;">' \
        '<p class="layui-red">{}</p></div></body></html>'.format(date, note)
    return s


@user_blueprint.route('/main/', methods=['GET'])
@login_required
def user_main():
    user_id = g.user_id
    balance = SqlData.search_user_field('balance', user_id)
    # 支出中有部分退款产生，所以所有支出减去退款才是真实支出
    sum_out_money = SqlData.search_trans_sum(user_id) - SqlData.search_income_money(user_id)
    sum_top_money = SqlData.search_user_field('sum_balance', user_id)
    card_num = SqlData.search_card_status("WHERE user_id={}".format(user_id))
    vice_num = SqlData.search_vice_count(user_id)
    notice = SqlData.search_admin_field('notice')
    up_remain_time = SqlData.search_admin_field('up_remain_time')
    card_remain = SqlData.search_sum_card_balance(user_id)
    update_t = up_remain_time
    context = dict()
    context['balance'] = balance
    context['sum_out_money'] = sum_out_money
    context['sum_top_money'] = sum_top_money
    context['card_num'] = card_num
    context['card_remain'] = card_remain
    context['update_t'] = update_t
    context['vice_num'] = vice_num
    context['notice'] = notice
    return render_template('user/main.html', **context)


@user_blueprint.route('/logout/', methods=['GET'])
@login_required
def logout():
    session.pop('user_id')
    session.pop('name')
    session.pop('vice_id')
    return redirect('/user/login/')


@user_blueprint.route('/img_code/', methods=['GET'])
def img_code():
    try:
        height = request.args.get('height')
        code, img_str = createCodeImage(height=int(height))
        string = ImgCode().jiami(code)
        return jsonify({'code': RET.OK, 'data': {'string': string, 'src': img_str}})
    except Exception as e:
        logging.error(str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@user_blueprint.route('/material/', methods=['GET', 'POST'])
def material():
    if request.method == 'GET':
        '''完善资料的HTML界面'''
        user_name = request.args.get('name')
        if not user_name:
            return redirect('/user/')
        context = dict()
        context['user_name'] = user_name
        return render_template('user/material.html', **context)
    if request.method == 'POST':

        '''新用户的首次登录更换密码和完善电话信息'''

        data = json.loads(request.form.get('data'))
        pass_1 = data.get('pass_1')
        pass_2 = data.get('pass_2')
        phone = data.get('phone')
        user_acc = data.get('user_name')
        if not all([pass_1, pass_2, phone]):
            return jsonify({'code': RET.SERVERERROR, 'msg': '必填项不能为空！'})
        if pass_1 != pass_2:
            return jsonify({'code': RET.SERVERERROR, 'msg': '两次输入密码不一致！'})
        res = re.match('(?!.*\s)(?!^[\u4e00-\u9fa5]+$)(?!^[0-9]+$)(?!^[A-z]+$)(?!^[^A-z0-9]+$)^.{8,16}$', pass_1)
        if not res:
            return jsonify({'code': RET.SERVERERROR, 'msg': '密码不符合要求！'})
        res_phone = re.match('^1(3[0-9]|4[5,7]|5[0-9]|6[2,5,6,7]|7[0,1,7,8]|8[0-9]|9[1,8,9])\d{8}$', phone)
        if not res_phone:
            return jsonify({'code': RET.SERVERERROR, 'msg': '请输入规范手机号码！'})
        try:
            user_id = SqlData.search_user_id(user_acc)
            SqlData.update_user_field('password', pass_1, user_id)
            SqlData.update_user_field('phone_num', phone, user_id)
            user_name = SqlData.search_user_field('name', user_id)
            now_time = xianzai_time()
            SqlData.update_user_field('last_login_time', now_time, user_id)
            session['user_id'] = user_id
            session['name'] = user_name
            session['vice_id'] = None
            session.permanent = True
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'MSG': MSG.SERVERERROR})


@user_blueprint.route('/login/', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        str_data, img = createCodeImage(height=38)
        context = dict()
        context['img'] = img
        context['code'] = ImgCode().jiami(str_data)
        return render_template('user/login.html', **context)

    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        user_name = data.get('user_name')
        user_pass = data.get('pass_word')
        image_real = data.get('image_real')
        image_code = data.get('image_code')
        cus_status = data.get('cus_status')
        results = {'code': RET.OK, 'msg': MSG.OK}
        try:
            img_code = ImgCode().jiemi(image_real)
            if image_code.lower() != img_code.lower():
                results['code'] = RET.SERVERERROR
                results['msg'] = '验证码错误！'
                return jsonify(results)
            if cus_status == "main":
                user_data = SqlData.search_user_info(user_name)
                if user_data:
                    user_id = user_data.get('user_id')
                    pass_word = user_data.get('password')
                    name = user_data.get('name')
                    if user_pass == pass_word:
                        last_login_time = SqlData.search_user_field('last_login_time', user_id)
                        if not last_login_time:
                            return jsonify({'code': 307, 'msg': MSG.OK})
                        now_time = xianzai_time()
                        SqlData.update_user_field('last_login_time', now_time, user_id)
                        session['user_id'] = user_id
                        session['name'] = name
                        session['vice_id'] = None
                        session.permanent = True
                        return jsonify(results)
                    else:
                        results['code'] = RET.SERVERERROR
                        results['msg'] = MSG.PSWDERROR
                        return jsonify(results)
                else:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = MSG.PSWDERROR
                    return jsonify(results)
            if cus_status == 'vice':
                user_data = SqlData.search_user_vice_info(user_name)
                user_id = user_data.get('user_id')
                password = user_data.get('password')
                vice_id = user_data.get('vice_id')
                if password == user_pass:
                    # 存储到缓存
                    session['user_id'] = user_id
                    session['name'] = user_name
                    session['vice_id'] = vice_id
                    session.permanent = True
                    # 存储子子账号操作权限到redis
                    res = SqlData.search_one_acc_vice(vice_id)
                    RedisTool.hash_set('svb_vice_auth', res.get('vice_id'), res)
                    return jsonify(results)
                else:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = MSG.PSWDERROR
                    return jsonify(results)

        except Exception as e:
            logging.error(str(e))
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.DATAERROR
            return jsonify(results)

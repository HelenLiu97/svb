import json
import time
import re
import logging
from flask import render_template, request, jsonify, redirect, session
from tools_me.mysql_tools import SqlData
from tools_me.other_tools import sum_code, xianzai_time, verify_required
from tools_me.parameter import RET, MSG
from tools_me.send_sms.send_sms import CCP
from . import verify_pay_blueprint


@verify_pay_blueprint.route('/del_log/', methods=['GET'])
@verify_required
def del_log():
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    limit = request.args.get('limit')
    page = request.args.get('page')
    status = request.args.get('status')
    data = SqlData.search_pay_log(status)
    if not data:
        results['msg'] = MSG.NODATA
        return jsonify(results)
    info = list(reversed(data))
    page_list = list()
    for i in range(0, len(info), int(limit)):
        page_list.append(info[i:i + int(limit)])
    info_list = page_list[int(page) - 1]

    # 查询当次充值时的账号总充值金额
    new_list = list()
    for o in info_list:
        x_time = o.get('ver_time')
        user_id = o.get('cus_id')
        sum_money = SqlData.search_time_sum_money(x_time, user_id)
        o['sum_balance'] = round(sum_money, 2)
        new_list.append(o)

    results['data'] = new_list
    results['count'] = len(data)
    return jsonify(results)


@verify_pay_blueprint.route('/logout/', methods=['GET'])
def logout():
    session.pop('user_name')
    session.pop('user_id')
    return redirect('/verify_pay/')


@verify_pay_blueprint.route('/login/', methods=['GET', 'POST'])
def verify_login():
    if request.method == 'GET':
        return render_template('verify_pay/login.html')
    if request.method == 'POST':
        data = request.values.to_dict()
        user_name = data.get('username')
        pass_word = data.get('password')
        data = SqlData.search_verify_login(user_name, pass_word)
        if data:
            session['user_name'] = data.get('user_name')
            session['user_id'] = data.get('user_id')
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '账号或密码错误!'})


@verify_pay_blueprint.route('/')
@verify_required
def verify_index():
    user_name = session.get('user_name')
    context = dict()
    context['user_name'] = user_name
    return render_template('verify_pay/index.html', **context)


@verify_pay_blueprint.route('/pay_log/', methods=['GET'])
@verify_required
def pay_log():
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    limit = request.args.get('limit')
    page = request.args.get('page')
    status = request.args.get('status')
    data = SqlData.search_pay_log(status)
    if not data:
        results['msg'] = MSG.NODATA
        return jsonify(results)
    info = list(reversed(data))
    page_list = list()
    for i in range(0, len(info), int(limit)):
        page_list.append(info[i:i + int(limit)])
    info_list = page_list[int(page) - 1]

    # 查询当次充值时的账号总充值金额
    new_list = list()
    for o in info_list:
        x_time = o.get('ver_time')
        user_id = o.get('cus_id')
        sum_money = SqlData.search_time_sum_money(x_time, user_id)
        o['sum_balance'] = round(sum_money, 2)
        new_list.append(o)

    results['data'] = new_list
    results['count'] = len(data)
    return jsonify(results)


@verify_pay_blueprint.route('/top_up/', methods=['GET', 'POST'])
@verify_required
def top_up():
    if request.method == 'GET':
        pay_time = request.args.get('pay_time')
        cus_name = request.args.get('cus_name')
        bank_msg = request.args.get('bank_msg')
        context = dict()
        context['pay_time'] = pay_time
        context['cus_name'] = cus_name
        context['bank_msg'] = bank_msg
        return render_template('verify_pay/check.html', **context)
    if request.method == 'POST':
        try:
            results = dict()
            data = json.loads(request.form.get('data'))
            pay_time = data.get('pay_time')
            cus_name = data.get('cus_name')
            check = data.get('check')
            ver_code = data.get('ver_code')
            bank_address = data.get("bank_msg")

            # 校验参数验证激活码
            if check != 'yes':
                results['code'] = RET.SERVERERROR
                results['msg'] = '请确认已收款!'
                return jsonify(results)
            pass_wd = SqlData.search_pay_code('ver_code', cus_name, pay_time)
            if pass_wd != ver_code:
                results['code'] = RET.SERVERERROR
                results['msg'] = '验证码错误!'
                return jsonify(results)

            status = SqlData.search_pay_code('status', cus_name, pay_time)
            if status != '待充值':
                results['code'] = RET.SERVERERROR
                results['msg'] = '该订单已充值,请刷新界面!'
                return jsonify(results)

            # 验证成功后,做客户账户充值
            cus_id = SqlData.search_user_field_name('id', cus_name)

            '''
            # 判断是否需要更改充值金额(取消改动充值金额权限)
            if not money:
                money = SqlData.search_pay_code('top_money', cus_name, pay_time)
            else:
                money = float(money)
                # 更新新的充值金额
                SqlData.update_pay_money(money, cus_id, pay_time)
            '''

            money = SqlData.search_pay_code('top_money', cus_name, pay_time)
            pay_num = sum_code()
            t = xianzai_time()
            before = SqlData.search_user_field_name('balance', cus_name)
            balance = before + money
            user_id = SqlData.search_user_field_name('id', cus_name)
            pay_money = SqlData.search_pay_code('pay_money', cus_name, pay_time)
            # 更新银行卡收款金额
            if bank_address:
                pattern = re.compile(r'\d+\.?\d*')
                bank_number = pattern.findall(bank_address)
                bank_money = SqlData.search_bank_top(bank_number)
                update_money = float(pay_money) + float(bank_money)
                SqlData.update_bank_top(bank_number, float(pay_money), update_money)
            else:
                # 更新首款码收款金额
                # pay_money = SqlData.search_pay_code('pay_money', cus_name, pay_time)
                url = SqlData.search_pay_code('url', cus_name, pay_time)
                SqlData.update_qr_money('top_money', pay_money, url)

            # 更新账户余额
            SqlData.update_user_balance(money, user_id)

            # 更新客户充值记录
            SqlData.insert_top_up(pay_num, t, money, before, balance, user_id)

            # 更新pay_log的订单的充值状态
            SqlData.update_pay_status('已充值', t, cus_id, pay_time)

            phone = SqlData.search_user_field_name('phone_num', cus_name)
            mid_phone = SqlData.search_pay_code('phone', cus_name, pay_time)

            # 给客户和代充值人发送短信通知
            money_msg = "{}元, 可用余额{}".format(money, balance)
            # if phone:
            #     phone_list = phone.split(",")
            #     for p in phone_list:
            #         CCP().send_Template_sms(p, ["556338卡段用户, " + cus_name, t, money_msg], 485108)
            if mid_phone:
                CCP().send_Template_sms(mid_phone, ["556338卡段用户, " + cus_name, t, money_msg], 485108)
            results['code'] = RET.OK
            results['msg'] = MSG.OK
            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            results = dict()
            results['code'] = RET.SERVERERROR
            results['msg'] = str(e)
            return jsonify(results)


@verify_pay_blueprint.route('/del_pay/', methods=['POST'])
@verify_required
def del_pay():
    try:
        data = json.loads(request.form.get('data'))
        user_name = data.get('user_name')
        pay_time = data.get('pay_time')
        user_id = SqlData.search_user_field_name('id', user_name)
        SqlData.del_pay_log(user_id, pay_time)
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        results = dict()
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@verify_pay_blueprint.route('/brex/')
@verify_required
def brex():
    user_name = session.get('user_name')
    context = dict()
    context['user_name'] = user_name
    return render_template('verify_pay/brex.html', **context)


@verify_pay_blueprint.route('/add_account/', methods=['POST'])
@verify_required
def add_brex_account():
    data = json.loads(request.form.get('data'))
    account = data.get('account')
    password = data.get('password')
    res = SqlData.search_brex_user(account)
    results = {"code": RET.OK, "msg": MSG.OK}
    if res:
        results['code'] = RET.SERVERERROR
        results['msg'] = '该账号已存在!'
        return jsonify(results)
    else:
        SqlData.insert_brex_user(account, password)
        return jsonify(results)


@verify_pay_blueprint.route('/all_account/')
@verify_required
def brex_user():
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    limit = request.args.get('limit')
    page = request.args.get('page')
    data = SqlData.search_brex_user_all()
    if not data:
        results['msg'] = MSG.NODATA
        return jsonify(results)
    info = list(reversed(data))
    page_list = list()
    for i in range(0, len(info), int(limit)):
        page_list.append(info[i:i + int(limit)])
    info_list = page_list[int(page) - 1]
    results['data'] = info_list
    results['count'] = len(data)
    return jsonify(results)


@verify_pay_blueprint.route('/del_account/')
@verify_required
def del_account():
    account = request.args.get('account')
    SqlData.del_brex_user(account)
    results = {"code": RET.OK, "msg": MSG.OK}
    return jsonify(results)


@verify_pay_blueprint.route('/brex_pay_log/', methods=['GET'])
# @verify_required
def brex_pay_log():
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    limit = request.args.get('limit')
    page = request.args.get('page')
    status = request.args.get('status')
    data = SqlData.search_brex_pay_log(status)
    if not data:
        results['msg'] = MSG.NODATA
        return jsonify(results)
    info = list(reversed(data))
    page_list = list()
    for i in range(0, len(info), int(limit)):
        page_list.append(info[i:i + int(limit)])
    info_list = page_list[int(page) - 1]
    results['data'] = info_list
    results['count'] = len(data)
    return jsonify(results)


@verify_pay_blueprint.route('/brex_del_pay/', methods=['POST'])
@verify_required
def brex_del_pay():
    try:
        data = json.loads(request.form.get('data'))
        pay_id = data.get('pay_id')
        SqlData.del_brex_pay_log(pay_id)
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        results = dict()
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@verify_pay_blueprint.route('/brex_top_up/', methods=['POST'])
@verify_required
def brex_top_up():
    try:
        data = json.loads(request.form.get('data'))
        pay_id = data.get('pay_id')
        now_time = xianzai_time()
        SqlData.update_brex_pay_log(now_time, pay_id)
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        results = dict()
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@verify_pay_blueprint.route('/top_msg_table/', methods=['GET'])
@verify_required
def email_table():
    push_json = SqlData.search_verify_email()
    if push_json:
        push_dict = json.loads(push_json)
        info_list = list()
        for i in push_dict:
            info_dict = dict()
            info_dict['user'] = i
            info_dict['email'] = push_dict.get(i)
            info_list.append(info_dict)
        return jsonify({'code': RET.OK, 'msg': MSG.OK, 'count': len(info_list), 'data': info_list})
    else:
        return jsonify({'code': RET.OK, 'msg': MSG.NODATA})


@verify_pay_blueprint.route('/top_msg/', methods=['POST'])
@verify_required
def top_msg():
    if request.method == 'POST':
        try:
            results = {"code": RET.OK, "msg": MSG.OK}
            data = json.loads(request.form.get('data'))
            top_people = data.get('top_people')
            email = data.get('email')
            push_json = SqlData.search_verify_email()
            if not push_json:
                info_dict = dict()
                info_dict[top_people] = email
            else:
                info_dict = json.loads(push_json)
                if top_people in info_dict:
                    return jsonify({'code': RET.SERVERERROR, 'msg': '收件人已存在！'})
                else:
                    info_dict[top_people] = email
            json_info = json.dumps(info_dict, ensure_ascii=False)
            SqlData.update_verify_email(json_info)
            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@verify_pay_blueprint.route('/del_email/')
@verify_required
def del_email():
    try:
        user = request.args.get('user')
        push_json = SqlData.search_verify_email()
        push_dict = json.loads(push_json)
        del push_dict[user]
        json_info = json.dumps(push_dict, ensure_ascii=False)
        SqlData.update_verify_email(json_info)
        results = {"code": RET.OK, "msg": MSG.OK}
        return jsonify(results)
    except Exception as e:
        logging.error(e)
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@verify_pay_blueprint.route('/edit_email/', methods=['POST'])
@verify_required
def edit_email():
    user = request.form.get('user')
    email = request.form.get('email')
    push_json = SqlData.search_verify_email()
    push_dict = json.loads(push_json)
    push_dict[user] = email
    json_info = json.dumps(push_dict, ensure_ascii=False)
    SqlData.update_verify_email(json_info)
    results = {"code": RET.OK, "msg": MSG.OK}
    return jsonify(results)


@verify_pay_blueprint.route('/edit_hand/', methods=['POST'])
@verify_required
def edit_hand():
    user = request.form.get('user')
    hand = request.form.get('hand')
    SqlData.update_divvy_hand(hand, user)
    results = {"code": RET.OK, "msg": MSG.OK}
    return jsonify(results)



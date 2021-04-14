import json
import datetime
import logging
import operator
import re
import time
import os
from flask import request, render_template, jsonify, session, g, redirect
from xpinyin import Pinyin

from tools_me.svb import svb
from tools_me.des_code import ImgCode
from tools_me.img_code import createCodeImage
from tools_me.mysql_tools import SqlData
from tools_me.other_tools import admin_required, sum_code, xianzai_time, get_nday_list, verify_login_time
from tools_me.parameter import RET, MSG, DIR_PATH
from tools_me.redis_tools import RedisTool
from tools_me.send_sms.send_sms import CCP
from tools_me.sm_photo import sm_photo
from . import admin_blueprint
from config import cache


@admin_blueprint.route('/user_line_chart/')
@admin_required
def line_chart():
    u_id = request.args.get('user_id')
    day_list = get_nday_list(7)
    sum_day_money = list()
    sum_day_card = list()
    u_sql = "AND user_id={}".format(u_id)
    for d in day_list:
        start_t = d + " 00:00:00"
        end_t = d + " 23:59:59"
        day_money = SqlData.search_trans_money(start_t, end_t, user_sql=u_sql)
        if not day_money:
            day_money = 0
        sum_day_money.append(abs(day_money))
        sql = "WHERE do_type='开卡' AND do_date BETWEEN '{}' AND '{}' AND user_id={}".format(start_t, end_t, u_id)
        card_num = SqlData.search_value_count('user_trans', sql=sql)
        sum_day_card.append(card_num)
    money_dict = {'name': '充值金额', 'type': 'column', 'yAxis': 1, 'data': sum_day_money, 'tooltip': {'valueSuffix': ' $'}}
    card_dict = {'name': '开卡数量', 'type': 'spline', 'data': sum_day_card, 'tooltip': {'valueSuffix': ' 张'}}
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    results['data'] = [money_dict, card_dict]
    results['xAx'] = day_list
    return jsonify(results)


@admin_blueprint.route('/account_chart_line/', methods=['GET', 'POST'])
@admin_required
def account_chart_line():
    if request.method == 'GET':
        u_id = request.args.get('user_id')
        context = dict()
        context['user_id'] = u_id
        return render_template('admin/user-chart.html', **context)


@admin_blueprint.route('/money_detail/', methods=['GET'])
@admin_required
def money_detail():
    info_id = request.args.get('info_id')
    detail = SqlData.search_middle_money_field('detail', int(info_id))
    detail_list = json.loads(detail)
    context = dict()
    context['info_list'] = detail_list
    return render_template('middle/money_detail.html', **context)


@admin_blueprint.route('/account_card/', methods=['GET'])
@admin_required
def account_card():
    u_id = request.args.get('user_id')
    card_status = request.args.get('card_status')
    page = request.args.get('page')
    limit = request.args.get('limit')
    if card_status == "hide":
        sql = " AND status != 'F'"
    else:
        sql = ""
    card_info = SqlData.search_card_info_admin("WHERE user_id = {} {}".format(u_id, sql))
    if len(card_info) == 0:
        results = dict()
        results['msg'] = MSG.NODATA
        results['code'] = RET.SERVERERROR
        return jsonify(results)
    task_info = list(reversed(card_info))
    page_list = list()
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results = dict()
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(card_info)
    results['msg'] = MSG.OK
    results['code'] = RET.OK
    return jsonify(results)


@admin_blueprint.route('/account_card_list/', methods=['GET'])
@admin_required
def account_card_list():
    u_id = request.args.get('u_id')
    context = dict()
    context['u_id'] = u_id
    return render_template('admin/card_list.html', **context)


@admin_blueprint.route('/del_account/', methods=['GET'])
@admin_required
def del_account():
    user_id = request.args.get('user_id')
    SqlData.del_recharge_acc(int(user_id))
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/edit_acc/', methods=['GET', 'POST'])
@admin_required
def edit_acc():
    if request.method == 'GET':
        user_id = request.args.get('user_id')
        context = dict()
        context['user_id'] = user_id
        return render_template('admin/edit_acc.html', **context)
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        user_id = data.get('user_id')
        account = data.get('account')
        password = data.get('password')
        if account:
            res = SqlData.find_in_set('recharge_account', account, 'username')
            if res:
                return jsonify({'code': RET.SERVERERROR, 'msg': '账号已存在！请重新命名。'})
            else:
                SqlData.update_recharge_account('username', account, int(user_id))
        if password:
            SqlData.update_recharge_account('password', password, int(user_id))
        return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/all_account/', methods=['GET'])
@admin_required
def all_account():
    data = SqlData.recharge_all_account()
    return jsonify({
        "code": RET.OK,
        "msg": MSG.OK,
        "count": len(data),
        "data": data,
    })


@admin_blueprint.route('/recharge_account/', methods=['GET'])
@admin_required
def recharge_account():
    return render_template('admin/recharge_account.html')


@admin_blueprint.route('/add_recharge/', methods=['GET', 'POST'])
@admin_required
def add_recharge():
    if request.method == "GET":
        return render_template('admin/add_recharge.html')
    if request.method == "POST":
        results = {"code": RET.OK, "msg": MSG.OK}
        try:
            data = json.loads(request.form.get('data'))
            name = data.get('name')
            account = data.get('username')
            password = data.get('password')
            SqlData.recharge_add_account(name=name, username=account, password=password)
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


@admin_blueprint.route('/user_decline_proportion/', methods=['GET'])
@admin_required
def user_decline_proportion():
    '''
    本接口是根据card的交易记录时时计算获取的，后期数量太大，可以采取缓存措施
    1：查出所有的用户
    2:查出所有的消费记录
    3：匹配计算数量以及比例
    :return:
    '''

    # user_info 数据格式：[{'id': 1, 'name': 'Helen'}]
    user_info = SqlData.search_user_field_admin()

    # 卡的全部交易记录数据(从中筛选三天内交易数量和decline数量)
    card_trans = SqlData.search_admin_card_trans('')

    # 获取三天前的时间
    three_before = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

    info_list = list()
    # 开始遍历每个客户进行删选
    for user in user_info:
        trans_num = 0
        decline_num = 0
        name = user.get('name')
        u_id = user.get('id')
        sum_decline = SqlData.search_trans_count(u_id, "AND card_trans.status='F'")
        sum_trans = SqlData.search_trans_count(u_id, "")
        for tran in card_trans:
            status = tran.get('status')  # 根据状态来判断给订单是否decline
            u_name = tran.get('name')
            trans_time = tran.get('transaction_date_time')
            mat = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", trans_time)
            # 如果匹配时间失败则时间调为4天前(不计数)
            try:
                trans_t = mat.group(0)
            except:
                trans_t = (datetime.datetime.now() - datetime.timedelta(days=4)).strftime("%Y-%m-%d")
            result = verify_login_time(three_before + " 00:00:00", trans_t + " 00:00:00")
            if result and status == 'F' and u_name == name:
                decline_num += 1
            if result and u_name == name:
                trans_num += 1
        three_bili = float("%.4f" % (decline_num / trans_num * 100)) if trans_num != 0 else 0
        sum_bili = float("%.4f" % (sum_decline / sum_trans * 100)) if sum_trans != 0 else 0
        user_dict = dict()
        user_dict['name'] = name
        user_dict['sum_decline'] = sum_decline
        user_dict['sum_trans'] = sum_trans
        user_dict['sum_bili'] = sum_bili
        user_dict['decline_num'] = decline_num
        user_dict['trans_num'] = trans_num
        user_dict['three_bili'] = three_bili
        info_list.append(user_dict)
    results = dict()
    info_list = sorted(info_list, key=operator.itemgetter('three_bili'))
    task_info = list(reversed(info_list))
    results['msg'] = MSG.OK
    results['code'] = RET.OK
    results['data'] = task_info
    results['count'] = len(user_info)
    return jsonify(results)


@admin_blueprint.route('/card_decline_proportion/', methods=['GET'])
@admin_required
def card_decline_proportion():
    return render_template('admin/decline_proportion.html')


@admin_blueprint.route('/card_decline_table/', methods=['GET'])
@admin_required
def card_decline_table():
    return render_template('admin/card_decline.html')


@admin_blueprint.route('/card_trans_table/', methods=['GET'])
@admin_required
def card_trans_table():
    return render_template('admin/card_trans.html')


@admin_blueprint.route('/card_trans_settle/', methods=['GET'])
@admin_required
def card_trans_settle():
    return render_template('admin/card_trans_settle.html')


@admin_blueprint.route('/push_log_settle/', methods=['GET'])
@admin_required
def push_log_settle():
    '''
    卡交易记录接口
    '''

    try:
        page = request.args.get('page')
        limit = request.args.get('limit')
        card_number = request.args.get('card_no')
        trans_status = request.args.get('trans_status')
        # 这是所有消费记录的sql
        if trans_status and card_number:
            sql_1 = " AND card_number LIKE '%{}%'".format(card_number)
            if trans_status == "T":
                sql_2 = " AND handing_fee != 0"
            else:
                sql_2 = " AND handing_fee = 0"
            sql = sql_1 + sql_2
        elif card_number:
            sql = " AND card_number LIKE '%{}%'".format(card_number)
        elif trans_status:
            if trans_status == "T":
                sql = " AND handing_fee != 0"
            else:
                sql = " AND handing_fee = 0"
        else:
            sql = ""

        results = dict()
        results['msg'] = MSG.OK
        results['code'] = RET.OK
        info = SqlData.search_admin_card_trans_settle(sql)
        if not info:
            results['msg'] = MSG.NODATA
            return jsonify(results)
        task_info = sorted(info, key=operator.itemgetter('authorization_date'))
        page_list = list()
        task_info = list(reversed(task_info))
        for i in range(0, len(task_info), int(limit)):
            page_list.append(task_info[i:i + int(limit)])
        results['data'] = page_list[int(page) - 1]
        results['count'] = len(task_info)
        return jsonify(results)
    except Exception as e:
        logging.error('查询卡交易推送失败:' + str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/push_log/', methods=['GET'])
@admin_required
def push_log():
    '''
    卡交易记录接口
    '''

    try:
        page = request.args.get('page')
        limit = request.args.get('limit')
        card_number = request.args.get('card_no')
        cus_name = request.args.get('cus_name')
        status = request.args.get('status')
        # 这是所有消费记录的sql
        if card_number or cus_name:
            card_sql = ""
            cus_sql = ""
            if card_number:
                card_sql = " card_trans.card_number LIKE '%" + card_number + "%'"
            if cus_name:
                cus_sql = " user_info.`name` LIKE '%" + cus_name + "%'"
            if card_number and cus_name:
                sql = "AND" + card_sql + " AND " + cus_sql
            else:
                sql = "AND" + card_sql + cus_sql
        else:
            sql = ""
        # 这是decline的sql
        if status:
            sql = " AND status='{}'".format(status)

        results = dict()
        results['msg'] = MSG.OK
        results['code'] = RET.OK
        info = SqlData.search_admin_card_trans(sql)
        if not info:
            results['msg'] = MSG.NODATA
            return jsonify(results)
        task_info = sorted(info, key=operator.itemgetter('transaction_date_time'))
        page_list = list()
        task_info = list(reversed(task_info))
        for i in range(0, len(task_info), int(limit)):
            page_list.append(task_info[i:i + int(limit)])
        results['data'] = page_list[int(page) - 1]
        results['count'] = len(task_info)
        return jsonify(results)
    except Exception as e:
        logging.error('查询卡交易推送失败:' + str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/edit_bank_money/', methods=['POST'])
@admin_required
def edit_bank_money():
    bank_number = request.form.get('bank_number')
    money = request.form.get('money')
    SqlData.update_bank_day_top(bank_number, float(money))
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/top_bank/', methods=['GET'])
@admin_required
def top_bank():
    bank_number = request.args.get('bank_number')
    status = SqlData.search_bank_status(bank_number)
    # status:1为锁定，0为正常，2为置顶
    if status == 2:
        SqlData.update_bank_status(bank_number, 0)
    else:
        res = SqlData.search_bank_info('WHERE status=2')
        if res:
            return jsonify({'code': RET.SERVERERROR, 'msg': '请取消已置顶银行卡后重试！'})
        SqlData.update_bank_status(bank_number, 2)
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/lock_bank/', methods=['GET'])
@admin_required
def lock_bank():
    bank_number = request.args.get('bank_number')
    status = SqlData.search_bank_status(bank_number)
    if status == 0:
        SqlData.update_bank_status(bank_number, 1)
    else:
        SqlData.update_bank_status(bank_number, 0)
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/del_bank/', methods=['GET'])
@admin_required
def del_bank():
    bank_number = request.args.get("bank_number")
    SqlData.del_benk_data(bank_number=bank_number)
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/bank_info/', methods=['GET', 'POST'])
@admin_required
def bank_info():
    if request.method == "GET":
        results = {}
        push_json = SqlData.search_bank_info()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        if not push_json:
            results['msg'] = MSG.NODATA
            return jsonify(results)
        results['data'] = push_json
        results['count'] = len(push_json)
        return jsonify(results)


@admin_blueprint.route('/bank_msg/', methods=['GET', 'POST'])
@admin_required
def bank_msg():
    if request.method == 'GET':
        return render_template('admin/bank_info.html', )
    if request.method == 'POST':
        try:
            data = json.loads(request.form.get('data'))
            results = {"code": RET.OK, "msg": MSG.OK}
            bank_name = data.get("bank_people")
            bank_number = data.get("bank_email")
            bank_address = data.get("bank_address")
            # 插入数据
            SqlData.insert_bank_info(bank_name=bank_name, bank_number=bank_number, bank_address=bank_address)
            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/top_code/', methods=['GET'])
@admin_required
def top_code():
    url = request.args.get('url')
    status = SqlData.search_qr_field('status', url)
    # status:1为锁定，0为正常，2为置顶
    if status == 2:
        SqlData.update_qr_info('status', 0, url)
    else:
        res = SqlData.search_qr_code("WHERE status=2")
        if res:
            return jsonify({'code': RET.SERVERERROR, 'msg': '请取消已置顶收款码后重试！'})
        SqlData.update_qr_info('status', 2, url)
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/edit_code/', methods=['GET', 'POST'])
@admin_required
def edit_code():
    if request.method == 'GET':
        try:
            url = request.args.get('url')
            status = SqlData.search_qr_field('status', url)
            if status == 1:
                now_status = 0
            else:
                now_status = 1
            SqlData.update_qr_info('status', now_status, url)
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})
    if request.method == 'POST':
        url = request.args.get('url')
        SqlData.del_qr_code(url)
        return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/ex_change/', methods=['GET', 'POST'])
@admin_required
def ex_change():
    if request.method == 'GET':
        admin_info = SqlData.search_admin_exchange()
        return render_template('admin/exchange_edit.html', **admin_info)
    if request.method == 'POST':
        try:
            results = {"code": RET.OK, "msg": MSG.OK}
            data = json.loads(request.form.get('data'))
            exchange = data.get('exchange')
            ex_range = data.get('ex_range')
            hand = data.get('hand')
            dollar_hand = data.get('dollar_hand')
            if exchange:
                SqlData.update_admin_field('set_change', float(exchange))
            if ex_range:
                SqlData.update_admin_field('set_range', float(ex_range))
            if hand:
                SqlData.update_admin_field('hand', float(hand))
            if dollar_hand:
                SqlData.update_admin_field('dollar_hand', float(dollar_hand))
            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/upload_code/', methods=['POST'])
@admin_required
def up_pay_pic():
    results = {'code': RET.OK, 'msg': MSG.OK}
    file = request.files.get('file')
    file_name = sum_code() + ".png"
    # file_path = DIR_PATH.PHOTO_DIR + "/" + file_name
    file_path = os.path.join(DIR_PATH.PHOTO_DIR, file_name)
    file.save(file_path)
    filename = sm_photo(file_path, file_name)
    if filename:
        # 上传成功后插入信息的新的收款方式信息
        os.remove(file_path)
        t = xianzai_time()
        url = "http://cdn.trybest.top/" + filename
        SqlData.insert_qr_code(url, t)
        return jsonify(results)
    else:
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/qr_info/', methods=['GET'])
@admin_required
def qr_info():
    results = dict()
    results['code'] = RET.OK
    results['msg'] = MSG.OK
    info_list = SqlData.search_qr_code('')
    if not info_list:
        results['msg'] = MSG.NODATA
        return jsonify(results)
    results['data'] = info_list
    results['count'] = len(info_list)
    return jsonify(results)


@admin_blueprint.route('/edit_email/', methods=['POST'])
@admin_required
def edit_email():
    user = request.form.get('user')
    email = request.form.get('email')
    push_json = SqlData.search_admin_field('top_push')
    push_dict = json.loads(push_json)
    push_dict[user] = email
    json_info = json.dumps(push_dict, ensure_ascii=False)
    SqlData.update_admin_field('top_push', json_info)
    results = {"code": RET.OK, "msg": MSG.OK}
    return jsonify(results)


@admin_blueprint.route('/del_email/')
@admin_required
def del_email():
    try:
        user = request.args.get('user')
        push_json = SqlData.search_admin_field('top_push')
        push_dict = json.loads(push_json)
        del push_dict[user]
        json_info = json.dumps(push_dict, ensure_ascii=False)
        SqlData.update_admin_field('top_push', json_info)
        results = {"code": RET.OK, "msg": MSG.OK}
        return jsonify(results)
    except Exception as e:
        logging.error(e)
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/top_msg_table/', methods=['GET'])
@admin_required
def email_table():
    push_json = SqlData.search_admin_field('top_push')
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


@admin_blueprint.route('/top_msg/', methods=['GET', 'POST'])
@admin_required
def top_msg():
    if request.method == 'GET':
        return render_template('admin/top_msg.html')
    if request.method == 'POST':
        try:
            results = {"code": RET.OK, "msg": MSG.OK}
            data = json.loads(request.form.get('data'))
            top_people = data.get('top_people')
            email = data.get('email')
            push_json = SqlData.search_admin_field('top_push')
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
            SqlData.update_admin_field('top_push', json_info)
            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/qr_code/', methods=['GET', 'POST'])
@admin_required
def qr_code():
    if request.method == 'GET':
        return render_template('admin/qr_code.html')


@admin_blueprint.route('/bento_refund', methods=['GET'])
@admin_required
def bento_refund():
    page = request.args.get('page')
    limit = request.args.get('limit')
    acc_name = request.args.get('acc_name')
    order_num = request.args.get('order_num')
    time_range = request.args.get('time_range')

    name_sql = ""
    order_sql = ""
    time_sql = ""

    if acc_name:
        name_sql = "account.name='{}'".format(acc_name)
    if order_num:
        order_sql = "account_trans.card_no='{}'".format(order_num)
    if time_range:
        min_time = time_range.split(' - ')[0] + ' 00:00:00'
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        time_sql = "account_trans.do_date BETWEEN '{}' and '{}'".format(min_time, max_time)

    if name_sql and time_sql and order_sql:
        sql_all = "AND " + name_sql + " AND " + order_sql + " AND " + time_sql
    elif name_sql and order_sql:
        sql_all = "AND " + name_sql + " AND " + order_sql
    elif time_sql and order_sql:
        sql_all = "AND " + time_sql + " AND " + order_sql
    elif name_sql and time_sql:
        sql_all = "AND " + name_sql + " AND " + time_sql
    elif name_sql:
        sql_all = "AND " + name_sql
    elif order_sql:
        sql_all = "AND " + order_sql
    elif time_range:
        sql_all = "AND " + time_sql
    else:
        sql_all = ""
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    task_info = SqlData.bento_refund_data(sql_all)
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return jsonify(results)
    page_list = list()
    task_info = sorted(task_info, key=operator.itemgetter('time'))
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    data = page_list[int(page) - 1]
    # 处理不同充值类型的显示方式(系统, 退款)
    """
    sum_data = 0
    for i in list(reversed(data)):
        sum_data = float(i.get("money")) + sum_data
        i.update({
            "sum_balance": sum_data
        })
    info_list_1 = list()
    for n in data:
        trans_type = n.get('trans_type')
        if trans_type == '退款':
            n['refund'] = ''
            info_list_1.append(n)
    # 查询当次充值时的账号总充值金额
    info_list = list()
    for o in info_list_1:
        x_time = o.get('time')
        user_id = o.get('user_id')
        sum_money = SqlData.search_time_sum_money(x_time, user_id)
        o['sum_balance'] = round(sum_money, 2)
        info_list.append(o)
    """
    for o in data:
        x_time = o.get("time")
        user_id = o.get("user_id")
        sum_money = SqlData.search_bento_sum_money(user_id=user_id, x_time=x_time)
        sum_refund = SqlData.search_bento_sum_refund(user_id=user_id, x_time=x_time)
        o["sum_balance"] = round(sum_money, 2)
        o["sum_refund"] = round(sum_refund, 2)
    results['data'] = data
    results['count'] = len(task_info)
    return jsonify(results)


@admin_blueprint.route('/cus_log', methods=['GET'])
@admin_required
def cus_log():
    page = request.args.get('page')
    limit = request.args.get('limit')

    cus_name = request.args.get('cus_name')
    time_range = request.args.get('time_range')
    time_sql = ""
    cus_sql = ""
    if time_range:
        min_time = time_range.split(' - ')[0]
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        time_sql = "AND log_time BETWEEN " + "'" + min_time + "'" + " and " + "'" + max_time + "'"
    if cus_name:
        cus_sql = "AND customer='" + cus_name + "'"

    task_info = SqlData.search_account_log(cus_sql, time_sql)
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info = sorted(task_info, key=operator.itemgetter('log_time'))
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return jsonify(results)


@admin_blueprint.route('/account_trans/', methods=['GET'])
@admin_required
def account_trans():
    page = request.args.get('page')
    limit = request.args.get('limit')
    trans_type = request.args.get('trans_type')
    if trans_type == "收入":
        sql = "AND trans_type='收入'"
    else:
        sql = ""
    time_range = request.args.get('time_range')
    cus_name = request.args.get('cus_name')
    trans_card = request.args.get('trans_card')
    do_type = request.args.get('do_type')
    time_sql = ""
    card_sql = ""
    cus_sql = ""
    do_sql = ""
    if time_range:
        min_time = time_range.split(' - ')[0]
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        time_sql = "AND user_trans.do_date BETWEEN " + "'" + min_time + "'" + " and " + "'" + max_time + "'"
    if trans_card:
        card_sql = "AND user_trans.card_no LIKE '%{}%'".format(trans_card.strip())
    if cus_name:
        cus_sql = "AND user_info.name LIKE '%" + cus_name + "%'"
    if do_type:
        do_sql = "AND user_trans.do_type LIKE '%{}%'".format(do_type)

    task_info = SqlData.search_trans_admin(cus_sql, card_sql, time_sql, do_sql, sql)
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return jsonify(results)
    page_list = list()
    task_info = sorted(task_info, key=operator.itemgetter('date'))

    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    results['data'] = page_list[int(page) - 1]
    results['count'] = len(task_info)
    return jsonify(results)


@admin_blueprint.route('/card_table/')
@admin_required
def card_table():
    if g.admin_id == 857:
        return render_template('user/no_auth.html')
    else:
        return render_template('admin/card_using.html')


@admin_blueprint.route('/notice/', methods=['GET', 'POST'])
@admin_required
def notice():
    if request.method == 'GET':
        note = SqlData.search_admin_field('notice')
        note = note.split("!@#")[0]
        context = dict()
        context['note'] = note
        return render_template('admin/notice.html', **context)
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        t = xianzai_time()
        note = data.get('note')
        note = note + "!@#" + t
        SqlData.update_admin_field('notice', note)
        return jsonify({"code": RET.OK, "msg": MSG.OK})


@admin_blueprint.route('/card_all', methods=['GET'])
@admin_required
def card_info_all():
    try:
        limit = request.args.get('limit')
        page = request.args.get('page')
        field = request.args.get('field')
        value = request.args.get('value')
        card_status = request.args.get('card_status')
        if field == "card_cus":
            account_id = SqlData.search_user_field_name('id', value)
            sql = "WHERE user_id=" + str(account_id)
        elif field == "card_end":
            sql = "WHERE card_number LIKE '%" + value + "'"
        elif field:
            sql = "WHERE " + field + " LIKE '%" + value + "%'"
        else:
            if card_status == "show":
                sql = "WHERE status != ''"
            else:
                sql = "WHERE status = 'T'"
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        info_list = SqlData.search_card_info_admin(sql)
        if not info_list:
            results['code'] = RET.OK
            results['msg'] = MSG.NODATA
            return jsonify(results)
        page_list = list()
        info_list = list(reversed(info_list))
        for i in range(0, len(info_list), int(limit)):
            page_list.append(info_list[i:i + int(limit)])
        results['data'] = page_list[int(page) - 1]
        results['count'] = len(info_list)
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


# 卡的交易记录
@admin_blueprint.route('/one_card_detail', methods=['GET'])
@admin_required
def one_detail():
    try:
        context = dict()
        card_number = request.args.get('card_number')
        card_status = SqlData.search_one_card_status(card_number)
        card_id = SqlData.search_card_field('card_id', card_number)
        card_detail = svb.card_detail(card_id)
        if card_status:
            available_balance = card_detail.get('data').get('available_balance')
            context['available_balance'] = available_balance / 100
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
                "billing_amount": float(td.get("billing_amount") / 100),
                "billing_currency": td.get("billing_currency"),
                "issuer_response": td.get("issuer_response"),
                "mcc": td.get("mcc"),
                "mcc_description": td.get("mcc_description"),
                "merchant_amount": float(td.get("merchant_amount") / 100),
                "merchant_currency": td.get("merchant_currency"),
                "merchant_id": td.get("merchant_id"),
                "merchant_name": td.get("merchant_name"),
                "transaction_date_time": td.get("transaction_date_time"),
                "vcn_response": td.get("vcn_response"),
            })

        settle = list()
        clearings = card_detail.get('data').get('clearings')
        for td in clearings:
            settle.append({
                "acquirer_ica": td.get("acquirer_ica"),
                "approval_code": td.get("approval_code"),
                "billing_amount": float(td.get("billing_amount") / 100),
                "billing_currency": td.get("billing_currency"),
                "issuer_response": td.get("issuer_response"),
                "mcc": td.get("mcc"),
                "mcc_description": td.get("mcc_description"),
                "merchant_amount": float(td.get("merchant_amount") / 100),
                "merchant_currency": td.get("merchant_currency"),
                "merchant_id": td.get("merchant_id"),
                "merchant_name": td.get("merchant_name"),
                "transaction_date_time": td.get("settlement_date"),
            })
        context['settle'] = settle
        context['pay_list'] = info_list
        return render_template('user/card_detail.html', **context)
    except Exception as e:
        logging.error((str(e)))
        return render_template('user/404.html')


@admin_blueprint.route('/sub_middle_money', methods=['POST'])
@admin_required
def sub_middle_money():
    info_id = request.args.get('id')
    n_time = xianzai_time()
    SqlData.update_middle_sub('已确认', n_time, int(info_id))
    return jsonify({"code": RET.OK, "msg": MSG.OK})


@admin_blueprint.route('/middle_money_html/', methods=['GET'])
@admin_required
def middle_html():
    return render_template('admin/middle_money.html')


@admin_blueprint.route('/middle_money', methods=['GET'])
@admin_required
def middle_money():
    try:
        limit = request.args.get('limit')
        page = request.args.get('page')
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        info_list = SqlData.search_middle_money_admin()
        if not info_list:
            results['code'] = RET.OK
            results['msg'] = MSG.NODATA
            return jsonify(results)
        info_list = sorted(info_list, key=operator.itemgetter('start_time'))
        page_list = list()
        info_list = list(reversed(info_list))
        for i in range(0, len(info_list), int(limit)):
            page_list.append(info_list[i:i + int(limit)])
        results['data'] = page_list[int(page) - 1]
        results['count'] = len(info_list)
        return jsonify(results)
    except Exception as e:
        logging.error(str(e))
        return jsonify({'code': RET.SERVERERROR, 'msg': MSG.SERVERERROR})


@admin_blueprint.route('/acc_to_middle/', methods=['GET', 'POST'])
@admin_required
def acc_to_middle():
    if request.method == 'GET':
        middle_id = request.args.get('middle_id')
        middle_sql = "WHERE middle_id=" + middle_id + ""
        cus_list = SqlData.search_cus_list(sql_line=middle_sql)
        null_list = SqlData.search_cus_list(sql_line="WHERE middle_id is null")
        context = dict()
        context['cus_list'] = cus_list
        context['null_list'] = null_list
        return render_template('admin/acc_to_middle.html', **context)
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        data = json.loads(request.form.get('data'))
        name = data.get('name')
        field = data.get('field')
        value = data.get('value')
        if value:
            if field != 'account' and field != 'password':
                try:
                    value = float(value)
                    SqlData.update_middle_field_int(field, value, name)
                except:
                    return jsonify({'code': RET.SERVERERROR, 'msg': '提成输入值错误!请输入数字类型!'})
            else:
                SqlData.update_middle_field_str(field, value, name)

        bind_cus = [k for k, v in data.items() if v == 'on']
        del_cus = [k for k, v in data.items() if v == 'off']

        if bind_cus:
            for i in bind_cus:
                middle_id_now = SqlData.search_user_field_name('middle_id', i)
                # 判断该客户是否已经绑定中介账号
                if middle_id_now:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '该客户已经绑定中介!请解绑后重新绑定!'
                    return jsonify(results)
                middle_id = SqlData.search_middle_name('id', name)
                user_id = SqlData.search_user_field_name('id', i)
                SqlData.update_user_field_int('middle_id', middle_id, user_id)
        if del_cus:
            for i in del_cus:
                user_id = SqlData.search_user_field_name('id', i)
                middle_id_now = SqlData.search_user_field_name('middle_id', i)
                middle_id = SqlData.search_middle_name('id', name)
                # 判断这个客户是不是当前中介的客户,不是则无权操作
                if middle_id_now != middle_id:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '该客户不是当前中介客户!无权删除!'
                    return jsonify(results)
                SqlData.update_user_field_int('middle_id', 'NULL', user_id)
        return jsonify(results)


@admin_blueprint.route('/middle_info/', methods=['GET'])
@admin_required
def middle_info():
    page = request.args.get('page')
    limit = request.args.get('limit')
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    task_info = SqlData.search_middle_info()
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


@admin_blueprint.route('/add_middle/', methods=["GET", 'POST'])
@admin_required
def add_middle():
    if request.method == "GET":
        return render_template('admin/add_middle.html')
    if request.method == "POST":
        results = {"code": RET.OK, "msg": MSG.OK}
        try:
            data = json.loads(request.form.get('data'))
            name = data.get('name')
            account = data.get('account')
            password = data.get('password')
            phone_num = data.get('phone_num')
            price_one = float(data.get('price_one'))
            price_two = float(data.get('price_two'))
            price_three = float(data.get('price_three'))
            ret = SqlData.search_middle_ed(name)
            if ret:
                results['code'] = RET.SERVERERROR
                results['msg'] = '该中介名已存在!'
                return jsonify(results)
            if phone_num:
                ret = re.match(r"^1[35789]\d{9}$", phone_num)
                if not ret:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '请输入符合规范的电话号码!'
                    return jsonify(results)
            SqlData.insert_middle(account, password, name, phone_num, price_one, price_two, price_three)
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = RET.SERVERERROR
            return jsonify(results)


@admin_blueprint.route('/add_account/', methods=['GET', 'POST'])
@admin_required
def add_account():
    if request.method == 'GET':
        if g.admin_id == 857:
            return render_template('user/no_auth.html')
        else:
            middle_info = SqlData.search_middle_info()
            middle_name = list()
            for i in middle_info:
                name = i.get('name')
                middle_name.append(name)
            context = dict()
            context['middle_name'] = middle_name
            return render_template('admin/add_account.html', **context)
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        try:
            data = json.loads(request.form.get('data'))
            name = data.get('name').strip()
            account = data.get('account').strip()
            password = data.get('password').strip()
            phone_num = data.get('phone_num')
            create_price = float(data.get('create_price'))
            min_top = float(data.get('min_top'))
            max_top = float(30000)
            middle_name = data.get('middle_name')
            hand = float(data.get('hand'))
            ed_name = SqlData.search_user_field_name('account', name)
            if ed_name:
                results['code'] = RET.SERVERERROR
                results['msg'] = '该用户名已存在!'
                return jsonify(results)
            if phone_num:
                ret = re.match(r"^1[35789]\d{9}$", phone_num)
                if not ret:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '请输入符合规范的电话号码!'
                    return jsonify(results)
            else:
                phone_num = ""
            if middle_name:
                middle_id = SqlData.search_middle_name('id', middle_name)
            else:
                middle_id = 'NULL'
            SqlData.insert_account(account, password, phone_num, name, create_price, min_top, max_top, middle_id, hand)
            # 创建用户后插入充值数据
            pay_num = sum_code()
            t = xianzai_time()
            user_id = SqlData.search_user_field_name('id', name)
            SqlData.insert_top_up(pay_num, t, 0, 0, 0, user_id)
            SqlData.insert_account_trans(date=t, trans_type="充值", do_type="支出", card_no=0, do_money=0,
                                         before_balance=0, balance=0, user_id=user_id)
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            print(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


@admin_blueprint.route('/password/', methods=['GET'])
@admin_required
def password():
    if g.admin_id == 857:
        return jsonify({'code': RET.OK, 'msg': 'finance1001'})
    else:
        password = SqlData.search_admin_field('password')
        return jsonify({'code': RET.OK, 'msg': password})


@admin_blueprint.route('/change_pass/', methods=['GET', 'POST'])
@admin_required
def change_pass():
    if request.method == 'GET':
        admin_name = g.admin_name
        context = dict()
        context['admin_name'] = admin_name
        return render_template('admin/changePwd.html', **context)
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        data = json.loads(request.form.get('data'))
        old_pass = data.get('old_pass')
        new_pass_one = data.get('new_pass_one')
        new_pass_two = data.get('new_pass_two')
        if new_pass_two != new_pass_one:
            results['code'] = RET.SERVERERROR
            results['msg'] = '两次输入密码不一致!'
            return jsonify(results)
        res = re.match('(?!.*\s)(?!^[\u4e00-\u9fa5]+$)(?!^[0-9]+$)(?!^[A-z]+$)(?!^[^A-z0-9]+$)^.{8,16}$', new_pass_one)
        if not res:
            results['code'] = RET.SERVERERROR
            results['msg'] = '密码不符合要求！'
            return jsonify(results)
        password = SqlData.search_admin_field('password')
        if old_pass != password:
            results['code'] = RET.SERVERERROR
            results['msg'] = '密码错误!'
            return jsonify(results)
        SqlData.update_admin_field('password', new_pass_one)
        session.pop('admin_id')
        session.pop('admin_name')
        return jsonify(results)


@admin_blueprint.route('/admin_info', methods=['GET'])
@admin_required
def admin_info():
    account, password, name, balance = SqlData.admin_info()
    context = dict()
    context['account'] = account
    context['password'] = password
    context['name'] = name
    context['balance'] = balance
    return render_template('admin/admin_info.html', **context)


@admin_blueprint.route('/cus_trans/', methods=['GET'])
@admin_required
def cus_trans():
    return render_template('admin/cus_trans.html')


@admin_blueprint.route('/cus_top_list/', methods=['GET'])
@admin_required
def cus_top_list():
    return render_template('admin/cus_top_table.html')


@admin_blueprint.route('/cus_refund/', methods=['GET'])
@admin_required
def cus_refund_top():
    return render_template('admin/cus_refund.html')


@admin_blueprint.route('/card_free/', methods=['GET'])
@admin_required
def card_free():
    return render_template('admin/card_free.html')


@admin_blueprint.route('/top_history/', methods=['GET'])
@admin_required
def top_history():
    page = request.args.get('page')
    limit = request.args.get('limit')
    acc_name = request.args.get('acc_name')
    order_num = request.args.get('order_num')
    time_range = request.args.get('time_range')
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}

    name_sql = ""
    order_sql = ""
    time_sql = ""
    if acc_name:
        name_sql = " AND user_info.name  LIKE '%" + acc_name + "%'"
    if order_num:
        order_sql = " AND top_up.pay_num = '" + order_num + "'"
    if time_range:
        min_time = time_range.split(' - ')[0]
        max_time = time_range.split(' - ')[1] + ' 23:59:59'
        time_sql = " AND top_up.time BETWEEN " + "'" + min_time + "'" + " and " + "'" + max_time + "'"
    sql_all = name_sql + order_sql + time_sql
    task_info = SqlData.search_top_history(sql_all)

    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return jsonify(results)
    page_list = list()
    task_info = sorted(task_info, key=operator.itemgetter('time'))
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    data = page_list[int(page) - 1]
    info_list = list()
    for o in data:
        x_time = o.get('time')
        user_id = o.get('user_id')
        sum_money = SqlData.search_time_sum_money(x_time, user_id)
        o['sum_balance'] = round(sum_money, 2)
        info_list.append(o)
    results['data'] = info_list
    results['count'] = len(task_info)
    return jsonify(results)


@admin_blueprint.route('/acc_pay/', methods=['POST'])
@admin_required
def acc_pay():
    if request.method == 'POST':
        money = request.form.get('money')
        name = request.form.get('name')
        try:
            _money = float(money)
            f_money = round(_money, 2)
            if f_money < 0:
                return jsonify({'code': RET.SERVERERROR, 'msg': '请输入正数金额！'})
            balance = SqlData.search_user_field_name('balance', name)
            if f_money > balance:
                return jsonify({'code': RET.SERVERERROR, 'msg': '扣费余额不足！'})
            user_id = SqlData.search_user_field_name('id', name)
            SqlData.update_balance(-f_money, user_id)
            a_balance = SqlData.search_user_field("balance", user_id)
            # balance = before_balance - create_price
            n_time = xianzai_time()
            SqlData.insert_account_trans(n_time, '支出', '系统扣费', 0, f_money, balance, a_balance, user_id)
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': '请输入正确的消费金额！'})


@admin_blueprint.route('/top_up', methods=['POST'])
@admin_required
def top_up():
    results = {"code": RET.OK, "msg": MSG.OK}
    try:
        data = request.form.get('money')
        name = request.form.get('name')
        pay_num = sum_code()
        t = xianzai_time()
        money = float(data)
        before = SqlData.search_user_field_name('balance', name)
        balance = before + money
        user_id = SqlData.search_user_field_name('id', name)
        # 更新账户余额
        SqlData.update_user_balance(money, user_id)
        # 更新客户充值记录
        SqlData.insert_top_up(pay_num, t, money, before, balance, user_id)

        phone = SqlData.search_user_field_name('phone_num', name)

        if phone:
            CCP().send_Template_sms(phone, ["556338卡段用户, " + name, t, money], 485108)

        return jsonify(results)

    except Exception as e:
        logging.error(e)
        results['code'] = RET.SERVERERROR
        results['msg'] = MSG.SERVERERROR
        return jsonify(results)


@admin_blueprint.route('/edit_parameter/', methods=['GET', 'POST'])
@admin_required
def edit_parameter():
    if request.method == 'GET':
        return render_template('admin/edit_parameter.html')
    if request.method == 'POST':
        results = {"code": RET.OK, "msg": MSG.OK}
        try:
            data = json.loads(request.form.get('data'))
            name = data.get('name_str')
            create_price = data.get('create_price')
            min_top = data.get('min_top')
            max_top = data.get('max_top')
            password = data.get('password')
            account_name = data.get('account_name')
            account = data.get('account')
            hand = data.get('hand')
            if create_price:
                SqlData.update_account_field('create_price', create_price, name)
            if min_top:
                SqlData.update_account_field('min_top', min_top, name)
            if max_top:
                SqlData.update_account_field('max_top', max_top, name)
            if password:
                SqlData.update_account_field('password', password, name)
            if account:
                # 取消消费记录的关联增快消费记录的查询速度，不支持直接修改用户名
                #account = account.strip()
                #ed_name = SqlData.search_user_field_name('account', account)
                #if ed_name:
                results['code'] = RET.SERVERERROR
                results['msg'] = "请联系管理员处理！"
                return jsonify(results)
                #SqlData.update_account_field('account', account, name)
            if account_name:
                account_name = account_name.strip()
                ed_name = SqlData.search_user_field_name('name', account_name)
                if ed_name:
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '该用户名已存在!'
                    return jsonify(results)
                SqlData.update_account_field('name', account_name, name)
            if hand:
                SqlData.update_account_field('hand', hand, name)
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


@admin_blueprint.route('/lock_acc/')
@admin_required
def lock_acc():
    acc_name = request.args.get('acc_name')
    u_id = SqlData.search_user_field_name('id', acc_name)
    check = request.args.get('check')
    if check == 'true':
        RedisTool.string_del(u_id)
    elif check == 'false':
        RedisTool.string_set(u_id, 'F')
    return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/edit_free/', methods=['GET'])
@admin_required
def edit_free():
    user_id = request.args.get('user_id')
    context = {'user_id': user_id}
    return render_template('admin/edit_free.html', **context)


@admin_blueprint.route('/free/', methods=['POST'])
@admin_required
def free_number():
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        card_num = data.get('card_num')
        price = data.get('price')
        user_id = data.get('user_id')
        try:
            if '-' in price:
                return jsonify({'code': RET.SERVERERROR, 'msg': '请输入正数！'})
            card_num = int(card_num)
        except:
            return jsonify({'code': RET.SERVERERROR, 'msg': '卡量请输入整数！'})
        price = float(price)
        deduct_money = round(price * card_num, 2)
        user_balance = SqlData.search_user_field('balance', int(user_id))
        if deduct_money > user_balance:
            return jsonify({'code': RET.SERVERERROR, 'msg': '账户余额不足！'})
        SqlData.update_user_free_card(card_num, user_id)
        SqlData.update_user_balance(-deduct_money, user_id)
        now_time = xianzai_time()
        SqlData.insert_card_free(card_num, price, deduct_money, now_time, int(user_id))
        balance = SqlData.search_user_field('balance', int(user_id))
        SqlData.insert_account_trans(now_time, '支出', '系统扣费', '购买免费卡量', deduct_money, user_balance, balance, int(user_id))
        return jsonify({'code': RET.OK, 'msg': MSG.OK})


@admin_blueprint.route('/card_free_log/', methods=['GET'])
@admin_required
def card_free_log():
    page = request.args.get('page')
    limit = request.args.get('limit')

    acc_name = request.args.get('acc_name')

    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}

    if acc_name:
        sql = "WHERE user_info.name like '%" + acc_name + "%'"
    else:
        sql = ""

    task_info = SqlData.search_card_free_history(sql)
    if len(task_info) == 0:
        results['MSG'] = MSG.NODATA
        return jsonify(results)
    page_list = list()
    task_info = sorted(task_info, key=operator.itemgetter('sub_time'))
    task_info = list(reversed(task_info))
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    data = page_list[int(page) - 1]
    results['data'] = data
    results['count'] = len(task_info)
    return jsonify(results)


@admin_blueprint.route('/account_info/', methods=['GET'])
@admin_required
def account_info():
    page = request.args.get('page')
    limit = request.args.get('limit')
    customer = request.args.get('customer')
    middle = request.args.get('middle')
    results = {"code": RET.OK, "msg": MSG.OK, "count": 0, "data": ""}
    if customer:
        sql = "WHERE name LIKE '%" + customer + "%'"
    elif middle:
        middle_id = SqlData.search_middle_name('id', middle)
        sql = "WHERE middle_id={}".format(middle_id)
    else:
        sql = ''
    task_one = SqlData.search_account_info(sql)
    if len(task_one) == 0:
        results['MSG'] = MSG.NODATA
        return results
    page_list = list()
    task_info_status = dict()
    for c in task_one:
        u_id = c.get('u_id')
        r = RedisTool.string_get(u_id)
        if not r:
            c['status'] = 'T'
        else:
            c['status'] = 'F'
        # 使用中文字母拍寻排列客户信息
        user_name = Pinyin().get_pinyin(c.get('name')).lower().strip()
        task_info_status[user_name] = c
    task_info = list()
    for i in sorted(task_info_status):
        task_info.append(task_info_status[i])
    for i in range(0, len(task_info), int(limit)):
        page_list.append(task_info[i:i + int(limit)])
    data = page_list[int(page) - 1]
    new_data = list()
    # 取出列表中的用户计算总消费和卡总余额
    for i in data:
        u_id = i.get('u_id')
        sum_out_money = SqlData.search_trans_sum(u_id) - SqlData.search_income_money(u_id)
        card_remain = SqlData.search_sum_card_balance(u_id)
        i.update({'sum_out_money': round(sum_out_money, 2)})
        i.update({'card_remain': card_remain})
        new_data.append(i)
    results['data'] = new_data
    results['count'] = len(task_info)
    return jsonify(results)


# @admin_blueprint.route('/account_card_list', methods=['GET'])
# @admin_required
# def account_card_list():
#     attribution = request.args.get('user_name')
#     context = dict()
#     context['user_name'] = attribution
#     return render_template('admin/card_list.html', **context)


@admin_blueprint.route('/middle_info_html/', methods=['GET'])
@admin_required
def middle_info_html():
    return render_template('admin/middle_info.html')


@admin_blueprint.route('/cus_list/', methods=['GET'])
@admin_required
def cus_list():
    if g.admin_id == 857:
        return render_template('admin/vice_cus_list.html')
    else:
        middle_info = SqlData.search_middle_info()
        middle_name = list()
        for i in middle_info:
            name = i.get('name')
            middle_name.append(name)
        context = dict()
        context['middle'] = middle_name
        return render_template('admin/cus_list.html', **context)


@admin_blueprint.route('/line_chart', methods=['GET'])
@admin_required
@cache.cached(timeout=21600, key_prefix='svb_admin_line')
def test():
    # 展示近三十天开卡数量
    day_num = 30
    day_list = get_nday_list(day_num)
    sum_day_money = list()
    sum_day_card = list()
    for d in day_list:
        start_t = d + " 00:00:00"
        end_t = d + " 23:59:59"
        day_money = SqlData.search_top_money(start_t, end_t)
        if not day_money:
            day_money = 0
        sum_day_money.append(day_money)
        sql = "WHERE do_type='开卡' AND do_date BETWEEN '{}' AND '{}'".format(start_t, end_t)
        card_num = SqlData.search_value_count('user_trans', sql=sql)
        sum_day_card.append(card_num)
    money_dict = {'name': '充值金额', 'type': 'column', 'yAxis': 1, 'data': sum_day_money, 'tooltip': {'valueSuffix': ' $'}}
    card_dict = {'name': '开卡数量', 'type': 'spline', 'data': sum_day_card, 'tooltip': {'valueSuffix': ' 张'}}
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


@admin_blueprint.route('/logout/', methods=['GET'])
@admin_required
def logout():
    session.pop('admin_id')
    session.pop('admin_name')
    return redirect('/admin/')


@admin_blueprint.route('/login', methods=['GET', 'POST'])
def admin_login():
    # ip = request.headers.get('X-Forwarded-For')
    ip = request.remote_addr
    if request.method == 'GET':
        str_data, img = createCodeImage(height=36)
        context = dict()
        context['img'] = img
        context['code'] = ImgCode().jiami(str_data)
        try_number = RedisTool.string_get(ip)
        if try_number is None:
            try_number = 0
        if int(try_number) >= 3:
            context['drop_status'] = "block"
        else:
            context['drop_status'] = "none"
        return render_template('admin/login.html', **context)

    if request.method == 'POST':
        results = dict()
        results['code'] = RET.OK
        results['msg'] = MSG.OK
        try:
            data = json.loads(request.form.get('data'))
            account = data.get('userName')
            password = data.get('password')
            image_real = data.get('image_real')
            image_code = data.get('image_code')

            try_number = RedisTool.string_get(ip)
            if not try_number:
                RedisTool.string_set(ip, 1)
            else:
                new_number = int(try_number) + 1
                RedisTool.string_set(ip, new_number)

            try_number = RedisTool.string_get(ip)
            if int(try_number) > 3:
                img_code = ImgCode().jiemi(image_real)
                if image_code.lower() != img_code.lower():
                    results['code'] = RET.SERVERERROR
                    results['msg'] = '验证码错误！'
                    return jsonify(results)
            if account == 'finance' and password == "finance1001":
                session['admin_id'] = 857
                session['admin_name'] = 'finance'
                session.permanent = True
                RedisTool.string_del(ip)
                return jsonify(results)
            else:
                admin_id, name = SqlData.search_admin_login(account, password)
                session['admin_id'] = admin_id
                session['admin_name'] = name
                session.permanent = True
                RedisTool.string_del(ip)
                return jsonify(results)

        except Exception as e:
            try_number = RedisTool.string_get(ip)
            if int(try_number) == 3:
                results['code'] = 501
                results['msg'] = MSG.PSWDERROR
            else:
                results['code'] = RET.SERVERERROR
                results['msg'] = MSG.PSWDERROR
            return jsonify(results)


@admin_blueprint.route('/', methods=['GET'])
@admin_required
def index():
    admin_name = g.admin_name
    context = dict()
    context['admin_name'] = admin_name
    if g.admin_id == 857:
        return render_template('admin/vice_AdminIndex.html', **context)
    else:
        return render_template('admin/AdminIndex.html', **context)


@admin_blueprint.route('/main/', methods=['GET'])
@admin_required
def index_main():
    cus_count = SqlData.search_value_count('user_info')
    card_using = SqlData.search_value_count('card_info', "WHERE user_id != ''")
    card_none = SqlData.search_value_count('card_info', "WHERE status ='T'")
    sum_top = SqlData.search_table_sum('money', 'top_up', '')
    user_balance = SqlData.search_table_sum('balance', 'user_info', '')
    card_remain = SqlData.search_sum_card_remain()
    update_t = SqlData.search_admin_field("up_remain_time")
    context = dict()
    context['cus_count'] = cus_count
    context['card_using'] = card_using
    context['card_none'] = card_none
    context['sum_top'] = sum_top
    context['user_balance'] = user_balance
    context['card_remain'] = card_remain
    context['update_t'] = update_t
    return render_template('admin/main.html', **context)

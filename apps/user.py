import json
import datetime
import logging
import operator
import os
import re
import time
import uuid

import xlwt
from config import cache
from tools_me.other_tools import xianzai_time, login_required, check_float, account_lock, get_nday_list, \
    verify_login_time, trans_lock, sum_code, create_card, dic_key
from tools_me.parameter import RET, MSG, TRANS_TYPE, DO_TYPE, DIR_PATH
from tools_me.redis_tools import RedisTool
from tools_me.send_email import send
from tools_me.remain import get_card_remain
from tools_me.img_code import createCodeImage
from tools_me.des_code import ImgCode
from tools_me.svb import svb
from . import user_blueprint
from flask import render_template, request, jsonify, session, g, redirect, send_file
from tools_me.mysql_tools import SqlData
from concurrent.futures.thread import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s', filename="error.log")

executor = ThreadPoolExecutor(5)


@user_blueprint.route('/pay_pic/', methods=['GET', 'POST'])
@login_required
def pay_pic():
    if request.method == 'GET':
        sum_money = request.args.get('sum_money')
        top_money = request.args.get('top_money')
        ex_change = request.args.get('ex_change')
        # 取出目前当前收款金额最低的收款码
        qr_info = SqlData.search_qr_code('WHERE status=2')
        if qr_info:
            url = qr_info[0].get('qr_code')
        else:
            qr_info = SqlData.search_qr_code('WHERE status=0')
            url = ''
            value_list = list()
            for i in qr_info:
                value_list.append(i.get('sum_money'))
            value = min(value_list)
            for n in qr_info:
                money = n.get('sum_money')
                if value == money:
                    url = n.get('qr_code')
                    break
        context = dict()
        bank_top_data = SqlData.search_bank_info(sql_line='WHERE status=2')
        if bank_top_data:
            data = bank_top_data[0]
            context['bank_name'] = data.get('bank_name')
            context['bank_number'] = data.get('bank_number')
            context['bank_address'] = data.get('bank_address')
        else:
            # 一下三个循环和判断为处理相同收款人，多个账号，取低于累计20万的中的最小收款账号
            bank_data = SqlData.search_bank_info(sql_line='WHERE status=0')
            # bank_info 整理为一个收款人对应多个收款卡号 {'':[],'':[]} 格式
            bank_info = dict()
            for n in bank_data:
                bank_name = n.get('bank_name')
                if bank_name in bank_info:
                    info_list = bank_info.get(bank_name)
                    info_list.append(n)
                else:
                    info_list = list()
                    info_list.append(n)
                    bank_info[bank_name] = info_list
            # sum_money_dict 为统计一个账号一共充值了多少元
            sum_money_dict = dict()
            for i in bank_info:
                value = bank_info.get(i)
                money = 0
                for m in value:
                    money += float(m.get('day_money'))
                sum_money_dict[i] = money
            # min_dict 为取出满足累计收款低于20万的账户，且最小的充值战账户
            min_dict = dict()
            for acc in sum_money_dict:
                if sum_money_dict.get(acc) < 200000:
                    min_dict[acc] = sum_money_dict.get(acc)
            if len(min_dict) == 0:
                context['bank_name'] = '无符合要求收款账户！'
                context['bank_number'] = '请联系管理员处理！'
                context['bank_address'] = '-------------'
            else:
                # 在最小充值账户中取出最小收款卡号推送
                min_acc = min(zip(min_dict.values(), min_dict.keys()))
                min_acc = min_acc[1]
                acc_list = bank_info.get(min_acc)
                data = min(acc_list, key=dic_key)
                context['bank_name'] = data.get('bank_name')
                context['bank_number'] = data.get('bank_number')
                context['bank_address'] = data.get('bank_address')

        context['sum_money'] = sum_money
        context['top_money'] = top_money
        context['url'] = url
        context['ex_change'] = ex_change
        return render_template('user/pay_pic.html', **context)
    if request.method == 'POST':
        '''
        获取充值金额, 保存付款截图. 发送邮件通知管理员
        '''
        # try:
        # 两组数据,1,表单信息充值金额,等一下客户信息 2,截图凭证最多可上传5张
        # print(request.form)
        # print(request.files)
        data = json.loads(request.form.get('data'))
        top_money = data.get('top_money')
        sum_money = data.get('sum_money')
        exchange = data.get('exchange')
        url = json.loads(request.form.get('url'))
        change_type = json.loads(request.form.get("change_type"))
        bank_name = json.loads(request.form.get("bank_name"))
        bank_number = json.loads(request.form.get("bank_number"))
        bank_address = json.loads(request.form.get("bank_address"))
        results = {'code': RET.OK, 'msg': MSG.OK}
        cus_name = g.user_name
        cus_id = g.user_id
        cus_account = SqlData.search_user_field_name('account', cus_name)
        phone = SqlData.search_user_field_name('phone_num', cus_name)
        try:
            # 保存所有图片
            file_n = 'file_'
            pic_list = list()
            # 判断有无上传图片
            f_obj = request.files.get("{}{}".format(file_n, 1))
            if not f_obj:
                return jsonify({'code': RET.SERVERERROR, 'msg': "请先上传图片再操作"})
            for i in range(5):
                file_name = "{}{}".format(file_n, i + 1)
                fileobj = request.files.get(file_name)
                if fileobj:
                    now_time = sum_code()
                    file_name = cus_account + "_" + str(now_time) + str(i) + ".png"
                    file_path = os.path.join(DIR_PATH.PHOTO_DIR, file_name)
                    fileobj.save(file_path)
                    with open(file_path, 'rb') as f:
                        c = f.read()
                        if b'Adobe Photoshop' in c:
                            logging.error('上传PS的图片可客户名称：' + cus_name)
                            return jsonify({'code': RET.SERVERERROR, 'msg': "图片存在异常，请勿使用PS截图凭证！"})
                    pic_list.append(file_path)
            n_time = xianzai_time()
            vir_code = str(uuid.uuid1())[:6]
            context = "客户:  " + cus_name + " , 于<span style='color:red'>" + n_time + "</span>在线申请充值: " \
                      + top_money + "美元, 折和人名币: <span style='color:red'>" + sum_money + "</span>元。本次计算汇率为: " + exchange + ", 验证码为: " + vir_code

            sum_money = float(sum_money)
            top_money = float(top_money)
            if change_type == "pic":
                SqlData.insert_pay_log(n_time, sum_money, top_money, vir_code, '待充值', phone, url, cus_id)
            elif change_type == "bank":
                SqlData.insert_pay_log(n_time, sum_money, top_money, vir_code, '待充值', phone,
                                         "{},{},{}".format(bank_name, bank_number, bank_address), cus_id)
            # 获取要推送邮件的邮箱
            top_push = SqlData.search_admin_field('top_push')
            top_dict = json.loads(top_push)
            email_list = list()
            for i in top_dict:
                email_list.append(top_dict.get(i))
            for p in email_list:
                executor.submit(send, context, pic_list, p)
                # send(context, pic_list, p)

            return jsonify(results)
        except Exception as e:
            logging.error(str(e))
            return jsonify({'code': RET.SERVERERROR, 'msg': str(e)})


@user_blueprint.route('/pay_top/', methods=['GET', 'POST'])
@login_required
def user_top():
    if request.method == 'GET':
        ex_change = SqlData.search_admin_field('ex_change')
        ex_range = SqlData.search_admin_field('ex_range')
        hand = SqlData.search_user_field('hand', g.user_id)
        dollar_hand = SqlData.search_admin_field('dollar_hand')
        context = dict()
        context['ex_change'] = ex_change
        context['ex_range'] = ex_range
        context['hand'] = hand
        context['dollar_hand'] = dollar_hand
        return render_template('user/pay_top.html', **context)
    if request.method == 'POST':
        '''
        1:校验前端数据是否正确
        2:查看实时汇率有没有变动
        3:核实客户是否存在
        '''
        data = json.loads(request.form.get('data'))
        sum_money = data.get('sum_money')
        top_money = data.get('top_money')
        if float(top_money) < 100:
            return jsonify({'code': RET.SERVERERROR, 'msg': '充值金额不能小于100$'})

        ex_change = SqlData.search_admin_field('ex_change')
        ex_range = SqlData.search_admin_field('ex_range')
        hand = SqlData.search_user_field('hand', g.user_id)
        _money_self = float(top_money) * (ex_change + ex_range) * (hand + 1)
        money_self = round(_money_self, 10)
        sum_money = round(float(sum_money), 10)
        if money_self == sum_money:
            return jsonify({'code': RET.OK, 'msg': MSG.OK})
        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '汇率已变动!请刷新界面后重试!'})


@user_blueprint.route('/free_card/', methods=['GET', 'POST'])
@login_required
def free_card():
    if request.method == 'GET':
        return render_template('user/free_card.html')
    if request.method == "POST":
        user_id = g.user_id
        data = json.loads(request.form.get('data'))
        set_meal_data = {1: {'number': 100, 'price': 4}, 2: {'number': 300, 'price': 3}, 3: {'number': 700, 'price': 2}}
        set_meal_number = data.get('number')
        set_meal_info = set_meal_data.get(int(set_meal_number))
        card_number = set_meal_info.get('number')
        price = set_meal_info.get('price')
        out_money = card_number * price
        user_data = SqlData.search_user_index(user_id)
        before_balance = user_data.get('balance')
        if out_money > before_balance:
            results = {"code": RET.SERVERERROR, "msg": "本次消费金额:" + str(out_money) + ",账号余额不足!"}
            return jsonify(results)
        SqlData.update_user_free_card(card_number, user_id)
        SqlData.update_balance(-out_money, user_id)
        now_time = xianzai_time()
        SqlData.insert_card_free(card_number, price, out_money, now_time, int(user_id))
        balance = SqlData.search_user_field('balance', int(user_id))
        SqlData.insert_account_trans(now_time, '支出', '系统扣费', '购买免费卡量', out_money, before_balance, balance,
                                     int(user_id))
        return jsonify({'code': RET.OK, 'msg': MSG.OK})


@user_blueprint.route('/card_settle_dw/', methods=['GET'])
@login_required
def card_settle_dw():
    user_id = g.user_id
    result = SqlData.search_card_trans_settle(user_id, '')
    # 创建一个workbook 设置编码
    workbook = xlwt.Workbook(encoding='utf-8')
    # 创建一个worksheet
    worksheet = workbook.add_sheet('My Worksheet')
    worksheet.write(0, 0, '卡号')
    worksheet.write(0, 1, '标签')
    worksheet.write(0, 2, '冻结金额')
    worksheet.write(0, 3, '冻结币种')
    worksheet.write(0, 4, '授权时间')
    worksheet.write(0, 5, '交易金额')
    worksheet.write(0, 6, '交易币种')
    worksheet.write(0, 7, '商户名称')
    worksheet.write(0, 8, '结算时间')
    worksheet.write(0, 9, '手续费')
    # 参数对应 行, 列, 值
    row = 1
    for i in result:
        worksheet.write(row, 0, label=i.get('card_number'))
        worksheet.write(row, 1, label=i.get('label'))
        worksheet.write(row, 2, label=i.get('billing_amount'))
        worksheet.write(row, 3, label=i.get('billing_currency'))
        worksheet.write(row, 4, label=i.get('authorization_date'))
        worksheet.write(row, 5, label=i.get('merchant_amount'))
        worksheet.write(row, 6, label=i.get('merchant_currency'))
        worksheet.write(row, 7, label=i.get('merchant_name'))
        worksheet.write(row, 8, label=i.get('settlement_date'))
        worksheet.write(row, 9, label=i.get('手续费'))
        row += 1

    # 保存
    path = 'H:\svb\static\excel\{}.xls'.format(g.user_name + str(sum_code()))
    workbook.save(path)
    return send_file(path)


@user_blueprint.route('/card_trans_dw/', methods=['GET'])
@login_required
def card_trans_dw():
    user_id = g.user_id
    result = SqlData.search_card_trans(user_id, '')
    # 创建一个workbook 设置编码
    workbook = xlwt.Workbook(encoding='utf-8')
    # 创建一个worksheet
    worksheet = workbook.add_sheet('My Worksheet')
    worksheet.write(0, 0, '卡号')
    worksheet.write(0, 1, '标签')
    worksheet.write(0, 2, '金额')
    worksheet.write(0, 3, '币种')
    worksheet.write(0, 4, '银行回应')
    worksheet.write(0, 5, '描述')
    worksheet.write(0, 6, '商户名称')
    worksheet.write(0, 7, '交易时间')
    # 参数对应 行, 列, 值
    row = 1
    for i in result:
        worksheet.write(row, 0, label=i.get('card_number'))
        worksheet.write(row, 1, label=i.get('label'))
        worksheet.write(row, 2, label=i.get('billing_amount'))
        worksheet.write(row, 3, label=i.get('billing_currency'))
        worksheet.write(row, 4, label=i.get('issuer_response'))
        worksheet.write(row, 5, label=i.get('mcc_description'))
        worksheet.write(row, 6, label=i.get('merchant_name'))
        worksheet.write(row, 7, label=i.get('transaction_date_time'))
        row += 1

    # 保存
    base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    excel_path = os.path.join(base_path, 'static\excel\{}.xls'.format(g.user_name + str(sum_code())))
    workbook.save(excel_path)
    return send_file(excel_path)


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
@trans_lock
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
    real_status = SqlData.check_card_real(card_number.strip(), user_id)
    if not real_status:
        results = {"code": RET.SERVERERROR, "msg": "请不要违规操作!"}
        return jsonify(results)

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

    del_status = SqlData.search_delete_in(card_number)
    if del_status:
        return jsonify({'code': RET.SERVERERROR, 'msg': "该卡正在等待删除！"})

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
@trans_lock
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
        # return jsonify({"code": RET.SERVERERROR, "msg": "暂时关闭卡删除，开放日期请咨询客服！"})
        card_number = request.args.get('card_number')
        user_id = g.user_id
        real_status = SqlData.check_card_real(card_number.strip(), user_id)
        if not real_status:
            results = {"code": RET.SERVERERROR, "msg": "请不要违规操作!"}
            return jsonify(results)
        card_status = SqlData.search_one_card_status(card_number)
        if card_status:
            status = SqlData.search_delete_in(card_number)
            if status:
                return jsonify({'code': RET.OK, 'msg': '该卡正在等待删除！'})
            card_id = SqlData.search_card_field('card_id', card_number)
            SqlData.insert_delete_card(card_number, card_id, user_id)
            return jsonify({'code': RET.OK, 'msg': '操作成功！正在删卡中...（此过程可能需要10-20分钟）'})
        else:
            return jsonify({'code': RET.SERVERERROR, 'msg': '该卡已注销！'})


# 批量充值
@user_blueprint.route('/batch/', methods=['POST'])
@login_required
@account_lock
@trans_lock
def card_batch():
    if request.method == 'POST':
        vice_id = g.vice_id
        if vice_id:
            auth_dict = RedisTool.hash_get('svb_vice_auth', vice_id)
            if auth_dict is None:
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
            c_card = auth_dict.get('c_card')
            if c_card == 'F':
                return jsonify({'code': RET.SERVERERROR, 'msg': '抱歉您没有权限执行此操作！'})
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
                        SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.BATCH, card_number,
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
@trans_lock
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
        real_status = SqlData.check_card_real(card_number.strip(), user_id)
        if not real_status:
            results = {"code": RET.SERVERERROR, "msg": "请不要违规操作!"}
            return jsonify(results)
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
        del_status = SqlData.search_delete_in(card_number)
        if del_status:
            return jsonify({'code': RET.SERVERERROR, 'msg': "该卡正在等待删除！"})
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
@trans_lock
@create_card
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
        # top_money = 20
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

        # 已修改，最低20，建的缓存卡量就是20刀
        # 计算充值金额是否在允许范围
        # if not min_top <= int(top_money) <= max_top:
        # if not min_top <= int(top_money):
        #     results = {"code": RET.SERVERERROR, "msg": "充值金额不在允许范围内!"}
        #     return jsonify(results)

        new_card = SqlData.search_valid_card(card_num, top_money)
        if not card_num == len(new_card):
            results = {"code": RET.SERVERERROR, "msg": "库存不足请五分钟后重试"}
            return jsonify(results)
        # 该处修改开卡
        try:
            for i in new_card:
                # 开卡费用
                n_time = xianzai_time()
                card_number = i[1]
                cvc = i[3]
                expiry = i[4]
                card_id = i[5]
                valid_starting_on = i[6]
                valid_ending_on = i[7]
                last4 = i[8]

                SqlData.update_new_card_use(card_id)
                # 插入卡信息
                SqlData.insert_card(card_number, cvc, expiry, card_id, last4, valid_starting_on, valid_ending_on, label, 'T', int(top_money), user_id)

                # 扣去开卡费用
                free_number = SqlData.search_user_field('free', user_id)
                before_balance = SqlData.search_user_field('balance', user_id)

                # 判断是否有可用免费卡量
                if free_number > 0:
                    SqlData.update_user_free_number(-1, user_id)
                    SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.CREATE_CARD, card_number,
                                                 0, before_balance, before_balance, user_id)
                else:
                    create_price_do_money = float(create_price) - float(create_price) * 2
                    SqlData.update_balance(create_price_do_money, user_id)
                    balance = SqlData.search_user_field("balance", user_id)
                    # balance = before_balance - create_price
                    SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.CREATE_CARD, card_number,
                                                 create_price, before_balance, balance, user_id)

                # 扣去充值费用
                before_balance = SqlData.search_user_field('balance', user_id)
                # 当前只有20刀的余额
                top_money = int(top_money)
                top_money_do_money = top_money - top_money * 2
                SqlData.update_balance(top_money_do_money, user_id)
                balance = SqlData.search_user_field("balance", user_id)
                n_time = xianzai_time()
                SqlData.insert_account_trans(n_time, TRANS_TYPE.OUT, DO_TYPE.TOP_UP, card_number,
                                             top_money, before_balance, balance, user_id)
            return jsonify({"code": RET.OK, "msg": "成功开卡! 账户余额为: $"+str(balance)})

        except Exception as e:
            print(e)
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
    data = page_list[int(page) - 1]
    info_list = list()
    for o in data:
        x_time = o.get('time')
        sum_money = SqlData.search_time_sum_money(x_time, user_id)
        o['sum_top'] = round(sum_money, 2)
        info_list.append(o)
    results['data'] = info_list
    results['count'] = len(task_info)
    return jsonify(results)


@user_blueprint.route('/card_table/', methods=['GET'])
@login_required
def card_table():
    return render_template('user/card_table.html')


@user_blueprint.route('/card_decline/', methods=['GET'])
@login_required
def card_decline():
    return render_template('user/card_decline.html')


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

        settle = list()
        clearings = card_detail.get('data').get('clearings')
        for td in clearings:
            settle.append({
                "acquirer_ica": td.get("acquirer_ica"),
                "approval_code": td.get("approval_code"),
                "billing_amount": float(td.get("billing_amount") / 100),
                "billing_currency": td.get("billing_currency"),
                "mcc": td.get("mcc"),
                "mcc_description": td.get("mcc_description"),
                "merchant_amount": float(td.get("merchant_amount") / 100),
                "merchant_currency": td.get("merchant_currency"),
                "merchant_id": td.get("merchant_id"),
                "merchant_name": td.get("merchant_name"),
                "transaction_date_time": td.get("settlement_date"),
            })
        context['pay_list'] = info_list
        context['settle'] = settle
        return render_template('user/card_detail.html', **context)
    except Exception as e:
        logging.error((str(e)))
        return render_template('user/404.html')


@user_blueprint.route('/push_log_settle/', methods=['GET'])
@login_required
def push_log_settle():

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
            sql_1 = " AND card_trans_settle.card_number LIKE '%{}%'".format(card_number)
            if trans_status == "T":
                sql_2 = " AND card_trans_settle.handing_fee != 0"
            else:
                sql_2 = " AND card_trans_settle.handing_fee = 0"
            sql = sql_1 + sql_2
        elif card_number:
            sql = " AND card_trans_settle.card_number LIKE '%{}%'".format(card_number)
        elif trans_status:
            if trans_status == "T":
                sql = " AND card_trans_settle.handing_fee != 0"
            else:
                sql = " AND card_trans_settle.handing_fee = 0"
        else:
            sql = ''
        results = dict()
        results['msg'] = MSG.OK
        results['code'] = RET.OK
        info = SqlData.search_card_trans_settle(user_id, sql)
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


@user_blueprint.route('/card_trans/', methods=['GET'])
@login_required
def card_trans():
    return render_template('user/card_trans.html')


@user_blueprint.route('/card_trans_settle/', methods=['GET'])
@login_required
def card_trans_settle():
    return render_template('user/card_trans_settle.html')


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
        # 处理隐藏注销的卡号
        info_list = list()
        destroy_card = SqlData.search_card_destroy()
        for card in data:
            card_number = card.get('card_number')
            if card_number.strip() in destroy_card:
                card['display'] = '\t556338******' + card_number[-4:]
            else:
                card['display'] = card_number
            info_list.append(card)
        results['data'] = info_list
        results['count'] = len(info)
        return jsonify(results)
    except Exception as e:
        print(e)
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


@user_blueprint.route('/change_account/', methods=["GET", "POST"])
@login_required
@account_lock
def change_account():
    # 判断是否是子账号用户
    vice_id = g.vice_id
    if vice_id:
        return render_template('user/no_auth.html')

    if request.method == 'GET':
        user_name = g.user_name
        context = dict()
        context['user_name'] = user_name
        return render_template('user/change_account.html', **context)
    if request.method == 'POST':
        data = json.loads(request.form.get('data'))
        old_account = data.get('old_account')
        new_account_one = data.get('new_account_one')
        new_account_two = data.get('new_account_two')
        user_id = g.user_id
        account = SqlData.search_user_field('account', user_id)
        results = {'code': RET.OK, 'msg': MSG.OK}
        for i in new_account_one:
            if i.isspace():
                results['code'] = RET.SERVERERROR
                results['msg'] = '账号内包含空格！'
                return jsonify(results)
        if not 6 <= len(new_account_one.strip()) <= 12:
            results['code'] = RET.SERVERERROR
            results['msg'] = '账号不符合要求！'
            return jsonify(results)
        if not (old_account == account):
            results['code'] = RET.SERVERERROR
            results['msg'] = '原账号错误！'
            return jsonify(results)
        if not (new_account_one == new_account_two):
            results['code'] = RET.SERVERERROR
            results['msg'] = '两次账号输入不一致！'
            return jsonify(results)
        ed_name = SqlData.search_user_field_name('account', new_account_one)
        if ed_name:
            results['code'] = RET.SERVERERROR
            results['msg'] = '该用户名已存在!'
            return jsonify(results)
        try:
            SqlData.update_user_field('account', new_account_one, g.user_id)
            session.pop('user_id')
            session.pop('name')
            return jsonify(results)
        except Exception as e:
            logging.error(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.SERVERERROR
            return jsonify(results)


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
        }]
        '''
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
    free_number = SqlData.search_user_field('free', user_id)
    # 支出中有部分退款产生，所以所有支出减去退款才是真实支出
    sum_out_money = SqlData.search_trans_sum(user_id) - SqlData.search_income_money(user_id)
    sum_top_money = SqlData.search_user_field('sum_balance', user_id)
    card_num = SqlData.search_card_status("WHERE user_id={}".format(user_id))
    vice_num = SqlData.search_vice_count(user_id)
    notice = SqlData.search_admin_field('notice')
    up_remain_time = SqlData.search_admin_field('up_remain_time')
    card_remain = SqlData.search_sum_card_balance(user_id)

    # 获取三天前的时间
    three_before = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

    # 获取所有的交易数据
    if user_id == 10:
        res = RedisTool.hash_get('declined', 10)
        three_bili = res.get('three_bili')
        sum_bili = res.get('sum_bili')
    else:
        card_trans = SqlData.search_card_trans(user_id, '')
        decline_num = 0
        trans_num = 0
        for tran in card_trans:
            status = tran.get('status')  # 根据状态来判断给订单是否decline
            trans_time = tran.get('transaction_date_time')
            mat = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", trans_time)
            # 如果匹配时间失败则时间调为4天前(不计数)
            try:
                trans_t = mat.group(0)
            except:
                trans_t = (datetime.datetime.now() - datetime.timedelta(days=4)).strftime("%Y-%m-%d")
            result = verify_login_time(three_before + " 00:00:00", trans_t + " 00:00:00")
            if result and status == 'F':
                decline_num += 1
            if result:
                trans_num += 1

        sum_decline = SqlData.search_trans_count(user_id, "AND card_trans.status='F'")
        three_bili = str(float("%.4f" % (decline_num / trans_num * 100)) if trans_num != 0 else 0) + "%"
        sum_bili = str(float("%.4f" % (sum_decline / len(card_trans) * 100)) if len(card_trans) != 0 else 0) + "%"

    update_t = up_remain_time
    context = dict()
    context['balance'] = balance
    context['sum_out_money'] = sum_out_money
    context['sum_top_money'] = sum_top_money
    context['card_num'] = card_num
    context['card_remain'] = card_remain
    context['update_t'] = update_t
    context['vice_num'] = vice_num
    context['three_bili'] = three_bili
    context['sum_bili'] = sum_bili
    context['notice'] = notice
    context['free_number'] = free_number
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
        res_phone = re.match('^1(3[0-9]|4[5,7]|5[0-9]|6[2,5,6,7]|7[0-9]|8[0-9]|9[1,8,9])\d{8}$', phone)
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
    # ip = request.headers.get('X-Forwarded-For')
    ip = request.remote_addr
    if request.method == 'GET':
        str_data, img = createCodeImage(height=38)
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
            if cus_status == "main":
                user_data = SqlData.search_user_info(user_name)
                if user_data:
                    user_id = user_data.get('user_id')
                    pass_word = user_data.get('password')
                    name = user_data.get('name')
                    if user_pass == pass_word:
                        last_login_time = SqlData.search_user_field('login_time', user_id)
                        if not last_login_time:
                            return jsonify({'code': 307, 'msg': MSG.OK})
                        now_time = xianzai_time()
                        SqlData.update_user_field('login_time', now_time, user_id)
                        session['user_id'] = user_id
                        session['name'] = name
                        session['vice_id'] = None
                        session.permanent = True
                        RedisTool.string_del(ip)
                        return jsonify(results)
                    else:
                        if int(try_number) == 3:
                            results['code'] = 501
                            results['msg'] = MSG.PSWDERROR
                        else:
                            results['code'] = RET.SERVERERROR
                            results['msg'] = MSG.PSWDERROR
                        return jsonify(results)
                else:
                    if int(try_number) == 3:
                        results['code'] = 501
                        results['msg'] = MSG.PSWDERROR
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
                    RedisTool.string_del(ip)
                    return jsonify(results)
                else:
                    if int(try_number) == 3:
                        results['code'] = 501
                        results['msg'] = MSG.PSWDERROR
                    else:
                        results['code'] = RET.SERVERERROR
                        results['msg'] = MSG.PSWDERROR
                    return jsonify(results)

        except Exception as e:
            logging.error(str(e))
            print(e)
            results['code'] = RET.SERVERERROR
            results['msg'] = MSG.DATAERROR
            return jsonify(results)

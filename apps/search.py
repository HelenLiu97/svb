from tools_me.parameter import RET
from . import search_blueprint
from flask import render_template, request, jsonify
from tools_me.mysql_tools import SqlData
from tools_me.svb import svb


@search_blueprint.route('/')
def card_search():
    return render_template('search/index.html')


@search_blueprint.route('/card_detail/')
def card_detail():
    card_num = request.args.get('card')
    if not card_num:
        return jsonify({'code': RET.SERVERERROR, 'msg': '请输出正确的卡号！'})
    card_num = card_num.strip()
    if not 17 > len(card_num) > 3:
        return jsonify({'code': RET.SERVERERROR, 'msg': '请输出正确的卡号！'})
    card_id = SqlData.search_card_like('card_id', card_num)
    if not card_id:
        return jsonify({'code': RET.SERVERERROR, 'msg': '未查询到卡信息，请按要求完善卡号！'})
    card_detail = svb.card_detail(card_id)
    if not card_detail:
        context = """<div class="noFind">
                        <div class="ufo">
                            <i class="seraph icon-test ufo_icon"></i>
                            <i class="layui-icon page_icon layui-icon-loading"></i>
                        </div>
                        <div class="page404">
                            <i class="layui-icon layui-icon-404"></i>
                            <h3>  </h3>
                            <h3>查询失败,请稍后重试!</h3>
                        </div>
                    </div>"""

        return jsonify({'code': RET.OK, 'msg': context})
    card_status = SqlData.search_card_like('status', card_num)
    if card_status == "T":
        available_balance = card_detail.get('data').get('available_balance')
        balance = available_balance / 100
        status = "正常"
    else:
        balance = 0
        status = "已注销"

    pay = ""
    authorizations = card_detail.get('data').get('authorizations')
    for td in authorizations:
        s = "<tr>" + \
        "<td>" + td.get("acquirer_ica") + "</td>" + \
        "<td>" + str(td.get("approval_code")) + "</td>" + \
        "<td>" + str(td.get("billing_amount") / 100) + "</td>" + \
        "<td>" + td.get("billing_currency") + "</td>" + \
        "<td>" + td.get("mcc") + "</td>" + \
        "<td>" + td.get("mcc_description") + "</td>" + \
        "<td>" + str(td.get("merchant_amount") / 100) + "</td>" + \
        "<td>" + td.get("merchant_currency") + "</td>" + \
        "<td>" + td.get("merchant_id") + "</td>" + \
        "<td>" + td.get("merchant_name") + "</td>" + \
        "<td>" + td.get("transaction_date_time") + "</td>" + \
        "<td>" + td.get("merchant_name") + "</td>" + \
        "<td>" + td.get("vcn_response") + "</td>" + \
        "</tr>"
        pay += s
    clear = ""
    clearings = card_detail.get('data').get('clearings')
    for tdd in clearings:
        s = "<tr>" + \
        "<td>" + tdd.get("acquirer_ica") + "</td>" + \
        "<td>" + str(tdd.get("approval_code")) + "</td>" + \
        "<td>" + str(tdd.get("billing_amount") / 100) + "</td>" + \
        "<td>" + tdd.get("billing_currency") + "</td>" + \
        "<td>" + tdd.get("mcc") + "</td>" + \
        "<td>" + tdd.get("mcc_description") + "</td>" + \
        "<td>" + str(tdd.get("merchant_amount") / 100) + "</td>" + \
        "<td>" + tdd.get("merchant_currency") + "</td>" + \
        "<td>" + tdd.get("merchant_id") + "</td>" + \
        "<td>" + tdd.get("merchant_name") + "</td>" + \
        "<td>" + str(tdd.get("settlement_date")) + "</td>" + \
        "</tr>"
        clear += s
    context = """
            <div>
                    <div class="col-lg-12" style="padding-top: 20px;">
                        <p style="line-height: 20px; font-size: 25px;text-align: center" >
                            <i class="layui-icon layui-icon-dollar" style="font-size: 25px"></i> <span style="color: rgb(148,17,36);">卡状态: </span><span>{}</span>
                            <i class="layui-icon layui-icon-note" style="font-size: 25px"></i> <span style="color: #007DDB">卡余额: </span><span>{}</span>
                        </p>
                    </div>
                </div>
        
        
            <div class="layui-tab layui-tab-card">
            
          <ul class="layui-tab-title">
            <li class="layui-this">已经发起的交易</li>
            <li>已经结算的交易</li>
          </ul>
          <div class="layui-tab-content" style="height: 100px">
            <div class="layui-tab-item layui-show">
                <div class="layui-form">
                <button type="button" onclick="tableToExcel('item','data')">导出交易数据</button>
              <table class="layui-table" lay-skin="nob" lay-size="sm" id="item">
                <colgroup>
                </colgroup>
                <thead>
                  <tr>
                    <th>流水号</th>
                    <th>认证码</th>
                    <th>冻结金额</th>
                    <th>冻结币种</th>
                    <th>银行回应</th>
                    <th>mcc</th>
                    <th>描述</th>
                    <th>交易金额</th>
                    <th>交易币种</th>
                    <th>交易ID</th>
                    <th>商户名称</th>
                    <th>交易时间</th>
                    <th>VCN回应信息</th>
                  </tr>
                </thead>
                <tbody>
                {}
                </tbody>
          </table>
        </div>
            </div>
            <div class="layui-tab-item">
                <div class="layui-form">
                <button type="button" onclick="tableToExcel('settle','settle')">导出交易数据</button>
              <table class="layui-table" lay-skin="nob" lay-size="sm" id="settle">
                <colgroup>
                </colgroup>
                <thead>
                  <tr>
                    <th>流水号</th>
                    <th>认证码</th>
                    <th>冻结金额</th>
                    <th>冻结币种</th>
                    <th>mcc</th>
                    <th>描述</th>
                    <th>交易金额</th>
                    <th>交易币种</th>
                    <th>交易ID</th>
                    <th>商户名称</th>
                    <th>结算时间</th>
                  </tr>
                </thead>
                <tbody>
                {}
                </tbody>
          </table>
        </div>
            </div>
          </div>
        </div>""".format(balance, status, pay, clear)
    return jsonify({'code': RET.OK, 'msg': context})


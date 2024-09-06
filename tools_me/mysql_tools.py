from tools_me.db_conn_init import get_my_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s', filename="error.log")


class SqlDataBase(object):
    def __init__(self):
        self.db = get_my_connection()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'inst'):  # 单例
            cls.inst = super(SqlDataBase, cls).__new__(cls, *args, **kwargs)
        return cls.inst

    def connect(self):
        conn, cursor = self.db.getconn()
        return conn, cursor

    def close_connect(self, conn, cursor):
        cursor.close()
        conn.close()

    # 查询某个值在某个字段中
    def search_value_in(self, table_name, value, field):
        sql = "select * from {} where find_in_set('{}',{})".format(table_name, value, field)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        if row:
            return True
        else:
            return False

    # 一下是用户方法-----------------------------------------------------------------------------------------------------

    # 登录查询
    def search_user_info(self, user_name):
        sql = "SELECT id, password, name FROM user_info WHERE BINARY account = '{}'".format(user_name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        try:
            user_data = dict()
            user_data['user_id'] = rows[0][0]
            user_data['password'] = rows[0][1]
            user_data['name'] = rows[0][2]
            return user_data
        except Exception as e:
            return False

    def search_value_count(self, table_name, sql=""):
        sql = "SELECT COUNT(*) FROM {} {}".format(table_name, sql)
        print(sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def search_trans_money(self, start_t, end_t, user_sql=''):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE do_type='充值' AND do_date BETWEEN  '{}' AND '{}' {}".format(
            start_t, end_t, user_sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    # 查询客户子账号登录
    def search_user_vice_info(self, user_name):
        sql = "SELECT id, v_password,user_id FROM vice_user WHERE BINARY v_account = '{}'".format(user_name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        try:
            user_data = dict()
            user_data['user_id'] = rows[0][2]
            user_data['password'] = rows[0][1]
            user_data['vice_id'] = rows[0][0]
            return user_data
        except Exception as e:
            return '账号或密码错误!'

    # 查询用户首页数据信息
    def search_user_index(self, user_id):
        sql = "SELECT create_price, min_top, balance, sum_balance FROM user_info WHERE id = {}".format(
            user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        user_info = dict()
        user_info['create_card'] = rows[0][0]
        user_info['min_top'] = rows[0][1]
        user_info['balance'] = rows[0][2]
        user_info['sum_balance'] = rows[0][3]
        return user_info

    # 用户基本信息资料
    def search_user_detail(self, user_id):
        sql = "SELECT account, phone_num, balance FROM user_info WHERE id = {}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        user_info = dict()
        user_info['account'] = rows[0][0]
        user_info['phone_num'] = rows[0][1]
        user_info['balance'] = rows[0][2]
        return user_info

    # 查询用户的某一个字段信息
    def search_user_field(self, field, user_id):
        sql = "SELECT {} FROM user_info WHERE id = {}".format(field, user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    # 更新用户的某一个字段信息(str)
    def update_user_field(self, field, value, user_id):
        sql = "UPDATE user_info SET {} = '{}' WHERE id = {}".format(field, value, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_user_field_int(self, field, value, user_id):
        sql = "UPDATE user_info SET {} = {} WHERE id = {}".format(field, value, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_user_bala(self, field, value, user_id):
        sql = "UPDATE user_info SET {} = {} WHERE id = {}".format(field, value, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_top_history_acc(self, user_id):
        sql = "SELECT * FROM top_up WHERE user_id={}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['pay_num'] = i[1]
                info_dict['time'] = str(i[2])
                info_dict['money'] = i[3]
                info_dict['before_balance'] = i[4]
                info_dict['balance'] = i[5]
                info_list.append(info_dict)
            return info_list

    def search_sum_card_balance(self, user_id):
        sql = "SELECT SUM(card_amount) FROM card_info WHERE user_id={} AND card_status='T'".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows[0]:
            return 0
        return rows[0]

    def search_sum_card_remain(self):
        sql = "SELECT SUM(card_amount) FROM card_info WHERE card_status='T'"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows[0]:
            return 0
        return rows[0]

    def search_one_card_status(self, crad_no):
        sql = "SELECT card_status from card_info WHERE card_number='{}'".format(crad_no)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if rows[0] == 'T':
            return True
        return False

    def search_card_field(self, field, crad_no):
        sql = "SELECT {} from card_info WHERE card_number='{}'".format(field, crad_no)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        return rows[0]

    def search_card_like(self, field, card_no):
        sql = "SELECT {} from card_info WHERE card_number LIKE '%{}'".format(field, card_no)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if len(rows) != 1:
            return False
        return rows[0][0]

    def check_card_real(self, card_number, user_id):
        sql = "SELECT * from card_info WHERE card_number='{}' AND user_id={}".format(card_number, user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if rows:
            return True
        return False

    def update_card_info_card_no(self, field, value, card_no):
        sql = "UPDATE card_info SET {}='{}' WHERE card_number='{}'".format(field, value, card_no)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新卡信息失败!")
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_card_balance(self, balance, card_id):
        sql = "UPDATE card_info SET card_amount={} WHERE card_id={}".format(balance, card_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新卡余额失败!")
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_table_count(self, table_name):
        sql = "SELECT COUNT(*) FROM {}".format(table_name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def search_card_info(self, user_id, status, sql1, sql2):
        sql = "SELECT * FROM card_info WHERE user_id={} AND card_status!='{}' {} {}".format(user_id, status, sql1, sql2)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['id'] = i[0]
                info_dict['card_number'] = "\t" + i[2]
                info_dict['expire'] = i[3]
                info_dict['cvc'] = i[5]
                info_dict['valid_start_on'] = str(i[6])
                info_dict['valid_end_on'] = str(i[7])
                info_dict['create_time'] = str(i[8])
                info_dict['label'] = i[9]
                info_dict['status'] = '正常' if i[10] == 'T' else '注销'
                info_dict['detail'] = "双击查看"
                info_list.append(info_dict)
            return info_list

    def search_card_select(self, user_id, name_sql, card_sql, label, time_sql):
        sql = "SELECT * FROM card_info WHERE user_id={} {} {} {} {}".format(user_id, name_sql, card_sql, label,
                                                                            time_sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['card_no'] = "\t" + i[2]
                info_dict['act_time'] = str(i[4])
                info_dict['card_name'] = i[5]
                info_dict['label'] = i[6]
                expire = i[7]
                if expire:
                    info_dict['expire'] = "\t" + expire[4:6] + "/" + expire[2:4]
                else:
                    info_dict['expire'] = ""
                info_dict['expire'] = i[7]
                info_dict['cvv'] = "\t" + i[8]
                info_list.append(info_dict)
            return info_list

    def search_logout_card(self, user_id):
        sql = "SELECT card_number FROM card_info WHERE user_id={} AND status='F'".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_list.append(i[0])
        return info_list

    def insert_card(self, card_number, cvc, expiry, card_id, last4, valid_start_on, valid_end_on, label, status,
                    balance, user_id):
        sql = "INSERT INTO card_info(card_number, cvc, expiry, card_id, last4, valid_start_on, valid_end_on, label, " \
              "card_status, card_amount, user_id) VALUES('{}','{}','{}',{},'{}','{}','{}','{}','{}',{},{})" \
            .format(card_number, cvc, expiry, card_id, last4, valid_start_on, valid_end_on, label, status, balance,
                    user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入卡信息失败!CardId:" + str(card_id) + '; ' + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_account_trans(self, date, trans_type, do_type, card_no, do_money, before_balance,
                             balance, user_id):
        sql = "INSERT INTO user_trans(do_date, trans_type, do_type, card_no, do_money, before_balance," \
              " balance, user_id) VALUES('{}','{}','{}','{}',{},{},{},{})".format(date, trans_type, do_type,
                                                                                  card_no, do_money, before_balance,
                                                                                  balance, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加用户交易记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_account_trans(self, account_id, card_sql, time_sql, type_sql="", do_sql=""):
        sql = "SELECT * FROM user_trans WHERE user_id = {} {} {} {} {}".format(account_id, card_sql, time_sql, type_sql,
                                                                               do_sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['date'] = str(i[1])
            info_dict['trans_type'] = i[2]
            info_dict['do_type'] = i[3]
            info_dict['card_no'] = "\t" + i[4]
            info_dict['do_money'] = i[5] if i[2] == '收入' else '-' + i[5]
            info_dict['before_balance'] = i[6]
            info_dict['balance'] = i[7]
            info_list.append(info_dict)
        return info_list

    def search_income_money(self, account_id):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE trans_type='收入' and user_id={}".format(account_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows[0]:
            return 0
        return rows[0]

    def search_trans_sum(self, account_id):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE trans_type='支出' and user_id={}".format(account_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows[0]:
            return 0
        return rows[0]
        # hand_money = rows[0][1]
        # sum_money = do_money + hand_money

    def insert_account_vice(self, v_account, v_password, c_card, top_up, refund, del_card, up_label, user_id):
        sql = "INSERT INTO vice_user(v_account, v_password, c_card, top_up, refund, del_card, up_label," \
              " user_id) VALUES ('{}','{}','{}','{}','{}','{}','{}',{})".format(v_account, v_password, c_card,
                                                                                top_up, refund, del_card,
                                                                                up_label, user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        conn.commit()
        self.close_connect(conn, cursor)

    def del_vice(self, vice_id):
        sql = "DELETE FROM vice_user WHERE id = {}".format(vice_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("删除失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_vice_field(self, field, value, vice_id):
        sql = "UPDATE vice_user SET {}='{}' WHERE id={}".format(field, value, vice_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新子账号信息失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_vice_count(self, user_id):
        sql = "SELECT COUNT(*) FROM vice_user WHERE user_id={}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def search_vice_id(self, v_account):
        sql = "SELECT id FROM vice_user WHERE v_account='{}'".format(v_account)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def search_one_acc_vice(self, user_id):
        sql = "SELECT * FROM vice_user WHERE id={}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        vice = dict()
        if row:
            vice['vice_id'] = row[0]
            vice['v_account'] = row[1]
            vice['v_password'] = row[2]
            vice['c_card'] = row[3]
            vice['top_up'] = row[4]
            vice['refund'] = row[5]
            vice['del_card'] = row[6]
            vice['up_label'] = row[7]
            vice['user_id'] = row[8]
        return vice

    def search_acc_vice(self, user_id):
        sql = "SELECT * FROM vice_user WHERE user_id={}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if rows:
            for row in rows:
                vice = dict()
                vice['vice_id'] = row[0]
                vice['v_account'] = row[1]
                vice['v_password'] = row[2]
                vice['c_card'] = row[3]
                vice['top_up'] = row[4]
                vice['refund'] = row[5]
                vice['del_card'] = row[6]
                vice['up_label'] = row[7]
                vice['account_id'] = row[8]
                info_list.append(vice)
            return info_list
        return info_list

    # 一下是中介使用方法-------------------------------------------------------------------------------------------------

    # 查询中介登录信息

    def search_middle_login(self, account):
        sql = "SELECT id, password FROM middle WHERE BINARY account='{}'".format(account)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows

    # 查询中介的你某一个字段信息
    def search_middle_field(self, field, middle_id):
        sql = "SELECT {} FROM middle WHERE id={}".format(field, middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

        # 用户基本信息资料

    def search_middle_detail(self, middle_id):
        sql = "SELECT account, phone_num, card_price FROM middle WHERE id = {}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        user_info = dict()
        user_info['account'] = rows[0][0]
        user_info['phone_num'] = rows[0][1]
        user_info['card_price'] = rows[0][2]
        return user_info

    # 更新用户的某一个字段信息(str)
    def update_middle_field(self, field, value, middle_id):
        sql = "UPDATE middle SET {} = '{}' WHERE id = {}".format(field, value, middle_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新中介字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_user_field_middle(self, middle_id):
        sql = "SELECT id, name FROM user_info WHERE middle_id = {}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        account_list = list()
        if not rows:
            return account_list
        for i in rows:
            info_dict = dict()
            info_dict['id'] = i[0]
            info_dict['name'] = i[1]
            account_list.append(info_dict)
        return account_list

    def search_user_middle_info(self, middle_id):
        sql = "SELECT id, name, sum_balance, balance FROM user_info WHERE middle_id = {}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        account_list = list()
        if not rows:
            return account_list
        for i in rows:
            info_dict = dict()
            info_dict['id'] = i[0]
            info_dict['name'] = i[1]
            info_dict['sum_balance'] = i[2]
            info_dict['balance'] = i[3]
            account_list.append(info_dict)
        return account_list

    def search_card_count(self, account_id, time_range):
        sql = "SELECT COUNT(*) FROM user_trans WHERE user_id={} AND do_type='开卡' {}".format(account_id,
                                                                                            time_range)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def insert_middle_money(self, middle_id, start_time, end_time, card_num, create_price, sum_money, create_time,
                            pay_status, detail):
        sql = "INSERT INTO middle_money(middle_id, start_time, end_time, card_num, create_price, sum_money," \
              " create_time, pay_status, detail) VALUES ({},'{}','{}',{},{},{},'{}','{}','{}')".format(
            middle_id, start_time, end_time, card_num, create_price, sum_money, create_time, pay_status, detail)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入中介开卡费记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_middle_money(self, middle_id):
        sql = "SELECT * FROM middle_money WHERE middle_id={}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['id'] = i[0]
            info_dict['start_time'] = str(i[2])
            info_dict['end_time'] = str(i[3])
            info_dict['card_num'] = i[4]
            info_dict['create_price'] = i[5]
            info_dict['sum_money'] = i[6]
            info_dict['create_time'] = str(i[7])
            info_dict['pay_status'] = i[8]
            if i[9]:
                info_dict['pay_time'] = str(i[9])
            else:
                info_dict['pay_time'] = ""
            info_list.append(info_dict)
        return info_list

    def search_middle_money_field(self, field, info_id):
        sql = "SELECT {} FROM middle_money WHERE id={}".format(field, info_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    # 以下是终端使用接口-------------------------------------------------------------------------------------------------

    # 验证登录
    def search_admin_login(self, account, password):
        sql = "SELECT id, name FROM admin WHERE BINARY account='{}' AND BINARY password='{}'".format(account, password)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0], rows[0][1]

    def search_account_info(self, info):
        sql = "SELECT * FROM user_info {}".format(info)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        account_list = list()
        if not rows:
            return account_list
        else:
            for i in rows:
                account_dict = dict()
                account_dict['u_id'] = i[0]
                account_dict['account'] = i[1]
                account_dict['password'] = i[2]
                account_dict['name'] = i[4]
                account_dict['create_price'] = i[5]
                account_dict['min_top'] = i[6]
                account_dict['max_top'] = i[7]
                account_dict['credit_hand'] = i[8]
                account_dict['balance'] = i[10]
                account_dict['sum_balance'] = i[11]
                account_dict['last_login_time'] = str(i[9])
                account_dict['free_number'] = str(i[13])
                account_dict['hand'] = i[14]
                account_list.append(account_dict)
            return account_list

    def update_account_field(self, field, value, name):
        sql = "UPDATE user_info SET {}='{}' WHERE name='{}'".format(field, value, name)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_user_field_name(self, field, name):
        sql = "SELECT {} FROM user_info WHERE name = '{}'".format(field, name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        return rows[0][0]

    def update_user_balance(self, money, user_id):
        sql = "UPDATE user_info set sum_balance=sum_balance+{}, balance=balance+{} WHERE id={}".format(money, money, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户余额失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_user_free_number(self, number, user_id):
        sql = "UPDATE user_info set free=free+{} WHERE id={}".format(number, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户已付费卡量失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_top_up(self, pay_num, now_time, money, before_balance, balance, user_id, text=''):
        sql = "INSERT INTO top_up(pay_num, `time`, money, before_balance, balance, user_id, remark) VALUES ('{}','{}',{},{},{},{},'{}')".format(
            pay_num, now_time, money, before_balance, balance, user_id, text)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入用户充值记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_top_history(self, sql_line):
        sql = "SELECT * FROM top_up LEFT JOIN user_info ON user_info.id=top_up.user_id WHERE user_id != '' {}".format(
            sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['pay_num'] = i[1]
                info_dict['time'] = str(i[2])
                info_dict['money'] = i[3]
                info_dict['before_balance'] = i[4]
                info_dict['balance'] = i[5]
                info_dict['user_id'] = i[6]
                info_dict['remark'] = i[7]
                info_dict['name'] = i[12]
                if 'zfb' in i[1]:
                    info_dict['source'] = 'zfb'
                elif 'ustd' in i[1]:
                    info_dict['source'] = 'ustd'
                elif 'bank' in i[1]:
                    info_dict['source'] = '银行卡'
                else:
                    info_dict['source'] = ''
                info_list.append(info_dict)
            return info_list

    def admin_info(self):
        sql = "SELECT account, password, name, balance FROM admin"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0], rows[0][1], rows[0][2], rows[0][3]

    def search_admin_field(self, field):
        sql = "SELECT {} FROM admin".format(field)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def update_admin_field(self, field, value):
        sql = "UPDATE admin SET {}='{}'".format(field, value)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新ADMIN字段失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_account(self, account, password, phone_num, name, create_price, min_top, middle_id, hand, ustd_hand):
        sql = "INSERT INTO user_info(account, password, phone_num, name, create_price, min_top, middle_id, hand, card_num) " \
              "VALUES ('{}','{}','{}','{}',{},{},{},{},{})".format(account, password, phone_num, name, create_price,
                                                             min_top, middle_id, hand, ustd_hand)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加用户失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_middle_ed(self, name):
        sql = "SELECT COUNT(*) FROM middle WHERE name ='{}'".format(name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def insert_middle(self, account, password, name, phone_num, price_one, price_two, price_three):
        sql = "INSERT INTO middle(account, password, name, phone_num, price_one, price_two, price_three) " \
              "VALUES ('{}','{}','{}','{}',{},{},{})".format(account, password, name, phone_num, price_one, price_two,
                                                             price_three)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加中介失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_middle_info(self):
        sql = "SELECT * FROM middle"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            middle_id = i[0]
            info_dict['middle_id'] = middle_id
            info_dict['cus_num'] = self.search_acc_middle(middle_id)
            info_dict['account'] = i[1]
            info_dict['password'] = i[2]
            info_dict['name'] = i[3]
            info_dict['phone_num'] = i[4]
            info_dict['price_one'] = i[5]
            info_dict['price_two'] = i[6]
            info_dict['price_three'] = i[7]
            info_list.append(info_dict)
        return info_list

    def search_acc_middle(self, middle_id):
        sql = "SELECT COUNT(*) FROM user_info WHERE middle_id={}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def search_cus_list(self, sql_line=""):
        sql = "SELECT name FROM user_info {}".format(sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        cus_list = list()
        if not rows:
            return cus_list
        for i in rows:
            cus_list.append(i[0])
        return cus_list

    def update_middle_field_int(self, field, value, name):
        sql = "UPDATE middle SET {} = {} WHERE name = '{}'".format(field, value, name)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新中介字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_middle_field_str(self, field, value, name):
        sql = "UPDATE middle SET {} = '{}' WHERE name = '{}'".format(field, value, name)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新中介字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_middle_name(self, field, name):
        sql = "SELECT {} FROM middle WHERE name='{}'".format(field, name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def search_name_info(self):
        sql = "SELECT last_name, female, man FROM name_info"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        last_name = list()
        female = list()
        for i in rows:
            last_name.append(i[0])
            female.append(i[1])
            female.append(i[2])
        info_dict = dict()
        info_dict['last_name'] = last_name
        info_dict['female'] = female
        return info_dict

    def search_middle_id(self):
        sql = "SELECT id FROM middle"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_list.append(i[0])
        return info_list

    def search_user_field_admin(self):
        sql = "SELECT id, `name` FROM user_info"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        account_list = list()
        if not rows:
            return account_list
        for i in rows:
            info_dict = dict()
            info_dict['id'] = i[0]
            info_dict['name'] = i[1]
            account_list.append(info_dict)
        return account_list

    def search_middle_money_admin(self):
        sql = "SELECT middle_money.*, middle.`name` FROM middle_money LEFT JOIN middle ON middle.id = middle_money.middle_id"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['id'] = i[0]
            info_dict['start_time'] = str(i[2])
            info_dict['end_time'] = str(i[3])
            info_dict['card_num'] = i[4]
            info_dict['create_price'] = i[5]
            info_dict['sum_money'] = i[6]
            info_dict['create_time'] = str(i[7])
            info_dict['pay_status'] = i[8]
            if i[9]:
                info_dict['pay_time'] = str(i[9])
            else:
                info_dict['pay_time'] = ""
            info_dict['name'] = i[12]
            if i[6]:
                info_list.append(info_dict)
        return info_list

    def update_middle_sub(self, pay_status, pay_time, info_id):
        sql = "UPDATE middle_money SET pay_status = '{}', pay_time = '{}' WHERE id = {}".format(pay_status, pay_time,
                                                                                                info_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新中介费确认失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_card_info_admin(self, sql_line):
        sql = "SELECT * FROM card_info {}".format(sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['card_id'] = i[1]
            info_dict['card_no'] = "\t" + i[2]
            info_dict['expire'] = i[3]
            info_dict['cvv'] = i[5]
            info_dict['valid_start_on'] = str(i[6])
            info_dict['valid_end_on'] = str(i[7])
            info_dict['label'] = i[9]
            info_dict['status'] = '正常' if i[10] == 'T' else '注销'
            info_dict['user_name'] = self.search_user_field('name', i[11])
            info_dict['user_id'] = i[11]
            info_dict['detail'] = '双击查看'
            info_list.append(info_dict)
        return info_list

    def search_card_destroy(self):
        sql = "SELECT card_number FROM card_info WHERE card_status='F'"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        for i in rows:
            info_list.append(i[0])
        return info_list

    def search_trans_admin(self, cus_sql, card_sql, time_sql, do_sql, sql):
        sql = "SELECT user_trans.*, user_info.name FROM user_trans LEFT JOIN user_info ON user_trans.user_id" \
              " = user_info.id WHERE user_trans.do_date != ''  {} {} {} {} {}".format(cus_sql, card_sql, time_sql,
                                                                                      do_sql, sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['date'] = str(i[1])
            info_dict['trans_type'] = i[2]
            info_dict['do_type'] = i[3]
            info_dict['card_no'] = "\t" + i[4]
            info_dict['do_money'] = i[5] if i[2] == '收入' else '-' + i[5]
            info_dict['before_balance'] = i[6]
            info_dict['balance'] = i[7]
            info_dict['cus_name'] = i[9]
            info_list.append(info_dict)
        return info_list

    def search_trans_sum_admin(self):
        sql = "SELECT SUM(do_money), SUM(hand_money) FROM account_trans WHERE trans_type='支出'"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows[0][0]:
            return 0
        do_money = rows[0][0]
        hand_money = rows[0][1]
        sum_money = do_money + hand_money
        return sum_money

    def search_user_sum_balance(self):
        sql = "SELECT SUM(sum_balance) FROM account"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def insert_account_log(self, n_time, customer, balance, out_money, sum_balance):
        sql = "INSERT INTO account_log(log_time, customer, balance, out_money, sum_balance) VALUES ('{}','{}',{},{},{})".format(
            n_time, customer, balance, out_money, sum_balance)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加用户余额记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_account_log(self, cus_sql, time_sql):
        sql = "SELECT * FROM account_log WHERE log_time != '' {} {}".format(cus_sql, time_sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['log_time'] = str(i[1])
            info_dict['customer'] = i[2]
            info_dict['balance'] = i[3]
            info_dict['out_money'] = i[4]
            info_dict['sum_balance'] = i[5]
            info_list.append(info_dict)
        return info_list

    def search_card_status(self, sql_line):
        sql = "SELECT COUNT(*) FROM card_info {}".format(sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def label_data(self, user_id):
        sql = "SELECT label FROM account WHERE id = {}".format(user_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows

    def search_bento_sum_money(self, x_time, user_id):
        sql = "SELECT do_money FROM account_trans where do_type='退款' and account_id={} and do_date <= '{}'".format(
            user_id, x_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchall()
        self.close_connect(conn, cursor)
        res = 0
        for i in row:
            v = float(i[0])
            if v >= 0:
                res += v
        return res

    def search_bento_sum_refund(self, x_time, user_id):
        sql = "SELECT do_money FROM account_trans where do_type='转移退款' and account_id={} and do_date <= '{}'".format(
            user_id, x_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchall()
        self.close_connect(conn, cursor)
        res = 0
        for i in row:
            v = float(i[0]) if i[0] else 0
            if v >= 0:
                res += v
        return res

    def bento_refund_data(self, sql_all):
        sql = 'SELECT account_trans.do_date, account_trans.card_no, account_trans.do_money, account_trans.before_balance, account_trans.balance, account.name, account_trans.card_no, account_trans.account_id, account_trans.do_type FROM account_trans LEFT JOIN account ON account.id = account_trans.account_id where account_trans.do_type LIKE "%退款%" {}'.format(
            sql_all)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        data = []
        for row in rows:
            data.append({
                "before_balance": row[3],
                "balance": row[4],
                "money": row[2],
                "name": row[5],
                "time": str(row[0]),
                "trans_type": "删卡退款" if row[8] == "退款" else row[8],
                "pay_num": row[6],
                "user_id": row[7],
            })
        return data

    def search_user_id(self, account):
        sql = "SELECT id FROM user_info WHERE account='{}'".format(account)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    # pay
    def search_user_check(self, name, account):
        sql = "SELECT id FROM user_info WHERE name='{}' AND account='{}'".format(name, account)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        return rows[0][0]

    # pay
    def search_qr_code(self, sql):
        sql = "SELECT * FROM qr_code {}".format(sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['qr_code'] = i[1]
            info_dict['qr_date'] = str(i[2])
            info_dict['sum_money'] = i[3]
            if i[4] == 0:
                info_dict['status'] = '正常'
            elif i[4] == 1:
                info_dict['status'] = '锁定'
            else:
                info_dict['status'] = '置顶'
            info_list.append(info_dict)
        return info_list

    def search_time_sum_money(self, x_time, user_id):
        sql = "SELECT sum(money) FROM top_up WHERE user_id={} AND time <= '{}'".format(user_id, x_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchall()
        self.close_connect(conn, cursor)
        res = 0
        for i in row:
            v = i[0]
            if v >= 0:
                res += v
        return res

    # pay
    def insert_pay_log(self, pay_time, pay_money, top_money, ver_code, status, phone, url, account_id, ex_change, hand):
        sql = "INSERT INTO pay_log(pay_time, pay_money, top_money, ver_code, status, phone, url, user_id, ex_change, hand) VALUES ('{}',{},{},'{}','{}','{}', '{}',{}, '{}','{}')".format(
            pay_time, pay_money, top_money, ver_code, status, phone, url, account_id, ex_change, hand)
        conn, cursor = self.connect()

        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入用户请求充值信息失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # pay
    def search_pay_log(self, status):
        sql = "SELECT pay_time,pay_money,top_money,top_up.before_balance,top_up.balance,pay_log.`status`,ver_time,url, user_info.`name`,user_info.id FROM pay_log LEFT JOIN user_info ON pay_log.user_id=user_info.id LEFT JOIN top_up on pay_log.user_id=top_up.user_id AND pay_log.ver_time=top_up.time WHERE pay_log.`status`='{}'".format(
            status)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['pay_time'] = str(i[0])
            info_dict['pay_money'] = i[1]
            info_dict['top_money'] = i[2]
            info_dict['before_balance'] = i[3]
            info_dict['balance'] = i[4]
            info_dict['status'] = i[5]
            info_dict['ver_time'] = str(i[6])
            info_dict['url'] = i[7]
            info_dict['cus_name'] = i[8]
            info_dict['cus_id'] = i[9]
            info_dict['bank_msg'] = i[7] if "http" not in i[7] else ""
            info_list.append(info_dict)
        return info_list

    # pay
    def search_pay_code(self, field, cus_name, pay_time):
        sql = "SELECT {} from pay_log LEFT JOIN user_info ON pay_log.user_id=user_info.id WHERE user_info.`name`='{}' AND pay_time='{}'".format(
            field, cus_name, pay_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return ''
        return rows[0][0]

    # pay
    def update_qr_money(self, file, value, url):
        sql = "UPDATE qr_code SET {}={}+{} WHERE url='{}'".format(file, file, value, url)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新收款码金额失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # pay
    def update_pay_status(self, pay_status, t, cus_name, pay_time):
        sql = "UPDATE pay_log SET status='{}',ver_time='{}' WHERE user_id={} AND pay_time='{}'".format(pay_status, t,
                                                                                                          cus_name,
                                                                                                          pay_time)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("确认充值状态失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # pay
    def del_pay_log(self, user_id, pay_time):
        # sql = "DELETE FROM pay_log WHERE account_id = {} AND pay_time='{}'".format(user_id, pay_time)
        sql = "UPDATE pay_log SET status='已删除' WHERE user_id = {} AND pay_time='{}'".format(user_id, pay_time)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("删除失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # pay
    def insert_qr_code(self, url, up_date):
        sql = "INSERT INTO qr_code(url, up_date) VALUES('{}', '{}')".format(url, up_date)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加收款二维码失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_balance(self, money, id):
        sql = "UPDATE user_info set balance=balance+{} WHERE id={}".format(money, id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新用户余额失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # qr_code
    def search_qr_field(self, field, url):
        sql = "SELECT {} FROM qr_code WHERE url='{}'".format(field, url)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        return rows[0][0]

    # qr_code
    def update_qr_info(self, file, value, url):
        sql = "UPDATE qr_code SET {}={} WHERE url='{}'".format(file, value, url)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新收款码状态失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # qr_code
    def del_qr_code(self, url):
        sql = "DELETE FROM qr_code WHERE url = '{}'".format(url)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
        self.close_connect(conn, cursor)

    # recharge
    def recharge_add_account(self, name, username, password):
        sql = "INSERT INTO verify_account(u_name, u_account, u_password) VALUES('{}', '{}', '{}')".format(name, username,
                                                                                                       password)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("add recharge account failed" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # recharge
    def recharge_all_account(self):
        sql = "SELECT * FROM verify_account"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        data = []
        for row in rows:
            data.append({
                "user_id": row[0],
                "name": row[1],
                "username": row[2],
                "password": row[3],
            })
        return data

    # recharge
    def recharge_search_user(self, username):
        sql = "SELECT * FROM recharge_account where username='{}'".format(username)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if rows:
            return {
                "password": rows[3]
            }
        return ""

    # bank_info
    def search_bank_info(self, sql_line=''):
        sql = "SELECT * FROM bank_info {}".format(sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        data = []
        for row in rows:
            if row:
                if row[6] == 0:
                    status = '正常'
                elif row[6] == 1:
                    status = '锁定'
                else:
                    status = '置顶'
                data.append({
                    "bank_name": row[1],
                    "bank_number": row[2],
                    "bank_address": row[3],
                    "day_money": str(row[4]),
                    "money": str(row[5]),
                    "status": status
                })
            else:
                return ""
        return data

    # bank_info
    def insert_bank_info(self, bank_name, bank_number, bank_address):
        sql = "INSERT INTO bank_info(bank_name, bank_number, bank_address) VALUES('{}', '{}', '{}')".format(bank_name,
                                                                                                            bank_number,
                                                                                                            bank_address)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("add bank_info failed" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # bank_info
    def del_benk_data(self, bank_number):
        sql = "DELETE FROM bank_info WHERE bank_number='{}'".format(bank_number)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.warning(str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    # bank_info
    def bank_min_data(self):
        sql = "select * from bank_info ORDER BY money asc"
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        if row:
            return {
                "bank_name": row[1],
                "bank_number": row[2],
                "bank_address": row[3],
                "day_money": row[4]
            }

    # bank_update
    def search_bank_top(self, bank_number):
        sql = "select money from bank_info where bank_number='{}'".format(bank_number[0])
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def search_bank_status(self, bank_number):
        sql = "SELECT status FROM bank_info WHERE bank_number='{}'".format(bank_number)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def update_bank_status(self, bank_number, status):
        sql = "UPDATE bank_info SET status={} WHERE bank_number='{}'".format(status, bank_number)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新银行收款信息失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_bank_top(self, bank_number, once_money, bank_money):
        sql = "UPDATE bank_info SET money='{}',day_money=day_money+{} WHERE bank_number='{}'".format(bank_money,
                                                                                                     once_money,
                                                                                                     bank_number[0])
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新银行收款信息失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_bank_day_top(self, bank_number, bank_money):
        sql = "UPDATE bank_info SET day_money={}  WHERE bank_number='{}'".format(bank_money, bank_number)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新银行收款信息失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def bento_chart_data(self, alias, time_range):
        sql = "SELECT COUNT(*) FROM user_trans WHERE do_type='开卡' and user_id={} {}".format(alias, time_range)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]

    def middle_user_id(self, name):
        sql = "SELECT id FROM middle WHERE name='{}'".format(name)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    def middle_user_data(self, middle_id):
        sql = "SELECT * FROM account WHERE middle_id={}".format(middle_id)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        data = []
        for row in rows:
            data.append({
                "account": row[1],
                "password": row[2],
                "name": row[4],
                "balance": row[9],
                "sum_balance": row[10],
                "label": row[12],
            })

        return data

    def search_table_sum(self, field, table, sql_line):
        sql = "SELECT SUM({}) FROM {} {}".format(field, table, sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if not rows[0]:
            return 0
        return rows[0]

    def del_recharge_acc(self, user_id):
        sql = "DELETE FROM verify_account WHERE id = {}".format(user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
        self.close_connect(conn, cursor)

    # 判断字符是否已包含在字段内
    def find_in_set(self, table, value, field):
        sql = "SELECT * FROM {} WHERE find_in_set('{}', {})".format(table, value, field)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if rows:
            return True
        else:
            return False

    # 更新用户的某一个字段信息(str)
    def update_recharge_account(self, field, value, user_id):
        sql = "UPDATE verify_account SET {} = '{}' WHERE id = {}".format(field, value, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新充值用户字段" + field + "失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_verify_login(self, u_account, u_password):
        sql = "SELECT id, u_name FROM verify_account WHERE BINARY u_account = '{}' AND BINARY u_password='{}'".format(
            u_account, u_password)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        user_data = dict()
        if not rows:
            return user_data
        user_data['user_id'] = rows[0][0]
        user_data['user_name'] = rows[0][1]
        return user_data

    def insert_card_trans(self, card_number, acquirer_ica, approval_code, billing_amount, billing_currency,
                          issuer_reponse, mcc,
                          mcc_description, merchant_amount, merchant_currency, merchant_id, merchant_name,
                          transaction_date_time, transaction_type, vcn_response, card_id, status, user_name, user_id):
        # 这么写sql是为了插入的交易数据重复，因为交易信息内没有唯一标识
        sql = "Insert into card_trans(`card_number`, `acquirer_ica`,`approval_code`, `billing_amount`,`billing_currency`," \
              "`issuer_reponse`,`mcc`,`mcc_description`,`merchant_amount`,`merchant_currency`,`merchant_id`," \
              "`merchant_name`,transaction_date_time,`transaction_type`,`vcn_response`, `card_id`, `status`, `user_name`, `user_id`)select '{0}','{1}','{2}',{3},'{4}','{5}','{6}','{7}',{8},'{9}','{10}','{11}','{12}','{13}','{14}',{15},'{16}','{17}', {18} from DUAL where not exists (select * from card_trans where `card_number`='{0}' and `acquirer_ica` = '{1}' and `approval_code`='{2}' and `billing_amount`={3} and `billing_currency`='{4}' and " \
              "`issuer_reponse`='{5}' and `mcc`='{6}' and `mcc_description` ='{7}' and `merchant_amount` = {8} and  `merchant_currency`= '{9}' and `merchant_id`='{10}' and " \
              "`merchant_name`='{11}' and `transaction_date_time`='{12}' and `transaction_type`='{13}' and `vcn_response`='{14}' and  `card_id`={15} and  `status`='{16}' and `user_name`='{17}' and `user_id`={18})".format(
            card_number, acquirer_ica, approval_code, billing_amount, billing_currency, issuer_reponse, mcc,
            mcc_description,
            merchant_amount, merchant_currency, merchant_id, merchant_name, transaction_date_time, transaction_type,
            vcn_response, card_id, status, user_name, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入卡信息失败!CardId:" + str(card_id) + '; ' + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_card_trans_settle(self, card_number, acquirer_ica, approval_code, authorization_date, billing_amount,
                                 billing_currency,
                                 clearing_type, exchange_rate, mcc,
                                 mcc_description, merchant_amount, merchant_currency, merchant_id, merchant_name,
                                 settlement_date, card_id, user_name, user_id):
        # 这么写sql是为了插入的交易数据重复，因为交易信息内没有唯一标识
        sql = "Insert into card_trans_settle(`card_number`, `acquirer_ica`,`approval_code`, `authorization_date`,`billing_amount`,`billing_currency`," \
              "`clearing_type`, `exchange_rate`,`mcc`,`mcc_description`,`merchant_amount`,`merchant_currency`,`merchant_id`," \
              "`merchant_name`, `settlement_date`, `card_id`, `user_name`, `user_id`)select '{0}','{1}','{2}','{3}',{4},'{5}','{6}','{7}',{8},'{9}','{10}','{11}','{12}','{13}','{14}',{15},'{16}',{17} " \
              "from DUAL where not exists (select * from card_trans_settle where `card_number`='{0}' and `acquirer_ica` = '{1}' and `approval_code`='{2}' and `authorization_date`='{3}' and `billing_amount`={4} and `billing_currency`='{5}' and " \
              "`clearing_type`='{6}' and `exchange_rate`='{7}' and `mcc`='{8}' and `mcc_description` ='{9}' and `merchant_amount` = {10} and  `merchant_currency`= '{11}' and `merchant_id`='{12}' and " \
              "`merchant_name`='{13}' and `settlement_date`='{14}' and `card_id`='{15}' and `user_name`='{16}' and `user_id`={17})".format(card_number, acquirer_ica, approval_code, authorization_date, billing_amount,
                                 billing_currency,
                                 clearing_type, exchange_rate, mcc,
                                 mcc_description, merchant_amount, merchant_currency, merchant_id, merchant_name,
                                 settlement_date, card_id, user_name, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入卡信息失败!CardId:" + str(card_id) + '; ' + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_settle_trans(self):
        sql = "SELECT `id`, card_number, billing_amount, merchant_currency FROM card_trans_settle WHERE handing_fee is null;"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['info_id'] = i[0]
            info_dict['card_number'] = i[1]
            info_dict['billing_amount'] = i[2]
            info_dict['merchant_currency'] = i[3]
            info_list.append(info_dict)
        return info_list

    def update_settle_handing(self, money, info_id):
        sql = "UPDATE card_trans_settle SET expense = {} WHERE id={}".format(money, info_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新卡跨币种消费手续费失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_trans_count(self, user_id, sql_line):
        sql = "SELECT DISTINCT COUNT(*) FROM card_trans JOIN card_info ON card_trans.card_id=card_info.card_id WHERE card_info.user_id={} {}".format(
            user_id, sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    def search_card_trans(self, user_id, sql_line):
        sql = "SELECT DISTINCT card_trans.*, card_info.label FROM card_trans JOIN card_info ON card_trans.card_id=card_info.card_id WHERE card_info.user_id={} {}".format(
            user_id, sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['card_number'] = "\t" + i[1]
            info_dict['acquirer_ica'] = i[2]
            info_dict['approval_code'] = i[3]
            info_dict['billing_amount'] = i[4]
            info_dict['billing_currency'] = i[5]
            info_dict['issuer_response'] = i[6]
            info_dict['mcc'] = i[7]
            info_dict['mcc_description'] = i[8]
            info_dict['merchant_amount'] = i[9]
            info_dict['merchant_currency'] = i[10]
            info_dict['merchant_id'] = "\t" + i[11]
            info_dict['merchant_name'] = i[12]
            info_dict['transaction_date_time'] = i[13]
            info_dict['transaction_type'] = i[14]
            info_dict['vcn_response'] = i[15]
            info_dict['status'] = i[17]
            info_dict['label'] = i[20]
            info_list.append(info_dict)
        return info_list

    def search_card_trans_settle(self, user_id, sql_line):
        sql = "SELECT DISTINCT card_trans_settle.*,card_info.label FROM card_trans_settle JOIN card_info ON card_trans_settle.card_id=card_info.card_id WHERE card_info.user_id={} {}".format(
            user_id, sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['card_number'] = "\t" + i[1]
            info_dict['authorization_date'] = i[4]
            info_dict['billing_amount'] = i[5]
            info_dict['billing_currency'] = i[6]
            info_dict['clearing_type'] = i[7]
            info_dict['merchant_amount'] = i[11]
            info_dict['merchant_currency'] = i[12]
            info_dict['merchant_name'] = i[14]
            info_dict['settlement_date'] = i[15]
            # info_dict['handing_fee'] = i[17]
            info_dict['label'] = i[17]
            info_list.append(info_dict)
        return info_list

    def search_admin_card_trans(self, sql_line):
        sql = "SELECT * FROM card_trans WHERE id is not null {}".format(
            sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['card_number'] = "\t" + i[1]
            info_dict['acquirer_ica'] = i[2]
            info_dict['approval_code'] = i[3]
            info_dict['billing_amount'] = i[4]
            info_dict['billing_currency'] = i[5]
            info_dict['issuer_response'] = i[6]
            info_dict['mcc'] = i[7]
            info_dict['mcc_description'] = i[8]
            info_dict['merchant_amount'] = i[9]
            info_dict['merchant_currency'] = i[10]
            info_dict['merchant_id'] = "\t" + i[11]
            info_dict['merchant_name'] = i[12]
            info_dict['transaction_date_time'] = i[13]
            info_dict['transaction_type'] = i[14]
            info_dict['vcn_response'] = i[15]
            info_dict['status'] = i[17]
            info_dict['name'] = i[18]
            info_list.append(info_dict)
        return info_list

    def search_admin_card_trans_settle(self, sql_line):
        sql = "SELECT * FROM card_trans_settle WHERE id is not null {}".format(
               sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        for i in rows:
            info_dict = dict()
            info_dict['card_number'] = "\t" + i[1]
            info_dict['authorization_date'] = i[4]
            info_dict['billing_amount'] = i[5]
            info_dict['billing_currency'] = i[6]
            info_dict['clearing_type'] = i[7]
            info_dict['merchant_amount'] = i[11]
            info_dict['merchant_currency'] = i[12]
            info_dict['merchant_name'] = i[14]
            info_dict['settlement_date'] = i[15]
            info_dict['expense'] = i[17]
            info_dict['user_name'] = i[18]
            info_dict['user_id'] = i[19]
            info_dict['_id'] = i[0]
            info_list.append(info_dict)
        return info_list

    def search_admin_exchange(self):
        sql = "SELECT ex_change, ex_range, hand, dollar_hand FROM admin"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        info_dict = dict()
        info_dict['ex_change'] = rows[0]
        info_dict['ex_range'] = rows[1]
        info_dict['hand'] = str(round(rows[2] * 100, 2)) + '%'
        info_dict['dollar_hand'] = str(round(rows[3] * 100, 2)) + '%'
        return info_dict

    def search_del_card(self, n_time):
        sql = "SELECT do_money, card_no FROM user_trans WHERE do_type='注销' AND do_date < '{}'".format(n_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['money'] = i[0]
            info_dict['card_no'] = i[1]
            info_list.append(info_dict)
        return info_list

    def search_card_top(self, card_no):
        sql = "SELECT SUM(do_money) FROM user_trans WHERE card_no='{}' AND (do_type='充值' OR do_type='批量充值')".format(card_no)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    def search_card_refund(self, card_no):
        sql = "SELECT IFNULL(SUM(do_money),0) FROM user_trans WHERE card_no='{}' AND do_type='退款'".format(card_no)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    def search_set_change(self):
        sql = "SELECT set_change, set_range  FROM admin"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0], rows[1]

    def insert_delete_card(self, card_number, card_id, user_id):
        sql = "INSERT INTO delete_card(card_number, card_id, user_id) VALUES('{}',{},{})".format(card_number, card_id, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入待删卡信息失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_delete_in(self, value):
        sql = "select * from delete_card where find_in_set('{}',card_number)".format(value)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        if row:
            return True
        else:
            return False

    def search_delete_card_info(self):
        sql = "SELECT * FROM delete_card;"
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if row:
            for i in row:
                info_dict = dict()
                info_dict['card_number'] = i[1]
                info_dict['card_id'] = i[2]
                info_dict['first_time'] = i[3]
                info_dict['first_remain'] = i[4]
                info_dict['second_time'] = i[5]
                info_dict['second_remain'] = i[6]
                info_dict['status'] = i[7]
                info_dict['user_id'] = i[8]
                info_list.append(info_dict)
            return info_list
        return info_list

    def update_delete_first(self, first_time, first_remain, card_number):
        sql = "UPDATE delete_card SET first_time = '{}',first_remain = {} WHERE card_number = '{}'".format(first_time, first_remain, card_number)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_delete_second(self, second_time, second_remain, card_number):
        sql = "UPDATE delete_card SET second_time = '{}',second_remain = {},status='T' WHERE card_number = '{}'".format(second_time, second_remain, card_number)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_user_free_card(self, number, user_name):
        sql = "UPDATE user_info SET free=free+{} WHERE id = {}".format(number, user_name)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_card_free(self, card_num, price, money, sub_time, user_id):
        sql = "INSERT INTO card_free(card_num, price, money, sub_time, user_id) VALUES({}, {}, {}, '{}',{})".format(
              card_num, price, money, sub_time, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加用户免费卡量记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_card_free_history(self, sql_line):
        sql = "SELECT card_free.*, user_info.name FROM card_free LEFT JOIN user_info ON user_info.id=card_free.user_id {}".format(sql_line)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['card_num'] = i[1]
                info_dict['price'] = i[2]
                info_dict['money'] = i[3]
                info_dict['sub_time'] = str(i[4])
                info_dict['name'] = i[6]
                info_list.append(info_dict)
            return info_list

    def search_top_money(self, start_t, end_t):
        sql = "SELECT SUM(money) FROM top_up WHERE `time` BETWEEN  '{}' AND '{}' ".format(start_t, end_t)
        conn, cursor = self.connect()
        cursor.execute(sql)
        row = cursor.fetchone()
        self.close_connect(conn, cursor)
        return row[0]

    def search_valid_card(self, number, top_money):
        sql = "SELECT * FROM new_card WHERE status = '' AND balance={} ORDER BY id ASC LIMIT {}".format(top_money, number)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows

    def update_new_card_use(self, card_id):
        sql = "UPDATE new_card SET status='T' WHERE card_id={}".format(card_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
            self.close_connect(conn, cursor)
            return True
        except Exception as e:
            logging.error("更新卡信息失败!")
            conn.rollback()
            self.close_connect(conn, cursor)
            return False


    def search_brex_user(self, username):
        sql = "SELECT * FROM brex_user WHERE account='{}'".format(username)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        if rows:
            return {
                "password": rows[2]
            }
        return {}

    def insert_brex_pay_log(self, pay_time, pay_money, top_money, status, phone, url, user_name):
        sql = "INSERT INTO brex_pay_log(pay_time, pay_money, top_money, status, phone, url, user_name) VALUES ('{}',{},{},'{}','{}', '{}','{}')".format(
            pay_time, pay_money, top_money, status, phone, url, user_name)
        conn, cursor = self.connect()

        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入用户请求充值信息失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_brex_user(self, account, password):
        sql = "INSERT INTO brex_user(account, password) VALUES ('{}','{}')".format(account, password)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("插入用户请求充值信息失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_brex_user_all(self):
        sql = "SELECT * FROM brex_user"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        info_list = list()
        if not rows:
            return info_list
        else:
            for i in rows:
                info_dict = dict()
                info_dict['account'] = i[1]
                info_dict['password'] = i[2]
                info_list.append(info_dict)
            return info_list

    def del_brex_user(self, account):
        sql = "DELETE FROM brex_user WHERE account = '{}'".format(account)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("删除失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_brex_pay_log(self, status):
        sql = "SELECT * FROM brex_pay_log WHERE status='{}'".format(
            status)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['pay_id'] = i[0]
            info_dict['pay_time'] = str(i[1])
            info_dict['pay_money'] = i[2]
            info_dict['top_money'] = i[3]
            info_dict['status'] = i[4]
            info_dict['ver_time'] = str(i[5])
            info_dict['url'] = i[7]
            info_dict['cus_name'] = i[8]
            info_dict['bank_msg'] = i[7] if "http" not in i[7] else ""
            info_list.append(info_dict)
        return info_list

    def del_brex_pay_log(self, pay_id):
        sql = "UPDATE brex_pay_log SET status='已删除' WHERE id = {} ".format(pay_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("删除失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_brex_pay_log(self, now_time, pay_id):
        sql = "UPDATE brex_pay_log SET status='已充值', ver_time='{}' WHERE id = {} ".format(now_time, pay_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("删除失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_verify_email(self):
        sql = "SELECT email FROM verify_account"
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchone()
        self.close_connect(conn, cursor)
        return rows[0]

    def update_verify_email(self, email):
        sql = "UPDATE verify_account SET email='{}'".format(email)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新BREX收件邮箱失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def update_divvy_hand(self, hand, account):
        sql = "UPDATE brex_user SET hand={} WHERE account='{}'".format(hand, account)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新divvy用户手续费失败" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def select_excel_info(self, user_id, sql=''):
        sql = "SELECT * FROM excel_info WHERE user_id='{}' {}".format(user_id, sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        data = []
        try:
            for i in rows:
                data.append({
                    "file_name": i[1],
                    "progress": i[2],
                })
        except Exception as e:
            logging.warning(str(e))
        return data

    def update_excel_info(self, progress, file_name):
        sql = "UPDATE excel_info SET progress={} WHERE file_name = '{}'".format(progress, file_name)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(str(e))
            conn.rollback()
        self.close_connect(conn, cursor)


    def insert_excel_info(self, file_name, progress, user_id):
        sql = "INSERT INTO excel_info( file_name, progress, user_id) VALUES('{}','{}','{}')".format(
                file_name, progress, user_id)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加用户免费卡量记录失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def insert_ustd_code(self, url, up_date, address):
        sql = "INSERT INTO ustd(url, up_date, address) VALUES('{}', '{}', '{}')".format(url, up_date, address)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("添加收款二维码失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def search_ustd_code(self, sql):
        sql = "SELECT * FROM ustd {}".format(sql)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        info_list = list()
        for i in rows:
            info_dict = dict()
            info_dict['qr_code'] = i[1]
            info_dict['qr_date'] = str(i[2])
            info_dict['address'] = i[3]
            info_dict['sum_money'] = i[4]
            if i[5] == 0:
                info_dict['status'] = '正常'
            elif i[5] == 1:
                info_dict['status'] = '锁定'
            else:
                info_dict['status'] = '置顶'
            info_list.append(info_dict)
        return info_list

    def search_ustd_field(self, field, url):
        sql = "SELECT {} FROM ustd WHERE url='{}'".format(field, url)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        if not rows:
            return False
        return rows[0][0]

    def update_ustd_info(self, file, value, url):
        sql = "UPDATE ustd SET {}={} WHERE url='{}'".format(file, value, url)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error("更新收款码状态失败!" + str(e))
            conn.rollback()
        self.close_connect(conn, cursor)

    def del_ustd_code(self, url):
        sql = "DELETE FROM ustd WHERE url = '{}'".format(url)
        conn, cursor = self.connect()
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
        self.close_connect(conn, cursor)

    def check_card_delete(self, card_number, now_time):
        sql = "SELECT COUNT(*) FROM user_trans WHERE card_no='{}' AND do_date < '{}' AND do_type='注销'".format(card_number, now_time)
        conn, cursor = self.connect()
        cursor.execute(sql)
        rows = cursor.fetchall()
        self.close_connect(conn, cursor)
        return rows[0][0]



SqlData = SqlDataBase()

if __name__ == "__main__":
    account = 'baocui'
    password = 'Bento1.0'
    card_number = '5563383501829202'
    now_time = '2023-07-19 22:05:05'
    res = SqlData.check_card_delete(card_number, now_time)
    print(res)

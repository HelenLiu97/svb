import pymysql
from DBUtils.PooledDB import PooledDB


class ConnMysql(object):
    __pool = None

    def __enter__(self):
        self.conn = self.__getconn()
        self.cursor = self.conn.cursot()

    def __getconn(self):
        if self.__pool is None:
            # host = "3.17.178.128"
            host = "127.0.0.1"
            port = 12588
            # port = 3306
            user = "root"
            # password = "liuxiao@140922"
            password = "Helen799677"
            database = "svb"
            self.__pool = PooledDB(pymysql, 4, host=host, port=port,
                                 user=user, passwd=password, db=database,
                                 charset='utf8', setsession=['SET AUTOCOMMIT = 1']
                                 )
        return self.__pool.connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()
        self.conn.close()

    def getconn(self):
        conn = self.__getconn()
        cursor = conn.cursor()
        return conn, cursor


def get_my_connection():
    return ConnMysql()

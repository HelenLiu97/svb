from qiniu import Auth, put_file


def sm_photo(path, file_name):
    try:
        # -*- coding: utf-8 -*-
        # flake8: noqa

        # 需要填写你的 Access Key 和 Secret Key
        access_key = 'KgHe4AAvPJStXOlhxGB3ds-3ndsUxS-wypBwKAgW'
        secret_key = '6l1ujW79c4Zwo5XmpznDLTdQLaobW3As3r9fnol1'

        # 构建鉴权对象
        q = Auth(access_key, secret_key)

        # 要上传的空间
        bucket_name = 'pay_pic'

        # 上传后保存的文件名
        key = file_name

        # 生成上传 Token，可以指定过期时间等
        token = q.upload_token(bucket_name, key)

        # 要上传文件的本地路径
        localfile = path

        ret, info = put_file(token, key, localfile)

        return ret.get('key')
    except:
        return False


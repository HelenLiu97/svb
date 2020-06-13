from flask import Blueprint


upload_blueprint = Blueprint('upload', __name__, url_prefix='/upload', template_folder='../templates')


user_blueprint = Blueprint('user', __name__, url_prefix='/user', template_folder='../templates')


middle_blueprint = Blueprint('middle', __name__, url_prefix='/middle',  template_folder='../templates')


admin_blueprint = Blueprint('admin', __name__, url_prefix='/admin',  template_folder='../templates')

pay_blueprint = Blueprint('pay', __name__, url_prefix='/pay',  template_folder='../templates')

verify_pay_blueprint = Blueprint('verify_pay', __name__, url_prefix='/verify_pay', template_folder='../templates')

finance_blueprint = Blueprint('finance', __name__, url_prefix='/finance', template_folder='../template')

search_blueprint = Blueprint('search', __name__, url_prefix='/search', template_folder='../template')


from . import upload, user,  middle, admin, search

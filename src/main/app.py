# -*- coding: utf-8 -*-
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
### Alias : PosServer.app & Last Modded : 2022.03.17. ###
Coded with Python 3.10 Grammar by IRACK000
Description : PosServer HTTP Server
Reference : [create_app] https://stackoverflow.com/questions/57600034/waitress-command-line-returning-malformed-application-when-deploying-flask-web
            [Logging] https://stackoverflow.com/questions/52372187/logging-with-command-line-waitress-serve
            [flask] https://flask.palletsprojects.com/en/2.0.x/api/
            [route multi rules] https://stackoverflow.com/questions/17285826/flask-redirecting-multiple-routes
                                https://hackersandslackers.com/flask-routes/
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
from datetime import datetime, time

from flask import Flask, request, jsonify, make_response, Request, Response, abort
from waitress import serve

if '__main__' == __name__:  # IDE가 실행 단위로 판단하지 않도록 통상적 경우와 리터럴 위치를 반대로 함.
    from cli.apis import check_py_version, change_work_dir  # 상대 경로 import; 파일 위치에 따라 코드가 수정 되어야 함.
    check_py_version()
    change_work_dir(__file__)


DEBUG = True


# HTTP Error Codes
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403
NOT_FOUND = 404
INTERNAL_SERVER_ERROR = 500
SERVICE_UNAVAILABLE = 503


# TODO: Logging


INVALID_ORDER_TOKEN_ERROR = "Invalid order token."


class JsonParseError(Exception):
    def __init__(self, msg):
        super(JsonParseError, self).__init__(msg)


class UnauthorizedClientError(Exception):
    def __init__(self, msg):
        super(UnauthorizedClientError, self).__init__(msg)


class ForbiddenAccessError(Exception):
    def __init__(self, msg):
        super(ForbiddenAccessError, self).__init__(msg)


# < Create Flask App ------------------------------------------------------------------------------------------------->
def create_app():
    app = Flask(__name__)

    service_denial_msg = "From 2:50 to 5:10, it is server inspection time. Sorry for the inconvenience. " \
                         "We would appreciate it if you could try again after the inspection."
    service_denial_start = time(2, 50, 0, 0)
    service_denial_end = time(5, 10, 0, 0)

    break_time_msg = "From 5:10 to 5:30, it is store break time. Sorry for the inconvenience. " \
                     "We would appreciate it if you could try again after the break."
    break_time_start = time(15, 30, 0, 0)
    break_time_end = time(16, 30, 0, 0)

    def server_status_noticer(func):
        def notice_service_denial(*args, **kwargs):
            # notice server inspection time
            if service_denial_start <= datetime.now().time() <= service_denial_end:
                abort(SERVICE_UNAVAILABLE, description="[ServerInspectionTimeError] " + service_denial_msg)
            # run function with error handling
            else:
                try:
                    return func(*args, **kwargs)
                except (ValueError | KeyError | TypeError | JsonParseError) as e:
                    abort(BAD_REQUEST, description=f"[{type(e).__name__}] {str(e)}")
                except (OSError | RuntimeError) as e:
                    abort(INTERNAL_SERVER_ERROR, description=f"[{type(e).__name__}] {str(e)}")
                except UnauthorizedClientError as e:
                    abort(UNAUTHORIZED, description=f"[{type(e).__name__}] {str(e)}")
                except ForbiddenAccessError as e:
                    abort(FORBIDDEN, description=f"[{type(e).__name__}] {str(e)}")
        notice_service_denial.__name__ = func.__name__  # rename function name
        return notice_service_denial

    def parse_json(req: Request, required_key: dict[str, type] = None) -> (str, dict):
        """
        Parse the request json
        :param req: Request object
        :param required_key: required key Info (json must have this keys)
        :return: dict when the request is valid, Response object when the request is invalid
        """
        personal_json = req.get_json()
        def check_keys() -> bool:  # TODO: check if get_json returns proper type of value or just returns str type
            for key, T in (required_key if required_key is not None else {}).items():
                if key not in personal_json or not personal_json[key] or not isinstance(personal_json[key], T):
                    return False
            return True
        if not personal_json or len(personal_json) >= len(required_key)+1 or not check_keys():
            raise JsonParseError("Json does not contain required keys.")
        elif 'token' not in personal_json or not isinstance(personal_json['token'], str):
            raise UnauthorizedClientError("Authorization token is not found.")
        else:
            return personal_json.pop('token'), personal_json

    @app.route('/')
    @server_status_noticer
    def index():
        """ To check if the server is running """
        return f"Hello, {request.environ.get('HTTP_X_REAL_IP', request.remote_addr)}!"

    #
    # process log in/out requests
    #
    @app.post('/sign')
    @server_status_noticer
    def process_sign_in_or_up() -> Response:
        """ Process the sign in or sign up request (CUSTOMER) - POST method
            Request:
                Body = {token: user_order_token, password: MD5(table_password)}
        """
        parsed_json = parse_json(request)
        ap.process_sign_in_or_up(parsed_json[0], **parsed_json[1])
        result = ?
        if result:
            return jsonify({'status': "success"})
        else:
            404? 401?
            return jsonify({'status': "success"})

    @app.put('/sign')  # initial login process
    @app.patch('/sign')  # additional login process
    @server_status_noticer
    def process_admin_sign_in_or_up() -> Response:
        """ Process the sign in or sign up request (ADMIN) - POST method
            Request:
                if method is put:
                    Body = {token: firebase_id_token, password: MD5(table_password)}
                else:  # when method is patch
                    Body = {main_token: firebase_id_token (main_token), token: firebase_id_token (additional_token),
                            password: MD5(table_password)}
            Response:
                200 Login Success - Login Succeed
                403 Forbidden     - Password Invalid
                                  - Already Registered
        """
        parsed_json = parse_json(request)
        ap.process_sign_in_or_up(parsed_json[0], **parsed_json[1])
        result = ?
        if result:
            return jsonify({'status': "success"})
        else:
            403
            return jsonify({'status': "success"})

    @app.patch('/signout')
    @app.patch('/sign_out')
    @server_status_noticer
    def process_sign_out() -> Response:
        """ Process the sign out request (ADMIN, CUSTOMER) - POST method
            * Check if the token belongs to ADMIN first.
            * Customer will be able to sign out only when there's no order history in customer's table.
            Request:
                Body = {token: firebase_id_token, password: MD5(table_password)}
        """
        parsed_json = parse_json(request)
        ap.process_sign_in_or_up(parsed_json[0], **parsed_json[1])
        result = ?
        if result:
            return jsonify({'status': "success"})
        else:
            404? 401?
            return jsonify({'status': "success"})

    #
    # process table order requests
    #
    @app.post('/table/<int:table_number>/status')
    def get_table_status(table_number: int):
        """ Get table status - POST method
            Request:
                Body = {token: firebase_id_token}
            Response:
                200 Not Found      ['status': 0]
                200 Not Registered ['status': 1]
                200 Not Ordered    ['status': 2]
                200 Registered     ['status': 3]
        """
        return 0

    @app.post('/table/<int:table_number>/order/')
    @app.post('/table/<int:table_number>/order_history')
    def get_table_order_history(table_number: int):
        """ Get table order history - POST method
            Request:
                Body = {token: firebase_id_token}
        """
        return 0



    @app.put('/order')
    def put_order():
        """ Put order
        :return: order token
        """
        token, personal_json = parse_json(request, {'order': str})
        if token != ORDER_TOKEN:
            raise UnauthorizedClientError(INVALID_ORDER_TOKEN_ERROR)
        else:
            return jsonify({"token": ORDER_TOKEN})

    @app.post('/table')
    def check_table():
        """ Post table
        :return: table token
        """
        token, personal_json = parse_json(request, {'table': str})
        if token != TABLE_TOKEN:
            raise UnauthorizedClientError(INVALID_TABLE_TOKEN_ERROR)
        else:
            return jsonify({"token": TABLE_TOKEN})

    return app


if __name__ == '__main__':
    wsgiapp = create_app()
    serve(wsgiapp, host='0.0.0.0', port=5000, url_scheme='https')

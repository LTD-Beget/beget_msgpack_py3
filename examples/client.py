#!/usr/bin/env python
import logging
import beget_msgpack
import config

logging.basicConfig(level=logging.INFO)

logger = beget_msgpack.Logger.get_logger()
# or -> logger = logging.get_logger('beget_msgpack')

logger.setLevel(logging.DEBUG)
# server = 'kon'  # Для этого сервера должен вернуться запрос для fastcgi
# server = 'sul'  # Для этого сервера должен вернуться запрос для msgpack.client
server = 'localhost'

# Обращаемся к фабрике запросов указывая сервер к которому мы будем отправлять запрос.
# Из фабрики получаем класс реквеста
request_factory = beget_msgpack.RequestFactory(config)
Request = request_factory.get_request(server)

# (Действия дальше идентичны для любого реквеста возврващаемого из фабрики)
# Делаем реквест с указанием контроллера/экшена и аргументов
# Response = Request.request('myControllerName/myActionName', my_arg='myMsg')
Request.set_timeout(40)
Response = Request.request('test/test', my_arg='myMsg')
# Из реквеста получаем Response
if Response.has_error():
    print(repr(Response.get_error()))
else:
    print(repr(Response.get_method_result()))

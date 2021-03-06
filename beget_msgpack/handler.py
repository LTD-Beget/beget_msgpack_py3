import select
import sys
import re
import traceback
import msgpack
import time

from .lib.logger import Logger
from .lib.response import Response
from .lib.errors.error_constructor import ErrorConstructor

import socketserver


class Handler(socketserver.BaseRequestHandler, object):
    """
    Обработчик запроса. Каждый запрос форкается и запускает этот класс.
    """

    def __init__(self, request, client_address, server,
                 controllers_prefix, timeout_receive=5, logger=None):

        self.controllers_prefix = controllers_prefix
        self.packer = msgpack.Packer(default=lambda x: x.to_msgpack())
        self.unpacker = msgpack.Unpacker()
        self.response = Response()
        self.timeout_receive = timeout_receive
        self.time_start = None

        if logger is None:
            self.logger = Logger.get_logger()
        else:
            self.logger = logger

        super(Handler, self).__init__(request, client_address, server)

    def setup(self):
        self.time_start = time.time()

        if hasattr(self.logger, 'request_id_generate') and callable(self.logger.request_id_generate):
            self.logger.request_id_generate()

    def handle(self):
        try:
            # Получаем все данные из сокета
            message = []
            data = b''
            while True:

                # Устанавливаем таймаут на получение данных из сокета
                ready = select.select([self.request], [], [], self.timeout_receive)
                if ready[0]:
                    data_buffer = self.request.recv(4096)
                else:
                    raise Exception('Exceeded timeout')

                # msgpack-rpc не завершает данные EOF, поэтому через not data мы не выйдем
                if not data_buffer:
                    raise Exception('Only for MessagePack')

                data += data_buffer

                try:
                    # Выходим если получилось декодировать, иначе продолжаем ожидать данные
                    message = msgpack.unpackb(data)
                    break
                except:
                    pass

            self.on_message(message)

        except Exception as e:
            self.logger.error('Handler: get Exception: %s\n  Traceback: %s', str(e), traceback.format_exc())

    def finish(self):
        time_end = time.time()
        self.logger.debug('Request completed in seconds: %s', time_end - self.time_start)

        if hasattr(self.logger, 'request_id_clear') and callable(self.logger.request_id_clear):
            self.logger.request_id_clear()

    def on_message(self, message):
        route_byte = message[2]
        route = route_byte.decode('UTF-8')
        arguments = message[3][0]
        self.logger.debug('Handler: \n  Route: %s\n  Arguments: %s', repr(route), repr(arguments))

        front_controller = FrontController(route, self.controllers_prefix, self.logger)
        result = front_controller.run_controller(arguments)

        result_encoded = self.packer.pack([1, 0, None, result])
        self.request.sendall(result_encoded)

    def log(self, msg):
        if hasattr(self, 'logger'):
            self.logger.debug(msg)


class FrontController(object):
    """
    Класс обработчик запросов
    Он отвечает за:
        - получение и вызов контроллера с передачей ему параметров (имя экшена, аргументы)
        - обработка ошибок
    """

    def __init__(self, route, controllers_prefix, logger):
        """
        :param route: получает путь к экшену в виде 'controller/action'
        :type route: str

        :param controllers_prefix: имя пакета (префикс) где будут искаться контроллеры
        :type controllers_prefix: str
        """
        self.route = route
        self.controllers_prefix = controllers_prefix
        self.logger = logger

    def run_controller(self, action_args):
        """
        :param action_args: получает dict аргументов или пустой dict
        :type action_args: dict
        """
        response = Response()

        # Ищем вызываемый контроллер
        try:
            (controller_name_search, action) = self.route.split("/")
            controller_name = controller_name_search[0].title() + controller_name_search[1:] + "Controller"
            controller_module_name = self._from_camelcase_to_underscore(controller_name_search) + "_controller"
            module_name = '%s.%s' % (self.controllers_prefix, controller_module_name)
            self.logger.debug('FrontController: \n'
                              '  module controller: %s\n'
                              '  class controller: %s\n'
                              '  action in controller: %s', module_name, controller_name, action)
            module_obj = sys.modules[module_name]
            controller_class = getattr(module_obj, controller_name)

        # Если контроллера нет, то возвращаем ошибку запроса
        except Exception as e:
            error_msg = "Failed to parse route or get controller. given: %s" % self.route
            self.logger.error('FrontController: %s\n  Exception: %s\n'
                              '  Traceback: %s', error_msg, str(e), traceback.format_exc())
            response.add_request_error(ErrorConstructor.TYPE_ERROR_BAD_REQUEST, error_msg)
            return response.dump()

        # Вызываем контроллер и передаем ему необходимыем параметры
        try:
            controller = controller_class(action, action_args, self.logger, response)
            result = controller.start()
            return result

        except Exception as e:
            self.logger.error('FrontController: Exception: %s\n  Traceback: %s', str(e), traceback.format_exc())
            response.add_request_error(ErrorConstructor.TYPE_ERROR_UNKNOWN, str(e))
        return response.dump()

    @staticmethod
    def _from_camelcase_to_underscore(string):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

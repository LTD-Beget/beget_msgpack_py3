from .lib.response import Response

import msgpack

from .lib.logger import Logger
from .lib.response import Response
from .lib.errors.error_constructor import ErrorConstructor


class ResponseFactory:
    """
    Класс для конструкции одного Response из разнообразных форматов:

        метод получения Response из чеголибо:
            Получаем исходный ответ чеголибо
            При необходимости декадируем его чтобы привести его к понятном для Request виду
            После получения утвержденного формата сообщения, передаем его в Request и возвращаем клиенту
    """

    def __init__(self):
        self.logger = Logger.get_logger()
        pass

    def get_response_by_msgpack_answer(self, answer):
        self.logger.debug('ResponseFactory:by_msgpack: get answer: %s', answer)
        return Response(answer)

    def get_response_by_fcgi_answer(self, answer, encode=True):
        code, header, raw_answer, error = answer
        self.logger.debug('ResponseFactory:by_fcgi: get answer: %s', repr(answer))

        # Если fcgi клиент сообщил нам об ошибке
        if error:
            self.logger.error('ResponseFactory:by_fcgi: get error in answer: %s' % error)
            return self.get_response_by_request_error(ErrorConstructor.TYPE_ERROR_UNKNOWN,
                                                      error,
                                                      ErrorConstructor.CODE_ERROR_UNKNOWN)

        try:
            answer_unpack = msgpack.unpackb(raw_answer)

        # Если ответ из сети пришел не запакованный в msgpack, то это ошибка
        except msgpack.exceptions.ExtraData:
            self.logger.error('ResponseFactory->by_fcgi: msgpack could not unpack answer')
            return self.get_response_by_request_error(ErrorConstructor.TYPE_ERROR_UNKNOWN, raw_answer, ErrorConstructor.CODE_ERROR_UNKNOWN)

        if encode:
            answer_unicode = self.byte_to_unicode_dict(answer_unpack)
            self.logger.debug('ResponseFactory:by_fcgi: change it to: %s', repr(answer_unicode))
            return Response(answer_unicode)
        else:
            answer_encoded = self.byte_to_unicode_dict_only_keys(answer_unpack)
            return Response(answer_encoded)

    def get_response_by_request_error(self, type_error=None, message=None, code=None):
        self.logger.debug('ResponseFactory:by_request_error: get code: %s, description: %s',
                          repr(code),
                          repr(message))
        response = Response()
        response.add_request_error(type_error, message, code)
        return response

    def byte_to_unicode_dict(self, answer):
        decoded = {}
        for key in answer:
            unicode_key = key.decode("utf-8")
            if isinstance(answer[key], dict):
                decoded[unicode_key] = self.byte_to_unicode_dict(answer[key])
            elif isinstance(answer[key], list):
                decoded[unicode_key] = self.byte_to_unicode_list(answer[key])
            elif isinstance(answer[key], int):
                decoded[unicode_key] = answer[key]
            elif isinstance(answer[key], float):
                decoded[unicode_key] = answer[key]
            elif answer[key] is None:
                decoded[unicode_key] = answer[key]
            else:
                try:
                    decoded[unicode_key] = answer[key].decode("utf-8")
                except UnicodeDecodeError:
                    # Костыль для кракозябр
                    decoded[unicode_key] = answer[key].decode("ISO-8859-1")
        return decoded

    def byte_to_unicode_dict_only_keys(self, answer):
        decoded = {}
        for key in answer:
            unicode_key = key.decode("utf-8")
            if isinstance(answer[key], dict):
                decoded[unicode_key] = self.byte_to_unicode_dict_only_keys(answer[key])
            else:
                decoded[unicode_key] = answer[key]
        return decoded

    def byte_to_unicode_list(self, answer):
        decoded = []
        for item in answer:
            if isinstance(item, dict):
                decoded_item = self.byte_to_unicode_dict(item)
                decoded.append(decoded_item)
            elif isinstance(item, list):
                decoded_item = self.byte_to_unicode_list(item)
                decoded.append(decoded_item)
            elif isinstance(item, int):
                decoded.append(item)
            elif isinstance(item, float):
                decoded.append(item)
            elif item is None:
                decoded.append(item)
            else:
                try:
                    decoded_item = item.decode("utf-8")
                except UnicodeDecodeError:
                    # Костыль для кракозябр
                    decoded_item = item.decode("ISO-8859-1")
                decoded.append(decoded_item)
        return decoded
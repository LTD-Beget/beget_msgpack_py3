import beget_msgpack


class MyControllerNameController(beget_msgpack.Controller):

    def action_my_action_name(self, my_arg):
        print('Controller get: %s' % repr(my_arg))
        return {'return': my_arg}

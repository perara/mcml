class Message:

    def __init__(self, command=None, args=None, payload=None):
        self.command = command
        self.args = args
        self.payload = payload


class RegisterService(Message):

    def __init__(self, service, local_endpoint, pid, depth):
        super().__init__("register_service", args=(service, ), payload=dict(
            local_endpoint=local_endpoint,
            pid=pid,
            depth=depth
        ))


class UnregisterService(Message):

    def __init__(self, service):
        super().__init__("unregister_service", args=(service, ))


class SubscribeService(Message):

    def __init__(self, service):
        super().__init__("subscribe_service", args=(service, ))


class Subscription(Message):

    def __init__(self, endpoint):
        super().__init__("subscription", args=tuple(endpoint))


class Quit(Message):

    def __init__(self):
        super().__init__(command="quit")

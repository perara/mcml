
class Message:

    def __init__(self, command, payload):
        self.c = command
        self.p = payload


class AnnounceMessage(Message):

    def __init__(self, service, host, port):
        super().__init__("endpoint_announce", payload=dict(
            service=service,
            host=host,
            port=port,
            id=str(uuid.uuid4())
        ))


class InitMessage(Message):

    def __init__(self, clazz):
        super().__init__("init", payload=dict(
            clazz=clazz,
            id=str(uuid.uuid4())
        ))


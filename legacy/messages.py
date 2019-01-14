class Message:

    def __init__(self, command=None, payload=None):
        self.command = command
        self.payload = payload


class RegisterService(Message):

    def __init__(self, service, local_endpoint, pid, depth):
        super().__init__("register_service",  payload=dict(
            local_endpoint=local_endpoint,
            pid=pid,
            depth=depth,
            service=service
        ))


class UnregisterService(Message):

    def __init__(self, service):
        super().__init__("unregister_service", payload=dict(
            service=service
        ))


class SubscribeService(Message):

    def __init__(self, id, service):
        super().__init__("subscribe_service",  payload=dict(
            id=id,
            service=service
        ))


class SubscriptionOK(Message):

    def __init__(self, id, service, host, port):
        super().__init__("subscription_ok", payload=dict(
            id=id,
            service=service,
            host=host,
            port=port
        ))


class SubscriptionFail(Message):

    def __init__(self, id, service):
        super().__init__("subscription_fail", payload=dict(
            id=id,
            service=service,
        ))


class PollRequestMessage(Message):

    def __init__(self):
        super().__init__("poll_request", payload=dict())


class PollResponseMessage(Message):

    def __init__(self, data):
        super().__init__("poll_response", payload=data)


class ReadBufferOverflowMessage(Message):

    def __init__(self, id, duration):
        super().__init__("read_buffer_overflow", payload=dict(
            id=id,
            duration=duration
        ))


class Quit(Message):

    def __init__(self):
        super().__init__(command="quit")

import uvloop
import asyncio
import socket
import logger
import inspect

class MCMLSocket(asyncio.Protocol):

    def __init__(self, use_uvloop=True):

        """Retrieve logger for the class."""
        self.logger = logger.get_logger("MCMLSocket")

        if use_uvloop:
            """Use the uvloop to increase throughput."""
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.get_event_loop()

        self._cb_on_received_async = []
        self._cb_on_received_sync = []

    async def data_received(self, data):
        message = data.decode()

        for cb in self._cb_on_received_sync:
            cb(message)
        for acb in self._cb_on_received_async:
            await acb(message)

    def add_on_receive_cb(self, cb):

        if inspect.iscoroutinefunction(cb):
            self._cb_on_received_async.append(cb)
        elif inspect.isfunction(cb):
            self._cb_on_received_sync.append(cb)
        else:
            raise AssertionError("add_on_receive_cb takes in callback which is either async def or def.")



    def connection_made(self, transport):
        self.transport = transport
        sock = transport.get_extra_info('socket')
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except (OSError, NameError):
            pass

    async def listen(self, host, port):
        server = await loop.create_server(lambda: self, host, port, backlog=1000)

    def dial(self, host, port):
        pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    async def test(data):
        print("async, ", data)

    def test2(data):
        print("sync, ", data)

    x = MCMLSocket()
    x.add_on_receive_cb(test)
    x.add_on_receive_cb(test2)

    loop.run_until_complete(x.listen("0.0.0.0", 41000))


    loop.run_forever()

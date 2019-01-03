import asyncio
import random
import time
from multiprocessing import Process
import os
from aiohttp import web
from client import Client
from logger import manager_log


class Message:

    def __init__(self, command=None, args=None, payload=None):
        self.command = command
        self.args = args
        self.payload = payload


class RegisterService(Message):

    def __init__(self, service, local_endpoint):
        super().__init__("register_service", args=(service, ), payload=local_endpoint)


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


class Manager(Process):

    def __init__(self, host="0.0.0.0", port=21000):
        Process.__init__(self)

        self.host = host
        self.port = port
        self.loop = None
        self.clients = dict()
        self.services = dict()

    def run(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.start_server())

    async def start_server(self):
        manager_log.warning("Manager is listening on on %s:%s", self.host, self.port)
        server = await asyncio.start_server(self.on_connect, host=self.host, port=self.port, loop=self.loop, start_serving=True)
        await server.serve_forever()

    async def on_connect(self, reader, writer):
        client = Client(reader, writer)
        self.clients[client] = client
        self.loop.create_task(self.read(client))

    async def read(self, client):

        while client.ready:
            data = await client.read()

            cmd = getattr(self, data.command, self.not_implemented)
            await cmd(client, data.payload, *data.args)
        del self.clients[client]

    async def write(self):
        pass

    async def subscribe_service(self, client, payload, service):

        try:
            remote_endpoint = random.choice(self.services[service])
            await client.write(Subscription(endpoint=remote_endpoint))
        except KeyError as e:
            pass # client.write()  # TOdo missing service in manager

    async def not_implemented(self, client, payload, *args):
        client.ready = False
        print("Client attempts to call unimplemented function!")

    async def quit(self, client, command, **kwargs):
        client.ready = False

    async def register_service(self, client, payload, service):
        if service not in self.services:
            self.services[service] = []
        self.services[service].append(payload)

        manager_log.warning("Registered %s as a service at %s", service, client.name)

    async def unregister_service(self, client, payload, service):
        if service in self.services:
            self.services[service].pop(self.services[service].find(client))
            manager_log.warning("Unregistered %s from client %s", service, client.name)


class TCPServer(Process):

    def __init__(self):
        Process.__init__(self)
        self._service_name = self.__class__.__name__

        self._manager_endpoint = (None, None)  # Host, Port
        self._manager_socket = None

        self._local_endpoint = None
        self._local_endpoint_socket = None

        self._remote_endpoint_name = None
        self._remote_endpoint = None
        self._remote_endpoint_socket = None

        self._loop = None

    async def _run(self):
        pass

    async def _process(self, x):
        return x

    async def set_manager(self, host, port):
        self._manager_endpoint = (host, port)

    async def create_server(self, host="0.0.0.0", port=0):
        self._local_endpoint = (host, port)

        self._local_endpoint_socket = await asyncio.start_server(
            self.on_client_connect,
            host=self._local_endpoint[0],
            port=self._local_endpoint[1],
            start_serving=True
        )
        self._local_endpoint = self._local_endpoint_socket.sockets[0].getsockname()

    async def on_client_connect(self, reader, writer):
        local_socket = writer.get_extra_info('socket')
        _client = Client(reader=reader, writer=writer, reconnect=True)

        #remote_socket = reader.get_extra_info('socket')
        manager_log.warning("[%s:%s] new client: %s:%s" % (local_socket.getsockname()[0], local_socket.getsockname()[1], local_socket.getpeername()[0], local_socket.getpeername()[1]))

        while True:
            data = await _client.read()
            data = await self._process(data)
            await self.forward(data)

    async def connect_manager(self):
        self._manager_socket = await Client.connect(*self._manager_endpoint)

    async def forward(self, x):
        if self._remote_endpoint_socket:
            await self._remote_endpoint_socket.write(x)


    async def register_service(self):
        await self._manager_socket.write(RegisterService(
            service=self._service_name,
            local_endpoint=self._local_endpoint)
        )

    async def set_remote_service(self, remote_service_name):
        if not remote_service_name:
            return

        self._remote_endpoint_name = remote_service_name

    async def connect_remote_service(self):
        """No remote service defined. Ignore request"""
        if self._remote_endpoint_name is None:
            return

        manager_log.warning("Attempting to connect to remote service '%s'.", self._remote_endpoint_name)

        await self._manager_socket.write(SubscribeService(service=self._remote_endpoint_name))
        subscription = await self._manager_socket.read()

        self._remote_endpoint_socket = await Client.connect(*subscription.args)

    def run(self):
        self._loop = asyncio.new_event_loop()

        self._loop.run_until_complete(self.async_start())
        self._loop.run_until_complete(self._run())
        self._loop.run_forever()

    async def async_start(self):
        await self.create_server()
        await self.connect_manager()
        await self.register_service()
        await self.connect_remote_service()


class Agent(TCPServer):

    def __init__(self):
        super().__init__()

    async def _run(self):

        while True:
            await self.forward(str(self.pid))
            #await asyncio.sleep(1)


class StateReplace(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        return x + " => " + str(self.pid)


class RGB2Gray(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        return x + " => " + str(self.pid)


class Model(TCPServer):

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.time = time.time()

    async def _process(self, x):
        #print(x + " => " + str(self.pid))
        if time.time() > self.time + 1:
            print("Msg per sec: %s" % self.counter)
            self.time = time.time()
            self.counter = 0
        self.counter += 1



class Struct:

    def __init__(self, struct):
        self.struct = struct

    async def build(self):

        previous_service = None
        for cls, count in reversed(self.struct["model"]):
            for i in range(count):

                obj = cls()
                await obj.set_manager(*self.struct["manager"])
                await obj.set_remote_service(remote_service_name=previous_service)
                obj.daemon = True
                obj.start()
            previous_service = cls.__name__

class WebServer(TCPServer):
    def __init__(self, host='0.0.0.0', port=8080):
        TCPServer.__init__(self)

    def run(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.dist_path = os.path.join(dir_path, "www", "dist", "www")
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.start_webserver())

        loop.run_forever()

    async def handle(self, request):

        return web.FileResponse(os.path.join(self.dist_path, "index.html"))



    async def start_webserver(self):
        app = web.Application()

        app.router.add_static('/', path=str(self.dist_path))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        print("Started server on http://localhost:8080")



if __name__ == "__main__":
    """Manager, Could be started anywhere...."""
    manager = Manager(host='127.0.0.1', port=41000)
    manager.daemon = True
    manager.start()

    webserver = WebServer(host='127.0.0.1', port=8080)
    webserver.daemon = True
    webserver.start()

    """Build Struct."""
    struct = Struct({
        "manager": ('127.0.0.1', 41000),
        "model": [
            (Agent, 3),
            (StateReplace, 1),
            (RGB2Gray, 1),
            (Model, 1)
        ]
    })

    loop = asyncio.get_event_loop()

    loop.create_task(struct.build())

    loop.run_forever()

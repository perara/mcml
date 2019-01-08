import asyncio
from multiprocessing import Process

from client import Client
from logger import manager_log
from messages import RegisterService, SubscribeService


class TCPServer(Process):

    def __init__(self):
        Process.__init__(self)
        self._service_name = self.__class__.__name__

        self._manager_endpoint = (None, None)  # Host, Port
        self._manager_socket = None

        self._local_endpoint = None
        self._local_endpoint_socket = None

        self._remote_endpoint_names = None
        #self._remote_endpoint = None
        self._remote_endpoint_sockets = []

        self.depth = None

        self._loop = None

    async def _run(self):
        pass

    async def _process(self, x):
        return x

    async def set_depth(self, depth):
        self.depth = depth

    async def set_manager(self, host, port):
        self._manager_endpoint = (host, port)

    async def create_server(self, host="0.0.0.0", port=0):
        self._local_endpoint = (host, port)

        self._local_endpoint_socket = await asyncio.start_server(
            self.on_client_connect,
            host=self._local_endpoint[0],
            port=self._local_endpoint[1],
            #start_serving=True
        )

        self._local_endpoint = self._local_endpoint_socket.sockets[0].getsockname()

    async def on_client_connect(self, reader, writer):
        local_socket = writer.get_extra_info('socket')
        _client = Client(reader=reader, writer=writer, reconnect=True)

        #remote_socket = reader.get_extra_info('socket')
        manager_log.warning("[%s:%s] new client: %s:%s" % (local_socket.getsockname()[0], local_socket.getsockname()[1], local_socket.getpeername()[0], local_socket.getpeername()[1]))

        while _client.ready:
            data = await _client.read()
            print(data)
            await self.on_client_message(_client, data)
            data = await self._process(data)

            await self.forward(data)

    async def connect_manager(self):
        self._manager_socket = await Client.connect(*self._manager_endpoint)

    async def on_client_message(self, client, x):
        return None

    async def forward(self, x):
        if self._remote_endpoint_sockets:
            for socket in self._remote_endpoint_sockets:
                await socket.write(x)

    async def register_service(self):
        """
        This function sends a register  service command to the manager. THe manager then logs the event and add the
        local endpoint as the specified service (service_name).
        :return:
        """
        await self._manager_socket.write(RegisterService(
            service=self._service_name,
            local_endpoint=self._local_endpoint,
            pid=self.pid,
            depth=self.depth
        ))

    async def set_remote_service(self, remote_service_names):
        if not remote_service_names:
            return

        print(remote_service_names)
        self._remote_endpoint_names = remote_service_names

    async def connect_remote_service(self):
        """No remote service defined. Ignore request"""
        if not self._remote_endpoint_names:
            return

        for remote_endpoint in self._remote_endpoint_names:

            manager_log.warning("Attempting to connect to remote service '%s'.", remote_endpoint)
            await self._manager_socket.write(SubscribeService(service=remote_endpoint))
            subscription = await self._manager_socket.read()


            remote_endpoint = await Client.connect(*subscription.args)
            self._remote_endpoint_sockets.append(remote_endpoint)

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
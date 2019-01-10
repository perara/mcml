import asyncio
from collections import deque
from multiprocessing import Process
from statistics import mean

from client import Endpoint
from logger import manager_log, tcpserver_log
from messages import RegisterService, SubscribeService, PollResponseMessage


class TCPServer(Process):

    SUBSCRIPTION_FAIL_SLEEP = 5

    def __init__(self):
        Process.__init__(self)
        self._service_name = self.__class__.__name__

        self._manager_endpoint = None
        self._local_endpoint_socket = None
        self._local_endpoint = None
        self._remote_endpoints = []

        """Throughput performance counter."""
        self._diag_throughput_in = 0
        self._diag_throughput_in_history = deque(maxlen=60)

        self._diag_throughput_out = 0
        self._diag_throughput_out_history = deque(maxlen=60)

        """The sleep duration for the diagnostics module."""
        self._diag_sleep = 1.0

        self.depth = None

        self._loop = None

        manager_log.info("[%s]: Initialization complete.", self._service_name)

    async def _run(self):
        return False

    async def _process(self, x):
        return x

    async def __diagnostics(self):
        while True:
            self._diag_throughput_in_history.append(self._diag_throughput_in)
            self._diag_throughput_out_history.append(self._diag_throughput_out)
            self._diag_throughput_in = 0
            self._diag_throughput_out = 0

            await asyncio.sleep(1.0)

    async def set_depth(self, depth):
        self.depth = depth

    async def set_manager(self, host, port):
        self._manager_endpoint = await Endpoint.create(
            service_type="Manager",
            reader=None,
            writer=None,
            host=host,
            port=port
        )

    async def create_server(self, host="0.0.0.0", port=0):
        self._local_endpoint = (host, port)

        self._local_endpoint_socket = await asyncio.start_server(
            self.on_client_connect,
            host=self._local_endpoint[0],
            port=self._local_endpoint[1],
        )

        self._local_endpoint = self._local_endpoint_socket.sockets[0].getsockname()

    async def on_client_connect(self, reader, writer):
        local_socket = writer.get_extra_info('socket')
        remote_endpoint_host, remote_endpoint_port = local_socket.getpeername()

        _client = await Endpoint.create(
            service_type=None,
            reader=reader,
            writer=writer,
            host=remote_endpoint_host,
            port=remote_endpoint_port
        )

        self._remote_endpoints.append(_client) # TODO fuckup?

        tcpserver_log.info("[%s] incoming connection from %s:%s. Readystate: %s",
                           self._service_name,
                           _client.host,
                           _client.port,
                           _client.ready
                           )
        while _client.ready:
            """Await data from the client endpoint."""
            data = await _client.read()

            """Callback on client message."""
            await self.on_client_message(_client, data)

            """Process callback for data manipulation."""
            data = await self._process(data)

            """Forward the data to next hop (if applicable)."""
            await self.forward(data)

            """Update performance counters for ingoing."""
            self._diag_throughput_in += 1

    async def on_manager_read(self):
        while self._manager_endpoint.ready:
            """Await data from the client endpoint."""
            data = await self._manager_endpoint.read()
            fn = getattr(self, "manager_response_%s" % data.command, None)

            if fn:
                await fn(data.command, data.payload)

    async def manager_response_subscription_fail(self, command, payload):
        await asyncio.sleep(TCPServer.SUBSCRIPTION_FAIL_SLEEP, loop=self._loop)
        await self.connect_remote_service()

    async def manager_response_subscription_ok(self, command, payload):
        endpoint_id = payload["id"]
        host = payload["host"]
        port = payload["port"]
        subscribed_endpoint = [x for x in self._remote_endpoints if x.id == endpoint_id][0]

        await subscribed_endpoint.connect(host=host, port=port)

    async def manager_response_poll_request(self, command, payload):
        poll_response = PollResponseMessage(data=dict(
            throughput_in=0 if not self._diag_throughput_in_history else mean(self._diag_throughput_in_history),
            throughput_out=0 if not self._diag_throughput_out_history else mean(self._diag_throughput_out_history)
        ))
        await self._manager_endpoint.write(poll_response)

    async def connect_manager(self):
        await self._manager_endpoint.connect()
        self._manager_endpoint.type = "Manager"

    async def on_client_message(self, client, x):
        return None

    async def forward(self, x):
        if not self._remote_endpoints:
            return
        for endpoint in self._remote_endpoints:

            if not endpoint.ready:
                continue

            if x is None:
                continue # print(self._service_name, endpoint)
                # Todo for Model, x is None. Find out why....

            await endpoint.write(x)

            """Update performance counters for outgoing"""
            self._diag_throughput_out += 1


    async def register_service(self):
        """
        This function sends a register  service command to the manager. THe manager then logs the event and add the
        local endpoint as the specified service (service_name).
        :return:
        """
        register_service = RegisterService(
            service=self._service_name,
            local_endpoint=self._local_endpoint,
            pid=self.pid,
            depth=self.depth
        )

        tcpserver_log.info("[%s]: registering with the manager service. Payload: %s",
                           self._service_name,
                           register_service.payload
                           )

        await self._manager_endpoint.write(register_service)

    async def set_remote_services(self, remote_service_names):
        if not remote_service_names:
            return

        for remote_service_name in remote_service_names:
            self._remote_endpoints.append(await Endpoint.create(remote_service_name))

    async def connect_remote_service(self):
        for remote_endpoint in self._remote_endpoints:

            if remote_endpoint.ready:
                # Do not subscribe when socket is active
                continue
                #raise ConnectionAbortedError("A remote endpoint was already active! (DEBUG)")

            service_type = remote_endpoint.type

            subscription_message = SubscribeService(
                service=service_type,
                id=remote_endpoint.id
            )

            tcpserver_log.info("[%s]: requesting subscription to service '%s'.", self._service_name, service_type)

            """Subscribe to remote service"""
            await self._manager_endpoint.write(subscription_message)

    def run(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self.async_start())

        tasks = [
            self._loop.create_task(self.__diagnostics()),
            self._loop.create_task(self._run())
        ]

        self._loop.run_until_complete(
            asyncio.wait(tasks)
        )

        self._loop.run_forever()


    async def async_start(self):
        await self.connect_manager()
        await self.create_server()
        await self.register_service()
        await self.connect_remote_service()
        self._loop.create_task(self.on_manager_read())
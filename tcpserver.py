import asyncio
from collections import deque
from multiprocessing import Process
from statistics import mean

from client import Endpoint, EndpointInfo
from logger import manager_log, tcpserver_log
from messages import RegisterService, SubscribeService, PollResponseMessage, ReadBufferOverflowMessage


class TCPServer(Process):
    SUBSCRIPTION_FAIL_SLEEP = 5

    def __init__(self):
        Process.__init__(self)
        self._service_name = self.__class__.__name__

        self._manager_endpoint_info = None
        self._manager_endpoint = None

        self._local_endpoint_socket = None
        self._local_endpoint = None

        self._remote_endpoints = []
        self._remote_endpoints_info = []

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

    """
    #
    #
    # Initialization functions
    #
    #
    """

    async def set_manager_info(self, host, port):
        self._manager_endpoint_info = EndpointInfo("Manager", host, port)

    async def set_remotes_info(self, remotes):
        if not remotes:
            return

        self._remote_endpoints_info.extend([EndpointInfo(name=x, host=None, port=None) for x in remotes])

    async def set_depth(self, depth):
        self.depth = depth

    """"
    #
    #
    # Manager related function
    #
    #
    """
    async def connect_manager(self):
        """
        Connects to the manager. This is inside the process async context.
        :return:
        """

        manager_endpoint = Endpoint(
            service_type=self._manager_endpoint_info.name,
            loop=self._loop,
            host=self._manager_endpoint_info.host,
            port=self._manager_endpoint_info.port)

        await manager_endpoint.connect()

        self._manager_endpoint = manager_endpoint

    async def loop_manager_read(self):

        while self._manager_endpoint.ready:
            """Await data from the client endpoint."""
            data = await self._manager_endpoint.read()
            fn = getattr(self, "manager_response_%s" % data.command, None)

            if fn:
                await fn(data.command, data.payload)

    async def manager_response_subscription_fail(self, command, payload):
        await asyncio.sleep(TCPServer.SUBSCRIPTION_FAIL_SLEEP, loop=self._loop)
        await self.request_subscribe_remote_endpoints()

    async def manager_response_subscription_ok(self, command, payload):
        endpoint_id = payload["id"]
        host = payload["host"]
        port = payload["port"]

        endpoint_info = [x for x in self._remote_endpoints_info if x.id == endpoint_id][0]
        endpoint = Endpoint(
            service_type=endpoint_info.name,
            loop=self._loop,
            host=host,
            port=port
        )

        self._remote_endpoints.append(endpoint)

        await endpoint.connect()

    async def manager_response_poll_request(self, command, payload):
        poll_response = PollResponseMessage(data=dict(
            throughput_in=0 if not self._diag_throughput_in_history else mean(self._diag_throughput_in_history),
            throughput_out=0 if not self._diag_throughput_out_history else mean(self._diag_throughput_out_history)
        ))
        await self._manager_endpoint.write(poll_response)

    """
    #
    #
    #
    #
    #
    """

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

    async def create_server(self, host="0.0.0.0", port=0):
        self._local_endpoint = (host, port)

        self._local_endpoint_socket = await asyncio.start_server(
            self.on_client_connect,
            host=self._local_endpoint[0],
            port=self._local_endpoint[1],
        )

        self._local_endpoint = self._local_endpoint_socket.sockets[0].getsockname()

        tcpserver_log.info("[%s] server ready and listening for clients on %s:%s",
                           self._service_name,
                           *self._local_endpoint)

    async def on_client_connect(self, reader, writer):
        local_socket = writer.get_extra_info('socket')
        remote_endpoint_host, remote_endpoint_port = local_socket.getpeername()

        _client = Endpoint(
            service_type=None,
            loop=self._loop,
            reader=reader,
            writer=writer,
            host=remote_endpoint_host,
            port=remote_endpoint_port
        )

        await _client.start()

        self._remote_endpoints.append(_client)

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

    async def on_client_message(self, client, x):
        return None

    async def forward(self, x):
        if not self._remote_endpoints:
            return

        for endpoint in self._remote_endpoints:

            if not endpoint.ready:
                continue

            await endpoint.write(x)

            """Update performance counters for outgoing"""
            self._diag_throughput_out += 1

    async def request_register_service(self):
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

    async def request_subscribe_remote_endpoints(self):

        for remote_endpoint_info in self._remote_endpoints_info:
            if not remote_endpoint_info.name:
                raise RuntimeError("The name for the remote endpoint cant be blank!")
            """if not remote_endpoint_info.host or not remote_endpoint_info.port:
                raise RuntimeError("Could not initiate connection for endpoint with arguments: %s, %s:%s" %
                                   (remote_endpoint_info.name, remote_endpoint_info.host, remote_endpoint_info.port)
                                   )"""

            subscription_message = SubscribeService(
                service=remote_endpoint_info.name,
                id=remote_endpoint_info.id
            )

            tcpserver_log.info("[%s]: requesting subscription to service '%s'.",
                               self._service_name,
                               remote_endpoint_info.name
                               )

            """Subscribe to remote service"""
            await self._manager_endpoint.write(subscription_message)

    def run(self):
        """
        :return:
        """

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
        await self.create_server()
        await self.connect_manager()
        await self.request_register_service()
        await self.request_subscribe_remote_endpoints()
        self._loop.create_task(self.loop_manager_read())



import asyncio
import pickle
import uuid

import zstd as zstd


from messages import ReadBufferOverflowMessage


class EndpointInfo:

    def __init__(self, name, host, port):
        self.id = "info_" + str(uuid.uuid4())
        self.name = name
        self.host = host
        self.port = port


class Endpoint:
    DELIMETER_SIZE = 3
    DELIMETER = b'\=='

    """Read buffer-overflow mechanism"""
    RBO_DECAY = .000001  # The rate of which the rbo mechanism decay on writer side
    RBO_INCREASE = .000002  # The rate of which the rbo mechanism increases on overflow
    RBO_POLL_WAIT = .1  # The read-buffer-oveflow check wait-time
    RBO_LIMIT = 1000  # The limit when overflow threshold is reached
    RBO_SEND_VALUE = 0  # The value that the reader request sender to wait
    RBO_WAIT_VALUE = 0  # The value that the writer awaits per send

    RETRY_TIMER = 1  # TODO 30 when prod

    def __init__(self, service_type, loop, reader=None, writer=None, host=None, port=None):
        self._loop = loop
        self.type = service_type
        self.id = str(uuid.uuid4())
        self.reader = reader
        self.writer = writer

        self.host = host
        self.port = port

        self.metadata = dict()
        self.diagnosis = dict()

        self.rq = asyncio.Queue(loop=self._loop)

        """Ready state is false by default (not connected to remote. 
        If true, reader must not be EOF and writer can write EOF."""
        self.ready = False
        if reader and writer and not reader.at_eof() and writer.can_write_eof():
            self.ready = True

    async def connect(self, host=None, port=None):

        host = host if host else self.host
        port = port if port else self.port

        if host is None or port is None:
            raise ConnectionError("Could not connect to the service: %s, Reason: No Host or Port supplied!", self.type)

        try:
            self.reader, self.writer = await asyncio.open_connection(host=host, port=port)
            self.ready = True
            await self.start()
        except ConnectionRefusedError as cre:
            await asyncio.sleep(Endpoint.RETRY_TIMER)
            self._loop.create_task(self.connect(host=host, port=port))

    async def start(self):
        """Start Loops"""
        self._loop.create_task(self._loop_stream_reader())
        self._loop.create_task(self._loop_buffer_control())

    async def handle_special_message(self, bytedata):
        data = await self.deserialize(bytedata)

        if data.command == "read_buffer_overflow":
            print(data.payload)
            Endpoint.RBO_WAIT_VALUE = data.payload["duration"]

    async def _loop_stream_reader(self):
        """
        Reads the network stream
        :return:
        """
        while True:
            data = (await self.reader.readuntil(Endpoint.DELIMETER))[:-Endpoint.DELIMETER_SIZE]

            if data[0] == ord("="):  # Might be fucked up
                await self.handle_special_message(data[1:])
                continue

            await self.rq.put(data)

    async def read(self):
        data = await self.rq.get()
        return await self.deserialize(data)

    async def _loop_buffer_control(self):
        """
        Ensures that the buffer does not overflow. Sends message to the sender when the buffer gets to big.
        :return:
        """

        rbom = ReadBufferOverflowMessage(
            id=self.id,
            duration=0
        )

        while True:
            """Do nothing if the reader object does not exist (pre-setup)."""
            if not self.reader:
                await asyncio.sleep(Endpoint.RBO_POLL_WAIT)
                continue

            """Check if the queue has reached the limit."""
            if self.rq.qsize() > Endpoint.RBO_LIMIT:

                """The queue has overflowed."""

                """Increase the send_value for wait time."""
                Endpoint.RBO_SEND_VALUE += Endpoint.RBO_INCREASE

                """Update the rbom object."""
                rbom.payload["duration"] = Endpoint.RBO_SEND_VALUE
                rbom.payload["size"] = self.rq.qsize()

                """Write the rbom to the socket stream."""
                await self.write(rbom, special=True)
            else:
                """The queue did not overflow. Reduce sleep"""
                Endpoint.RBO_SEND_VALUE = max(0, Endpoint.RBO_SEND_VALUE - Endpoint.RBO_DECAY)

            await asyncio.sleep(Endpoint.RBO_POLL_WAIT)

    async def write(self, data, special=False):
        serialized = await self.serialize(data)
        if special:
            serialized = b'=' + serialized

        self.writer.write(serialized + Endpoint.DELIMETER)
        await asyncio.sleep(Endpoint.RBO_WAIT_VALUE)

    async def deserialize(self, cryped_message):
        #return pickle.loads(cryped_message)
        return pickle.loads(zstd.decompress(cryped_message))

    async def serialize(self, message):
        #return pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        return zstd.compress(
            pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        )

    def toDict(self):
        return dict(
            service=self.type,
            local_endpoint=dict(
                id=self.id,
                host=self.host,
                port=self.port
            ),
            remote_endpoint=dict(
                id=self.id,
                diagnosis=self.diagnosis,
                service=self.metadata["service"],
                host=self.metadata["host"],
                port=self.metadata["port"],
                pid=self.metadata["pid"],
                depth=self.metadata["depth"],
                remotes=[
                    x.toDict() for x in self.metadata["remotes"]
                ]
            )
        )
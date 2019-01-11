import asyncio
import pickle
import uuid
from asyncio import IncompleteReadError
import inspect
import zstd as zstd

from logger import manager_log
from messages import ReadBufferOverflowMessage
from asyncio import StreamWriter

class Endpoint:
    DELIMETER_SIZE = 3
    DELIMETER = b'\=='

    READ_BUFFER_OVERFLOW_LIMIT = 50000 #50000000  # The read buffer overflows when this value is reached
    READ_BUFFER_OVERFLOW_POLL_SLEEP = 1  # The frequency of which the polling method checks for overflow
    READ_BUFFER_OVERFLOW_WRITE_SLEEP_STEP_SIZE = 0.01  # The value the sleep duration is increased with when overflowing
    READ_BUFFER_OVERFLOW_CURRENT_SLEEP = 0  # Current sleep duration when overflow occurred.

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

        self._loop.create_task(self.buffer_control())
        self.rq = asyncio.Queue(loop=self._loop)

        """Ready state is false by default (not connected to remote. 
        If true, reader must not be EOF and writer can write EOF."""
        self.ready = False
        if reader and writer and not reader.at_eof() and writer.can_write_eof():
            self.ready = True


    @staticmethod
    async def create(service_type, loop, reader=None, writer=None, host=None, port=None):
        print(loop)
        return Endpoint(service_type=service_type, loop=loop, reader=reader, writer=writer, host=host, port=port)

    async def connect(self, host=None, port=None):

        host = host if host else self.host
        port = port if port else self.port

        if host is None or port is None:
            raise ConnectionError("Could not connect to the service: %s, Reason: No Host or Port supplied!", self.type)

        try:
            self.reader, self.writer = await asyncio.open_connection(host=host, port=port)
            self.ready = True
        except ConnectionRefusedError as cre:
            # TODO this
            raise NotImplementedError("TODO THIS")

    async def read_stream(self):

        while True:
            data = (await self.reader.readuntil(Endpoint.DELIMETER))[:-Endpoint.DELIMETER_SIZE]
            await self.rq.put(data)

    async def read(self):
        data = await self.rq.get()
        return await self.deserialize(data)

    async def buffer_control(self):

        rbom = ReadBufferOverflowMessage(
            id=self.id,
            duration=0
        )

        while True:
            if not self.reader:
                await asyncio.sleep(Endpoint.READ_BUFFER_OVERFLOW_POLL_SLEEP)
                continue

            buflen = len(self.reader._buffer)
            if buflen > Endpoint.READ_BUFFER_OVERFLOW_LIMIT:
                print("Overflow!", buflen)
                #Endpoint.READ_BUFFER_OVERFLOW_CURRENT_SLEEP += Endpoint.READ_BUFFER_OVERFLOW_WRITE_SLEEP_STEP_SIZE
                #rbom.payload["duration"] = Endpoint.READ_BUFFER_OVERFLOW_CURRENT_SLEEP
                #await self.write(rbom)

            await asyncio.sleep(Endpoint.READ_BUFFER_OVERFLOW_POLL_SLEEP)

            # Todo gradual decrease

    async def write(self, data):
        serialized = await self.serialize(data)

        if not self.writer.can_write_eof():
            print("STILL TRYING TO WRITER :(")

        self.writer.write(serialized + Endpoint.DELIMETER)

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
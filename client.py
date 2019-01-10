import asyncio
import pickle
import uuid
from asyncio import IncompleteReadError

import zstd as zstd

from logger import manager_log


class Endpoint:
    DELIMETER_SIZE = 3
    DELIMETER = b'\=='

    RETRY_TIMER = 1  # TODO 30 when prod

    def __init__(self, service_type, reader=None, writer=None, host=None, port=None):
        self.type = service_type
        self.id = str(uuid.uuid4())
        self.reader = reader
        self.writer = writer

        self.host = host
        self.port = port

        self.metadata = dict()
        self.diagnosis = dict()

        """Ready state is false by default (not connected to remote. 
        If true, reader must not be EOF and writer can write EOF."""
        self.ready = False
        if reader and writer and not reader.at_eof() and writer.can_write_eof():
            self.ready = True

    @staticmethod
    async def create(service_type, reader=None, writer=None, host=None, port=None):
        return Endpoint(service_type=service_type, reader=reader, writer=writer, host=host, port=port)

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
            manager_log.warning("Could not connect to %s:%s, Retrying in %s...", host, port, Endpoint.RETRY_TIMER)
            await asyncio.sleep(Endpoint.RETRY_TIMER)
            client = await Endpoint.connect(host, port)
            return client

    async def read(self):
        try:
            data = (await self.reader.readuntil(Endpoint.DELIMETER))[:-Endpoint.DELIMETER_SIZE]
        except IncompleteReadError as e:
            self.ready = False
            return None

        return await self.deserialize(data)

    async def write(self, data):
        serialized = await self.serialize(data)
        try:
            self.writer.write(serialized + Endpoint.DELIMETER)
        except Exception as e:
            print("------------------------")
            print(e)
            print("------------------------")
            exit(0)
        #await self.writer.drain()

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
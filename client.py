import asyncio
import pickle
from asyncio import IncompleteReadError

from logger import manager_log


class Client:
    DELIMETER_SIZE = 3
    DELIMETER = b'\=='

    RETRY_TIMER = 1  # TODO 30 when prod

    def __init__(self, reader, writer, reconnect=True):
        self.reader = reader
        self.writer = writer
        self._peername = [str(x) for x in writer.get_extra_info('peername')]
        self._sockname =  [str(x) for x in writer.get_extra_info('sockname')]
        self.name = ':'.join(self._peername)  # ('127.0.0.1', 63122)
        self.ready = True
        self._reconnect = reconnect

        #manager_log.warning("Client %s => %s", self._peername, self._sockname)

    @staticmethod
    async def connect(host, port):
        try:
            return Client(*await asyncio.open_connection(host=host, port=port))
        except ConnectionRefusedError as cre:
            manager_log.warning("Could not connect to %s:%s, Retrying in %s...", host, port, Client.RETRY_TIMER)
            await asyncio.sleep(Client.RETRY_TIMER)
            client = await Client.connect(host, port)
            return client

    async def read(self):
        try:
            data = (await self.reader.readuntil(Client.DELIMETER))[:-Client.DELIMETER_SIZE]
        except IncompleteReadError as e:
            self.ready = False
            return None

        return await self.deserialize(data)

    async def write(self, data):
        serialized = await self.serialize(data)
        self.writer.write(serialized + Client.DELIMETER)
        await self.writer.drain()

    async def deserialize(self, cryped_message):
        return pickle.loads(cryped_message)
        #return pickle.loads(zstd.decompress(cryped_message))

    async def serialize(self, message):
        return pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        #return zstd.compress(
         #   pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        #)
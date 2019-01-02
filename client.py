import asyncio
import pickle
import ujson
import zstd
from asyncio import IncompleteReadError

from commands import Commands
from logger import manager_log


class Client:
    SEPARATOR = b'\n\r\n\r'
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
            data = await self.reader.readuntil(separator=Client.SEPARATOR)
            data = data[:-len(Client.SEPARATOR)]  # Todo optimize?

        except IncompleteReadError as e:
            return Commands.QUIT

        return await self.deserialize(data)

    async def write(self, data):
        self.writer.write(await self.serialize(data) + Client.SEPARATOR)
        await self.writer.drain()

    async def deserialize(self, cryped_message):
        return pickle.loads(zstd.decompress(cryped_message))

    async def serialize(self, message):
        return zstd.compress(
            pickle.dumps(message, protocol=pickle.HIGHEST_PROTOCOL)
        )
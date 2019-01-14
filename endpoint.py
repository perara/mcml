import asyncio
import uuid
from functools import partial
from multiprocessing import Process

import pynng
import inspect
from manager import PickleSerializer
from message import AnnounceMessage, Message

import logging

logger = logging.getLogger("endpoint")
logger.setLevel(level=logging.INFO)

# 1. Create Agent Class Definition, add decorator. (Developer)
# 2. Decorator parses the class definition. Connects to manager with Req/Res pattern


class EndpointSub:

    def __init__(self, local_endpoint):
        self.local_endpoint = local_endpoint
        self.serializer = PickleSerializer()  # TODO set dynamically.
        self.sub = pynng.Sub0()
        self.sub.tcp_keepalive = True
        #self.sub.add_post_pipe_connect_cb(self.__on_connect)
        #self.sub.add_post_pipe_remove_cb(self.__on_disconnect)
        self.sub.dial('tcp://0.0.0.0:41001', block=True)  # TODO - Set dynamically or via config

    async def areceive(self):

        while True:
            message = await self.sub.arecv()
            message = self.serializer.deserialize(d=message)

            #print(message)

    def __on_connect(self, d):
        self.connected = True
        print("[LocalEndpoint-%s]: connected to manager." % self.local_endpoint.id)

    def __on_disconnect(self, d):
        self.sub = None
        self.connected = False


class EndpointPush:

    def __init__(self, local_endpoint):
        self.local_endpoint = local_endpoint
        self.serializer = PickleSerializer()  # TODO set dynamically.
        self.push = pynng.Push0()
        self.push.tcp_keepalive = True
        #self.push.add_post_pipe_connect_cb(self.__on_connect)
        #self.push.add_post_pipe_remove_cb(self.__on_disconnect)
        self.push.dial('tcp://0.0.0.0:41000', block=True)  # TODO - Set dynamically or via config

    def send(self, msg):
        ser_msg = self.serializer.serialize(d=msg)
        self.push.send(ser_msg)
        self.local_endpoint.stats.out_counter += 1

    async def asend(self, msg):
        ser_msg = self.serializer.serialize(d=msg)
        await self.push.asend(ser_msg)
        self.local_endpoint.stats.out_counter += 1

    def __on_connect(self, d):
        self.connected = True
        print("[LocalEndpoint-%s]: connected to manager. (Push)" % self.local_endpoint.id)

    def __on_disconnect(self, d):
        self.s_request = None
        self.connected = False


class Statistics:

    def __init__(self, local_endpoint, loop):
        self.local_endpoint = local_endpoint
        self.loop = loop

        self.in_per_sec = 0
        self.out_per_sec = 0

        self.in_counter = 0
        self.out_counter = 0

        loop.create_task(self.run())

    async def run(self):
        while True:
            self.in_per_sec = self.in_counter
            self.out_per_sec = self.out_counter
            self.in_counter = 0
            self.out_counter = 0
            print("[%s]: In: %s, Out: %s" % (self.local_endpoint.id, self.in_per_sec, self.out_per_sec))
            await asyncio.sleep(1.0, loop=self.loop)


class LocalEndpoint:
    """
    LocalEndpoint class represents the class that were sent to the manager and executed remotely.
    """
    def __init__(self):
        self.id = str(uuid.uuid4())
        self._loop = asyncio.get_event_loop()
        self.stats = Statistics(self, loop=self._loop)
        self.push = EndpointPush(self)
        self.sub = EndpointSub(self)



    @staticmethod
    def remote(clazz):
        instance = clazz()
        return instance

class Endpoint(Process):

    def __init__(self, serializer=PickleSerializer):
        Process.__init__(self)
        self.daemon = True

        self.loop = None

        self.s_request = None

        self.serializer = serializer()  # The serializer used to serialize/deserialize messages

    def __call__(self, *args, **kwargs):
        print(kwargs)

    def run(self):
        """Create new event loop for the forked process."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.loop.run_until_complete(self.async_run())
        self.loop.run_forever()

    async def async_run(self):
        """Setup Request Handler (Request/Response) pattern."""
        self.s_request = pynng.Req0(dial='tcp://0.0.0.0:41000')

        await self.request(AnnounceMessage("test_service", "0.0.0.0", 8080))

    async def request(self, msg):
        """Serialize the message."""
        msg = self.serializer.serialize(msg)

        """Send the message async."""
        await self.s_request.asend(msg)

        """Wait for the message response."""
        return await self.s_request.arecv()

    @staticmethod
    def hook(cls, **kwargs):
        """Retrieve all methods of the decorated class."""
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)

        """Remote dual underscore functions (__init__)."""
        methods = [x for x in methods if not x[0].startswith("__")]

        """Create a LocalEndpoint instance."""
        local_endpoint = type("MCML_%s" % cls.__name__,  (LocalEndpoint, ), {})
        local_endpoint.remote = partial(local_endpoint.remote, local_endpoint)

        """Populate the LocalEndpoint instance with functions transfering via sockets."""
        for (method_name, method_fn) in methods:

            async def a_fn_template(self):

                await self.asend(Message("function_call", dict(
                    id=self.id,
                    fn=method_name
                )))

            def fn_template(self):

                self.send(Message("function_call", dict(
                    id=self.id,
                    fn=method_name
                )))

            setattr(
                local_endpoint,
                method_name,
                fn_template
            )

            setattr(
                local_endpoint,
                "a%s" % method_name,
                a_fn_template
            )

        """Return the LocalEndpoint."""
        return local_endpoint

@Endpoint.hook
class Agent:

    def __init__(self):
        self.test = "HEIEIA"

    async def loop(self):
        while True:
            await self.send(Message("message", dict()))

    async def reset(self):
        pass


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    agents = []

    for x in range(16):
        agent = Agent.remote()
        agents.append(agent)


    async def spam(agent):
        while True:
            await agent.push.asend(Message("message", dict()))


    loop.run_until_complete(
        asyncio.wait([spam(a) for a in agents])
    )

    loop.run_forever()
import pynng
import asyncio

in_count = 0
out_count = 0

async def send(sender):
    global out_count
    while True:
        await sender.asend(b'Hello World')

        out_count += 1

async def recv(receiver):
    global in_count
    while True:
        await receiver.arecv()
        in_count += 1

async def counter():
    global in_count, out_count
    while True:
        print("IN: ", in_count, "OUT: ", out_count)
        in_count = 0
        out_count = 0
        await asyncio.sleep(1.0)

with pynng.Pair0(listen='tcp://127.0.0.1:54321') as s1, \
        pynng.Pair0(dial='tcp://127.0.0.1:54321') as s2:

    loop = asyncio.get_event_loop()

    loop.create_task(send(s1))
    loop.create_task(recv(s2))
    loop.create_task(counter())

    loop.run_forever()

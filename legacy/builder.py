class Struct:

    def __init__(self, struct):
        self.struct = struct

    async def build(self):

        for cluster in self.struct["model"]:
            previous_service = []
            depth = 0  # Process Depth
            for data in reversed(cluster):

                if "agent" not in data:
                    raise KeyError("Missing 'agent' key in struct layer.")

                agent_cls = data["agent"]
                population = data['population'] if 'population' in data else 1
                extra_remotes = data['extra_remotes'] if 'extra_remotes' in data else []

                if extra_remotes and depth == 0:
                    depth = 1

                all_remotes = [x.__name__ for x in extra_remotes] + previous_service

                for i in range(population):

                    obj = agent_cls()

                    await obj.set_manager_info(**self.struct["manager"])
                    await obj.set_remotes_info(remotes=all_remotes)
                    await obj.set_depth(depth)

                    obj.daemon = True
                    obj.start()

                depth += 1

                previous_service = [agent_cls.__name__]


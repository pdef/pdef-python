import pdef
from world import World, Human, Sex
from world.continents import ContinentName


def json_format():
    # Read a human from a JSON string.
    human = Human.from_json("")
    human.continent = ContinentName.AFRICA

    # Serialize a human to a JSON string.
    json = human.to_json()
    print json

def client():
    # Create an HTTP RPC client.
    client = pdef.rpc_client(World, url='http://example.com/world/')
    world_client = client.proxy()

    # Create a man.
    man = world_client.humans().create(
        Human(1, name='John', sex=Sex.MALE, continent=ContinentName.ASIA))

    # Switch day/night.
    world_client.switchDayNight()


def server():
    world_service = get_my_world_implementation()
    handler = pdef.rpc_handler(World, world_service)
    wsgi_app = pdef.wsgi_app(handler)

    # Pass it to your web server.

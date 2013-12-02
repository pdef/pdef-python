import datetime
import pdef
from world import World, Human, Sex
from world.continents import ContinentName
from world.space import Location


def messages():
    human = Human(id=1, name="John")
    human.location = Location(lat=30, lng=40)
    human.birthday = datetime.datetime(1987, 8, 7)


def json_format():
    # Read a human from a JSON string.
    human = Human.from_json("")
    Human.from_json_stream()
    human.continent = ContinentName.AFRICA

    # Serialize a human to a JSON string.
    json = human.to_json()

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

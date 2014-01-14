Pdef Python
===========
Python code generator for [Pdef compiler](https://github.com/pdef/pdef)
and Python implementation of descriptors, JSON format and HTTP RPC.

Requirements
------------
Python 2.6 or Python 3.3+.


Installation
------------
- Code generator:
    ```bash
    $ pip install pdef-java
    ```

    Or [download](https://github.com/pdef/pdef-python/releases) the release,
    unzip it and in the `generator` directory run:
    ```bash
    $ python setup.py install
    ```

    The python generator will appear in the installed generators:
    ```bash
    $ pdefc generate -h
    usage: pdefc generate [...]
    available generators:
      - python: Python code generator, supports module names, does not support prefixes.
    ```

- Python package:
    ```bash
    $ pip install pdef
    ```

    Or add it as a requirement to your project in `setup.py` or in pip `requirements.txt`.
    See [releases](https://github.com/pdef/pdef-python/releases) for the latest version.

Code generation
---------------
Pass a pdef package path or a url to the compiler:
```bash
$ pdefc generate-python https://raw.github.com/pdef/pdef/1.1/example/world.yaml \
    --out generated
```

The generator uses absolute module names (`package.module`) + `protocol.py` as python module names.
For example, `world.continents` is converted into `world/continents/protocol.py`.
Use `--module` to manually map pdef modules to python modules.
```bash
$ pdefc generate-python https://raw.github.com/pdef/pdef/1.1/example/world.yaml \
    --module world.space:world_space
    --module world:world_api
    --out generated
```

Messages
--------
Generated messages implement `__eq__`, `__copy__`, `__deepcopy__`, and `__str__` magic methods,
and merging methods. The messages are not thread-safe. The examples are based
on the [pdef example package](https://github.com/pdef/pdef/tree/master/example).

```python
human = Human(id=1, name="John")
human.location = Location(lat=30, lng=40)
human.birthday = datetime.datetime(1900, 1, 2)

import copy
another = copy.deepcopy(human)

assert copy == human
```

Messages support merging which deep copies fields from a source message to a destination one.
```python
human = Human(id=1, name="John")

another = Human()
another.merge(human)

assert another == human
```

Messages try to be None-safe and return default values for empty fields.
If an empty field is a collection or a message then it is initialized to an empty
object on the first access.
```python
# All properties return default values when the fields are empty.
human = Human()
assert human.id == 0
assert human.name == ""

# Special properties allow to check if the field is present.
assert not human.has_id
assert not human.has_name

# Absent collection and message fields are initialized to empty objects on first access.
continent = Continent()
assert not continent.has_humans

# The collection is initialized to an empty one.
continent.humans.append(human)
assert continent.humans == [human]
```

JSON Format
-----------
Pdef uses built-in json parser/serializer:
```python
# From a JSON-compatible dictionary.
human = Human.from_dict({
    "id": 123
    "name": "John})

# From a JSON string.
s = get_json_string()
human = Human.from_json(s)

# From a file-like object.
with open('human.json', 'rt') as f:
    human = Human.from_json_stream(f)
```

Serialization:
```python
# To a JSON-compatible dictionary.
d = human.to_dict()

# To a JSON string.
s = human.to_json(ident=None)

# To a file-like object.
with open('myfile.json', 'wt') as f:
    human.to_json_stream(f, indent=None)
```

Use `pdef.jsonformat` to read/write other pdef data types:
```python
# Write a list of ints to a JSON-string.
list0 = [1, 2, 3]
listd = pdef.descriptors.list0(pdef.descriptors.int32)
s = pdef.jsonformat.write(list0, listd)

# Read a list of ints from a JSON-string.
list1 = pdef.jsonformat.read(s, listd)
assert list0 == list1
```


HTTP RPC Client
---------------
RPC clients are thread-safe.

Create a default HTTP RPC client based on [requests](http://www.python-requests.org/en/latest/).
```python
client = pdef.rpc_client(World, url='http://example.com/world/')
world_client = client.proxy()

# Execute a remote method.
humans = world.humans().all(limit=10, offset=0)

# Execute a void remote method.
world.switchDayNight()
```

None primitive results are converted into default values.
```python
# It's safe to write:
count = in world.humans().count()
count += 1  # Cannot be None
```

Full client example:
```python
# Create a requests session.
session = my_requests_session()

# Create an rpc client.
client = pdef.rpc_client(World, url='http://example.com/world/', session=session)

# Create an interface proxy with the client as an invocation handler.
proxy = pdef.proxy(World, invocation_handler=client)

# Execute a remote method.
proxy.humans().all(limit=10)
```

HTTP RPC Server
---------------
RPC handlers are thread-safe.

Create an rpc handler and a WSGI application:
```python
world = get_my_world()
handler = pdef.rpc_handler(World, world)
wsgi_app = pdef.wsgi_app(handler)
# Pass the app to a web server.
```

None primitive arguments are converted into default values:
```python
class MyHumans(Humans):
    def all(self, limit, offset):
        # None limit and offset are set to 0.
        pass
```

To support other frameworks (such as Django, Flask, etc.) you need to convert custom requests
into `RpcRequests` and handle `RpcResults`.
```python
# In Django something like this will work.

# urlpatterns
urlpatterns = patterns('',
    url(r'^myapp/api/(?P<path>\.+)$', 'myapp.views.api'),
)

# views
def api(request, path):
    # Convert a django request into an rpc request.
    rpc_req = RpcRequest(method=request.method, path=path)
    rpc_req.query = request.GET
    rpc_req.post = request.POST

    # Handle the rpc request.
    handler = get_rpc_handler()
    success, rpc_result = handler(rpc_req)

    # Convert the rpc result into a django response.
    response = HttpResponse(rpc_result.to_json(), content_type="application/json;charset=utf-8")
    if success:
        # It's a successful result.
        response.status_code = 200
    else:
        # It's an expected application exception.
        response.status_code = 422 # Unprocessable entity.

    # Send the response.
    return response
```

License and Copyright
---------------------
Copyright: 2013 Ivan Korobkov <ivan.korobkov@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

import json

site_name = "zero-to-tech"

def make_data():
    data = {"message": "hello, world", "from": site_name}
    return json.dumps(data)

print(make_data())

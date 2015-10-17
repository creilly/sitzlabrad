import json

def mangle(d):
    return {
        key.replace(' ','_'):value 
        for key, value in d.items()
    }

def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

def load_json(text):
    return byteify(json.loads(text))

def dump_json(json_object):
    return json.dumps(json_object)

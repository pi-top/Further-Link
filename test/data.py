directory = {
    'name': 'test_directory',
    'files': {
        'test.py': {
            'type': 'text',
            'content': 'from lib import call_lib\nprint(call_lib())'
        },
        'lib.py': {
            'type': 'text',
            'content': 'def call_lib():\n  return "lib called"'
        },
        'image.jpg': {
            'type': 'url',
            'content': 'https://placekitten.com/50/50'
        }
    }
}


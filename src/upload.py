import os
from . import BadUpload
import aiofiles
from aiohttp import ClientSession
from shutil import rmtree

file_types = ['url', 'text']

def file_is_valid(file):
    return (
        'type' in file and
        file['type'] in file_types and
        'content' in file and
        isinstance(file['content'], str)
    )


def directory_is_valid(directory):
    return (
        'name' in directory and
        isinstance(directory['name'], str) and
        'files' in directory and
        isinstance(directory['files'], object) and
        all(file_is_valid(file) for file in directory['files'].values())
    )


async def download_file(url, file_path):
    async with ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200

            async with aiofiles.open(file_path, 'wb') as file:
                await file.write(await response.read())


async def upload(directory):
    try:
        directory_name = directory['name']
        if '.' in directory_name:
            raise Exception('Forbidden directory name')

        work_dir = os.environ.get('FURTHER_LINK_WORK_DIR', os.path.join(os.environ.get('HOME'), '.further/projects'))
        directory_path = os.path.join(work_dir, directory_name)

        if os.path.exists(directory_path):
            rmtree(directory_path)

        os.makedirs(directory_path, exist_ok=True)

        for file_name, file_info in directory['files'].items():
            file_path = os.path.join(directory_path, file_name)

            if file_info['type'] == 'text':
                async with aiofiles.open(file_path, 'w') as file:
                    await file.write(file_info['content'])

                continue

            if file_info['type'] == 'url':
                await download_file(file_info['content'], file_path)

    except Exception as e:
        raise BadUpload()

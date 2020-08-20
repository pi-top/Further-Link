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
        isinstance(file['content'], dict)
    )


def directory_is_valid(directory):
    return (
        'name' in directory and
        isinstance(directory['name'], str) and
        'files' in directory and
        isinstance(directory['files'], list) and
        all(file_is_valid(file) for file in directory['files'])
    )


def valid_url_content(content):
    return (
        'url' in content and
        isinstance(content['url'], str) and
        'bucketName' in content and
        isinstance(content['bucketName'], str) and
        'fileName' in content and
        isinstance(content['fileName'], str) and
        'aliasName' in content and
        isinstance(content['aliasName'], str)
    )


async def download_file(url, file_path):
    async with ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200

            async with aiofiles.open(file_path, 'wb') as file:
                await file.write(await response.read())


async def upload(directory):
    try:
        id = directory['name']
        if '.' in id:
            raise Exception('Forbidden directory name')

        work_dir = os.environ.get('FURTHER_LINK_WORK_DIR', os.path.join(
            os.environ.get('HOME'), 'further'))

        # clear the sym links every time
        sym_directory_path = os.path.join(work_dir, id)
        if os.path.exists(sym_directory_path):
            rmtree(sym_directory_path)
        os.makedirs(sym_directory_path, exist_ok=True)

        for file in directory['files']:
            if file['type'] == 'url':
                content = file['content']
                if not valid_url_content(content):
                    raise Exception('Invalid url content')

                bucketName = content['bucketName']
                fileName = content['fileName']
                url = content['url']

                directory_path = os.path.join(work_dir, bucketName)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)
                file_path = os.path.join(directory_path, fileName)
                if not os.path.exists(file_path):
                    await download_file(url, file_path)

                aliasName = content['aliasName']
                symlink_path = os.path.join(sym_directory_path, aliasName)
                os.symlink(file_path, symlink_path)
            # if file['type'] == 'text' etc
    except Exception as e:
        raise BadUpload(e)

import os


def doesFileExist(path, name):
    return os.path.exists(path + name)

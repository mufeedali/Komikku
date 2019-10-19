import subprocess


def folder_size(path):
    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE)

    return res.stdout.split()[0].decode()

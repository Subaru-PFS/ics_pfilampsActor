from importlib import reload

import socketserver
import subprocess

def calibShell(object):
    def __init__(self):
        self.connect()


def main(argv=None):
    if isinstance(argv, str):
        import shlex
        argv = shlex.split()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default=1025, help='TCP port to listen on.')
    parser.add_argument()
    opts = parser.parse(argv)

if __name__ == "__main__":
    main()

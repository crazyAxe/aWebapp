#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os, time, subprocess, sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def log(s):
    print('[monitor] %s ' % s)


class myFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, fn):
        super(myFileSystemEventHandler, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endwith('.py'):
            log('python source file change: %s' % event.src_path)
        self.restart()


command = ['echo', 'ok']
process = None


def kill_process():
    global process
    if process:
        log('kill process [%s]' % process.pid)
        process.kill()
        process.wait()
        log('process [%s] ended with %s' % (process.pid, process.returncode))
        process = None


def start_process():
    global process, command
    log('start process %s ...' ' '.join(command))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(path, callback):
    observer = Observer()
    observer.schedule(myFileSystemEventHandler, path, recursive=True)
    observer.start()
    log('start watch %s ' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt as e:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        print('usage: ./pymonitor your-script.py')
        exit(0)
    if argv[0] != 'python3':
        argv.insert(0, 'python3')
    command = argv
    path = os.path.abspath('.')
    start_watch(path, None)

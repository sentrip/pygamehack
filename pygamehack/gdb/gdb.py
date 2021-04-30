import re
import io
import os
import signal
import subprocess
import contextlib
from collections import deque
from dataclasses import dataclass, field
from distutils.spawn import find_executable
from typing import Any, Callable

from .io import GDBIO


DEFAULT_THREAD = '1'
MAX_HARDWARE_WATCHPOINTS = 4


#region Watch

@dataclass(unsafe_hash=True)
class Watch(object):
    name: str
    address: int
    callback: Callable[['Watch', Any, Any, Any], None] = field(repr=False)
    read: bool = False
    write: bool = True
    c_type: str = ''
    
    def __post_init__(self):
        self._number = ''
        self._thread = ''
        self._active = False

    @property
    def _command(self) -> str:
        mod = 'a' if self.read and self.write else 'r' if self.read else ''
        return f'{mod}watch {self._expression}'

    @property
    def _expression(self) -> str:
        if self.c_type:
            return f'*({self.c_type}*){hex(self.address)}'
        else:
            return f'*{hex(self.address)}'


#endregion

#region GDB

class GDB(object):

    #region Public

    def __init__(self, path=None):
        self._io = None
        self._process = None
        self._timeout = 0.05
        self._command = [_get_gdb_path(path)] + _DEFAULT_GDB_ARGS
        self._attached = False
        self._can_attach = True
        self._suspended = False
        self._active_watches = 0
        self._threads = set()
        self._watches = {}
        self._watch_queue = deque()

    def attach(self, process_id):
        if not self._can_attach:
            return
        self.detach()
        self._attach(process_id)

    def detach(self):
        if self._attached:
            self._detach()

    # Program Control

    def continue_(self):
        self._write('c')
        self._suspended = True

    # TODO: This seems to be unnecessary and we can keep continue_waiting over and over?
    # def interrupt(self):
    #     if self._suspended:
    #         os.kill(self._process.pid, signal.CTRL_C_EVENT)

    def wait(self):
        self._handle(self._io.read(self._wait_done, self._timeout))
        self._suspended = False

    @contextlib.contextmanager
    def continue_wait(self):
        self.continue_()
        yield
        self.wait()
    
    # Watches

    def add_watch(self, watch: Watch, thread: str = DEFAULT_THREAD):
        # assert thread in self._threads, "Invalid thread id"
        assert watch.name not in self._watches and watch._expression not in self._watches
        watch._thread = thread
        self._watches[watch.name] = watch
        self._watches[watch._expression] = watch
        if len(self._watches) < MAX_HARDWARE_WATCHPOINTS:
            self._watch(watch)
            self.wait()
        else:
            self._watch_queue.append(watch)

    def remove_watch(self, watch: Watch):
        if watch._active:
            self._write(f'thread apply {watch._thread} delete {watch._number}')
            self.wait()
        
        del self._watches[watch.name]
        del self._watches[watch._expression]

    #endregion

    #region Private

    def _close(self):
        if self._process:
            self._process.terminate()
        self._process = None
        self._io = None

    def _attach(self, process_id):
        self._process, self._io = _get_gdb_process(self._command)
        self._can_attach = False
        self._write(f'attach {process_id}')
        self.wait()

    def _detach(self):
        self._write('q')
        self._write('y')
        self.wait()
        self._close()

    def _add_queued_watches(self):
        to_add = MAX_HARDWARE_WATCHPOINTS - self._active_watches
        while to_add > 0 and self._watch_queue:
            w = self._pop_next_valid_watch_from_queue()
            if w:
                self._watch(w)
                to_add -= 1
    
    def _pop_next_valid_watch_from_queue(self):
        w = self._watch_queue.popleft()
        while w.name not in self._watches:
            w = self._watch_queue.popleft()
            if not self._watch_queue:
                return None
        return w

    def _watch(self, watch):
        self._write(f'thread apply {watch._thread} {watch._command}')
        self._active_watches += 1

    def _write(self, data):
        # assert not self._suspended, "Cannot write when suspended"
        self._io.write(data)

    def _on_attach(self, result):
        self._attached = True
        self._can_attach = True

    def _on_detach(self, result):
        self._attached = False

    def _on_thread_create(self, result):
        self._threads.add(result['payload']['id'])

    def _on_thread_exit(self, result):
        if result['payload']['id'] in self._threads:
            self._threads.remove(result['payload']['id'])

    def _on_breakpoint_create(self, result):
        bpt = result['payload']['bkpt']
        if bpt['type'] == 'hw watchpoint':
            watch = self._watches[bpt['what']]
            watch._number = bpt['number']
            watch._active = True
    
    def _on_breakpoint_delete(self, result):
        self._active_watches -= 1
        self._add_queued_watches()
    
    def _on_watchpoint_trigger(self, result):
        r = result['payload']
        watch = self._watches[r['wpt']['exp']]
        watch.callback(watch, r['value']['old'], r['value']['new'], r)

    def _handle(self, results):
        for r in results:
            if r['type'] == 'notify':
                # Startup
                if r['message'] == 'thread-group-started':
                    self._on_attach(r)
                if r['message'] == 'thread-group-exited':
                    self._on_detach(r)
                elif r['message'] == 'thread-created':
                    self._on_thread_create(r)
                elif r['message'] == 'thread-exited':
                    self._on_thread_exit(r)
                # Watch
                elif r['message'] == 'breakpoint-created':
                    self._on_breakpoint_create(r)
                elif r['message'] == 'breakpoint-deleted':
                    self._on_breakpoint_delete(r)
                elif r['message'] == 'stopped':
                    if r['payload']['reason'] == 'watchpoint-trigger':
                        self._on_watchpoint_trigger(r)
                # else:
                #     print(r)
            # elif r['type'] == 'result':
            #     print(r)

    def _wait_done(self, results):
        for r in results:
            if r['type'] == 'result' and r['message'] == 'done':
                return True
    
    #endregion

#endregion

#region Helpers

_USING_WINDOWS = True
_DEFAULT_GDB_ARGS = [
    '-silent',          # Do not print any version output when the program starts
    '--nx',             # Do not execute commands from any .gdbinit initialization files.
    '--interpreter=mi3' # Structured output
]


def _get_gdb_path(path):
    gdb_path = find_executable(path or 'gdb')
    if gdb_path is None:
        raise RuntimeError('Could not find gdb executable')
    return gdb_path


def _get_gdb_process(command):
    process = subprocess.Popen(
        command,
        shell=False,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        # creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    return process, GDBIO(process.stdin, process.stdout, process.stderr)

#endregion

import logging
from collections import deque
from dataclasses import dataclass
from threading import Event
from typing import Callable

import psutil
from pygdbmi.gdbcontroller import GdbController, GdbTimeoutError


log = logging.getLogger('pygamehack')
MAX_ACTIVE_WATCHES = 4


@dataclass
class Watch:
    name: str
    number: int
    address: int
    expression: str
    callback: Callable[[str, dict], None]
    write: bool = True
    is_active: bool = False

    @property
    def cmd(self):
        return f'{"" if self.write else "a"}watch {self.expression}'


class GDB(object):
    def __init__(self):
        if any(proc.name() == 'gdb.exe' for proc in psutil.process_iter()):
            raise RuntimeError('GDB already running')

        self.dbg = GdbController()
        self._kill_event = Event()
        self._handlers = {}
        self._watches = {}
        self._pid = 0
        self._watch_queue = deque()
        self._active_watches = 0
        self._to_remove = set()

    def attach(self, pid):
        self._pid = pid
        self._handle_results(self.dbg.write(f'attach {pid}'))

    def watch_address(self, name: str, address: int, handler: Callable[[str, dict], None], write: bool = True) -> Watch:
        watch = Watch(name, 0, address, '*' + hex(address), handler, write)
        self._watches[watch.expression] = watch
        self._watch_queue.append(watch)
        return watch

    def watch_for_changes(self):
        self._watch_for_changes()

    def remove_watch(self, n):
        self._to_remove.add(n)
        self._write(f'thread apply 1 delete {n}')

    def exit(self):
        self._kill_event.set()
        self._write('c')
        self._write('q')
        self.dbg.write('y', read_response=False)
        GDB.kill_process()  # graceful shutdown is hard

    @staticmethod
    def kill_process():
        for proc in psutil.process_iter():
            if proc.name() == 'gdb.exe':
                proc.terminate()

    def _watch_for_changes(self):

        self._add_available_watches()

        while len(self._watches) and not self._kill_event.is_set():
            try:
                self._handle_results(self.dbg.get_gdb_response(timeout_sec=0.1))

            except GdbTimeoutError:
                continue

            except KeyboardInterrupt:
                self._kill_event.set()

        log.info('Exiting...')

    def _activate_watch(self, watch, number):
        watch.is_active = True
        watch.number = number
        self._watches[number] = watch
        log.info(f'Watch {number} created: ' + watch.expression)

    def _delete_watch(self, watch):
        watch.is_active = False
        del self._watches[watch.number]
        del self._watches[watch.expression]
        self._active_watches -= 1
        log.info(f'Watch {watch.number} removed: ' + watch.expression)

    def _add_available_watches(self):
        added = False
        while self._active_watches < MAX_ACTIVE_WATCHES and self._watch_queue:
            watch = self._watch_queue.popleft()
            log.debug(f'Adding watch from queue ({len(self._watch_queue)}) {watch}')
            self._write(f'thread apply 1 {watch.cmd}')
            self._active_watches += 1
            added = True

        self._handle_results(self.dbg.get_gdb_response(timeout_sec=0.01, raise_error_on_timeout=False))

        if added:
            self._write('c')

    def _write(self, cmd):
        self.dbg.write(cmd, timeout_sec=0, raise_error_on_timeout=False, read_response=False)

    _ignored_message_types = {
        'log', 'console',
    }

    _ignored_notification_messages = {
        'running', 'stopped',
        'breakpoint-modified', 'library-loaded',
        'thread-group-added', 'thread-group-started',
        'thread-selected', 'thread-created', 'thread-exited',
    }

    def _handle_results(self, results):
        for r in results:

            t, msg = r['type'], r['message']

            if msg == 'stopped' and r['payload'].get('reason', '') == 'watchpoint-trigger':
                watch = self._watches[r['payload']['wpt']['exp']]
                watch.callback(watch.name, r['payload'])
                if watch.number not in self._to_remove:
                    self._write('c')

            elif msg == 'breakpoint-created':
                brk = r['payload']['bkpt']
                self._activate_watch(self._watches[brk['original-location']], int(brk["number"]))

            elif msg == 'breakpoint-deleted':
                self._delete_watch(self._watches[int(r["payload"]["id"])])
                self._add_available_watches()

            elif msg == 'error':
                raise RuntimeError('GDB: ' + r['payload']['msg'])

            elif t == 'output' and msg is None and r['payload'] == '*stopped':
                log.info('Attached to ' + str(self._pid))

            elif (
                    t in GDB._ignored_message_types
                    or (t == 'result' and (msg == 'done' or msg == 'running'))
                    or (t == 'notify' and msg in GDB._ignored_notification_messages)
            ):
                pass

            elif t == 'notify':
                print(r)

            else:
                log.debug('Unrecognized message: ' + (t or '??') + ' - ' + (msg or '??'))

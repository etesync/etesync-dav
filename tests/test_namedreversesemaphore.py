# Copyright © 2017 Tom Hacohen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import pytest

import time
import uuid
import threading
from etesync_dav.radicale.etesync_cache import NamedReverseSemaphore


class ExThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self):
        super().join()
        if self.exc:
            raise self.exc
        return self.ret

def thread_run(name, expected, barrier=None):
    if barrier is not None:
        timeout = None
    else:
        timeout = 0
    lock2 = NamedReverseSemaphore(name)
    if barrier is not None:
        barrier.wait()
    ret = lock2.acquire(timeout)
    assert expected == ret
    if expected:
        lock2.release()


class TestNamedReverseSemaphore:
    def test_same_key_nolock(self):
        name1 = str(uuid.uuid4())

        lock1 = NamedReverseSemaphore(name1)
        lock2 = NamedReverseSemaphore(name1)
        lock3 = NamedReverseSemaphore(name1)

        lock1.acquire()
        lock2.acquire()
        lock3.acquire()

        lock1.acquire()
        lock1.acquire()

        with lock1:
            with lock2:
                with lock3:
                    with lock1:
                        pass

        lock1.release()
        lock1.release()

        lock3.release()
        lock2.release()
        lock1.release()

    def test_different_key_same_thread(self):
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())

        lock1 = NamedReverseSemaphore(name1)
        lock2 = NamedReverseSemaphore(name2)

        with lock1:
            assert not lock2.acquire(0)
            assert lock1.acquire(0)
            lock1.release()

        assert lock2.acquire(0)
        lock2.release()

        with lock2:
            assert not lock1.acquire(0)
            assert lock2.acquire(0)
            lock2.release()

    def test_same_key_different_thread(self):
        name1 = str(uuid.uuid4())

        lock1 = NamedReverseSemaphore(name1)
        with lock1:
            thread = ExThread(target=thread_run, args=(name1, True), daemon=True)
            thread.start()
            thread.join()

    def test_different_key_different_thread(self):
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())

        thread = ExThread(target=thread_run, args=(name2, True), daemon=True)
        thread.start()
        thread.join()

        lock1 = NamedReverseSemaphore(name1)
        with lock1:
            thread = ExThread(target=thread_run, args=(name2, False), daemon=True)
            thread.start()
            thread.join()

    def test_different_key_different_thread_wait(self):
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())
        barrier = threading.Barrier(2)

        thread = ExThread(target=thread_run, args=(name2, True), daemon=True)
        thread.start()
        thread.join()

        lock1 = NamedReverseSemaphore(name1)
        with lock1:
            thread = ExThread(target=thread_run, args=(name2, True, barrier), daemon=True)
            thread.start()
            barrier.wait()
            # FIXME: hack to make sure we acquired the lock in the other thread
            time.sleep(0.2)
        thread.join()

    def test_multiple_keys_different_thread(self):
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())
        name3 = str(uuid.uuid4())
        barrier = threading.Barrier(3)

        threads = []

        lock1 = NamedReverseSemaphore(name1)
        with lock1:
            threads.insert(0, ExThread(target=thread_run, args=(name2, True, barrier), daemon=True))
            threads[0].start()
            threads.insert(0, ExThread(target=thread_run, args=(name3, True, barrier), daemon=True))
            threads[0].start()

            barrier.wait()
            # FIXME: hack to make sure we acquired the lock in the other thread
            time.sleep(0.2)

        for thread in threads:
            thread.join()

    def test_multiple_keys_multiple_times_different_thread(self):
        name1 = str(uuid.uuid4())
        name2 = str(uuid.uuid4())
        name3 = str(uuid.uuid4())
        barrier = threading.Barrier(5)

        threads = []

        lock1 = NamedReverseSemaphore(name1)
        with lock1:
            threads.insert(0, ExThread(target=thread_run, args=(name2, True, barrier), daemon=True))
            threads[0].start()
            threads.insert(0, ExThread(target=thread_run, args=(name2, True, barrier), daemon=True))
            threads[0].start()
            threads.insert(0, ExThread(target=thread_run, args=(name3, True, barrier), daemon=True))
            threads[0].start()
            threads.insert(0, ExThread(target=thread_run, args=(name3, True, barrier), daemon=True))
            threads[0].start()

            barrier.wait()
            # FIXME: hack to make sure we acquired the lock in the other thread
            time.sleep(0.2)

        for thread in threads:
            thread.join()

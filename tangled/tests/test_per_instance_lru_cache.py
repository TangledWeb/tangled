"""Tests for :func:`tangled.decorators.per_instance_lru_cache`.

This is a copy of Lib/test/test_functools.py from the CPython source
modified for per-instance caching of methods and properties.

"""
import builtins
import copy
import functools
import pickle
import sys
import threading
import time
import unittest
from random import choice
from test import support

from tangled.decorators import per_instance_lru_cache


class TestPerInstanceLRUCache(unittest.TestCase):

    @per_instance_lru_cache()
    def cached_meth(self, x, y):
        return 3 * x + y

    @per_instance_lru_cache()
    def cached_prop(self):
        return 3

    def test_lru(self):
        class C:

            def orig(self, x, y):
                return 3 * x + y

        instance = C()

        f = per_instance_lru_cache(maxsize=20)(C.orig)
        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertEqual(maxsize, 20)
        self.assertEqual(currsize, 0)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 0)

        domain = range(5)
        for i in range(1000):
            x, y = choice(domain), choice(domain)
            actual = f(instance, x, y)
            expected = instance.orig(x, y)
            self.assertEqual(actual, expected)

        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertTrue(hits > misses)
        self.assertEqual(hits + misses, 1000)
        self.assertEqual(currsize, 20)

        f.cache_clear(instance)   # test clearing
        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 0)
        self.assertEqual(currsize, 0)
        f(instance, x, y)
        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

        # Test bypassing the cache
        self.assertIs(f.__wrapped__, C.orig)
        f.__wrapped__(instance, x, y)
        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

    def test_lru_no_cache(self):
        class C:

            @per_instance_lru_cache(0)
            def f(self):
                nonlocal f_cnt
                f_cnt += 1
                return 20

        instance = C()

        self.assertEqual(C.f.cache_info(instance).maxsize, 0)
        f_cnt = 0
        for i in range(5):
            self.assertEqual(instance.f(), 20)
        self.assertEqual(f_cnt, 5)
        hits, misses, maxsize, currsize = C.f.cache_info(instance)
        self.assertEqual(hits, 0)
        self.assertEqual(misses, 5)
        self.assertEqual(currsize, 0)

    def test_lru_maxsize_one(self):
        class C:

            @property
            @per_instance_lru_cache(1)
            def f(self):
                nonlocal f_cnt
                f_cnt += 1
                return 20

        instance = C()

        self.assertEqual(C.f.fget.cache_info(instance).maxsize, 1)
        f_cnt = 0
        for i in range(5):
            self.assertEqual(instance.f, 20)
        self.assertEqual(f_cnt, 1)
        hits, misses, maxsize, currsize = C.f.fget.cache_info(instance)
        self.assertEqual(hits, 4)
        self.assertEqual(misses, 1)
        self.assertEqual(currsize, 1)

    def test_lru_maxsize_two(self):
        class C:

            @per_instance_lru_cache(2)
            def f(self, x):
                nonlocal f_cnt
                f_cnt += 1
                return x*10

        instance = C()

        self.assertEqual(C.f.cache_info(instance).maxsize, 2)
        f_cnt = 0
        for x in 7, 9, 7, 9, 7, 9, 8, 8, 8, 9, 9, 9, 8, 8, 8, 7:
            #    *  *              *                          *
            self.assertEqual(instance.f(x), x*10)
        self.assertEqual(f_cnt, 4)
        hits, misses, maxsize, currsize = C.f.cache_info(instance)
        self.assertEqual(hits, 12)
        self.assertEqual(misses, 4)
        self.assertEqual(currsize, 2)

    def test_lru_reentrancy_with_len(self):
        # Test to make sure the LRU cache code isn't thrown-off by
        # caching the built-in len() function.  Since len() can be
        # cached, we shouldn't use it inside the lru code itself.
        old_len = builtins.len
        try:
            builtins.len = per_instance_lru_cache(4)(len)
            for i in [0, 0, 1, 2, 3, 3, 4, 5, 6, 1, 7, 2, 1]:
                self.assertEqual(len('abcdefghijklmn'[:i]), i)
        finally:
            builtins.len = old_len

    def test_lru_type_error(self):
        # Regression test for issue #28653.
        # lru_cache was leaking when one of the arguments
        # wasn't cacheable.

        class C:

            @per_instance_lru_cache(maxsize=None)
            def infinite_cache(self, o):
                pass

            @per_instance_lru_cache(maxsize=10)
            def limited_cache(self, o):
                pass

        instance = C()

        with self.assertRaises(TypeError):
            instance.infinite_cache([])

        with self.assertRaises(TypeError):
            instance.limited_cache([])

    def test_lru_with_maxsize_none(self):
        class C:

            @per_instance_lru_cache(maxsize=None)
            def fib(self, n):
                if n < 2:
                    return n
                return self.fib(n-1) + self.fib(n-2)

        instance = C()

        self.assertEqual([instance.fib(n) for n in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610])
        self.assertEqual(C.fib.cache_info(instance),
            functools._CacheInfo(hits=28, misses=16, maxsize=None, currsize=16))
        C.fib.cache_clear(instance)
        self.assertEqual(C.fib.cache_info(instance),
            functools._CacheInfo(hits=0, misses=0, maxsize=None, currsize=0))

    def test_lru_with_maxsize_negative(self):
        class C:

            @per_instance_lru_cache(maxsize=-10)
            def eq(self, n):
                return n

        instance = C()

        for _ in (0, 1):
            self.assertEqual([instance.eq(n) for n in range(150)], list(range(150)))
        self.assertEqual(C.eq.cache_info(instance),
            functools._CacheInfo(hits=0, misses=300, maxsize=-10, currsize=1))

    def test_lru_with_exceptions(self):
        # Verify that user_function exceptions get passed through without
        # creating a hard-to-read chained exception.
        # http://bugs.python.org/issue13177
        for maxsize in (None, 128):

            class C:

                @per_instance_lru_cache(maxsize)
                def func(self, i):
                    return 'abc'[i]

            instance = C()

            self.assertEqual(instance.func(0), 'a')
            with self.assertRaises(IndexError) as cm:
                instance.func(15)
            self.assertIsNone(cm.exception.__context__)
            # Verify that the previous exception did not result in a cached entry
            with self.assertRaises(IndexError):
                instance.func(15)

    def test_lru_with_types(self):
        for maxsize in (None, 128):

            class C:

                @per_instance_lru_cache(maxsize=maxsize, typed=True)
                def square(self, x):
                    return x * x

            instance = C()

            self.assertEqual(instance.square(3), 9)
            self.assertEqual(type(instance.square(3)), type(9))
            self.assertEqual(instance.square(3.0), 9.0)
            self.assertEqual(type(instance.square(3.0)), type(9.0))
            self.assertEqual(instance.square(x=3), 9)
            self.assertEqual(type(instance.square(x=3)), type(9))
            self.assertEqual(instance.square(x=3.0), 9.0)
            self.assertEqual(type(instance.square(x=3.0)), type(9.0))
            self.assertEqual(C.square.cache_info(instance).hits, 4)
            self.assertEqual(C.square.cache_info(instance).misses, 4)

    def test_lru_with_keyword_args(self):
        class C:

            @per_instance_lru_cache()
            def fib(self, n):
                if n < 2:
                    return n
                return self.fib(n=n-1) + self.fib(n=n-2)

        instance = C()

        self.assertEqual(
            [instance.fib(n=number) for number in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]
        )
        self.assertEqual(C.fib.cache_info(instance),
            functools._CacheInfo(hits=28, misses=16, maxsize=128, currsize=16))
        C.fib.cache_clear(instance)
        self.assertEqual(C.fib.cache_info(instance),
            functools._CacheInfo(hits=0, misses=0, maxsize=128, currsize=0))

    def test_lru_with_keyword_args_maxsize_none(self):
        class C:

            @per_instance_lru_cache(maxsize=None)
            def fib(self, n):
                if n < 2:
                    return n
                return self.fib(n=n-1) + self.fib(n=n-2)

        instance = C()

        self.assertEqual([instance.fib(n=number) for number in range(16)],
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610])
        self.assertEqual(instance.fib.cache_info(instance),
            functools._CacheInfo(hits=28, misses=16, maxsize=None, currsize=16))
        instance.fib.cache_clear(instance)
        self.assertEqual(instance.fib.cache_info(instance),
            functools._CacheInfo(hits=0, misses=0, maxsize=None, currsize=0))

    @unittest.skipIf(sys.version_info[:2] < (3, 6), 'This test requires Python 3.6+.')
    def test_kwargs_order(self):
        # PEP 468: Preserving Keyword Argument Order
        class C:

            @per_instance_lru_cache(maxsize=10)
            def f(self, **kwargs):
                return list(kwargs.items())

        instance = C()

        self.assertEqual(instance.f(a=1, b=2), [('a', 1), ('b', 2)])
        self.assertEqual(instance.f(b=2, a=1), [('b', 2), ('a', 1)])
        self.assertEqual(C.f.cache_info(instance),
            functools._CacheInfo(hits=0, misses=2, maxsize=10, currsize=2))

    def test_lru_cache_decoration(self):
        class C:

            def f(self, zomg: 'zomg_annotation'):
                """f doc string"""
                return 42

        g = per_instance_lru_cache()(C.f)
        for attr in functools.WRAPPER_ASSIGNMENTS:
            self.assertEqual(getattr(g, attr), getattr(C.f, attr))

    @unittest.skipUnless(threading, 'This test requires threading.')
    def test_lru_cache_threaded(self):
        n, m = 5, 11

        class C:

            def orig(self, x, y):
                return 3 * x + y

        instance = C()

        f = per_instance_lru_cache(maxsize=n*m)(C.orig)
        hits, misses, maxsize, currsize = f.cache_info(instance)
        self.assertEqual(currsize, 0)

        start = threading.Event()
        def full(k):
            start.wait(10)
            for _ in range(m):
                self.assertEqual(f(instance, k, 0), instance.orig(k, 0))

        def clear():
            start.wait(10)
            for _ in range(2*m):
                f.cache_clear(instance)

        orig_si = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            # create n threads in order to fill cache
            threads = [threading.Thread(target=full, args=[k]) for k in range(n)]
            with support.start_threads(threads):
                start.set()

            hits, misses, maxsize, currsize = f.cache_info(instance)

            # XXX: Why can be not equal?
            self.assertLessEqual(misses, n)
            self.assertLessEqual(hits, m*n - misses)
            self.assertEqual(currsize, n)

            # create n threads in order to fill cache and 1 to clear it
            threads = [threading.Thread(target=clear)]
            threads += [threading.Thread(target=full, args=[k]) for k in range(n)]
            start.clear()
            with support.start_threads(threads):
                start.set()
        finally:
            sys.setswitchinterval(orig_si)

    @unittest.skipUnless(threading, 'This test requires threading.')
    def test_lru_cache_threaded2(self):
        # Simultaneous call with the same arguments
        n, m = 5, 7
        start = threading.Barrier(n+1)
        pause = threading.Barrier(n+1)
        stop = threading.Barrier(n+1)

        class C:

            @per_instance_lru_cache(maxsize=m*n)
            def f(self, x):
                pause.wait(10)
                return 3 * x

        instance = C()

        self.assertEqual(C.f.cache_info(instance), (0, 0, m*n, 0))

        def test():
            for i in range(m):
                start.wait(10)
                self.assertEqual(C.f(instance, i), 3 * i)
                stop.wait(10)

        threads = [threading.Thread(target=test) for k in range(n)]
        with support.start_threads(threads):
            for i in range(m):
                start.wait(10)
                stop.reset()
                pause.wait(10)
                start.reset()
                stop.wait(10)
                pause.reset()
                self.assertEqual(C.f.cache_info(instance), (0, (i+1)*n, m*n, i+1))

    @unittest.skipUnless(threading, 'This test requires threading.')
    def test_lru_cache_threaded3(self):
        class C:

            @per_instance_lru_cache(maxsize=2)
            def f(self, x):
                time.sleep(.01)
                return 3 * x

        instance = C()

        def test(i, x):
            with self.subTest(thread=i):
                self.assertEqual(instance.f(x), 3 * x, i)
        threads = [threading.Thread(target=test, args=(i, v))
                   for i, v in enumerate([1, 2, 2, 3, 2])]
        with support.start_threads(threads):
            pass

    def test_rlock_not_needed(self):
        # There's a test for functools.lru_cache() that demonstrates its
        # need to use an RLock instead of a Lock. In a similar vein,
        # this test intends to show that @per_instance_lru_cache does
        # *not* require an RLock. The purpose of this is to ensure the
        # implementation isn't changed in a way that might cause
        # reentrancy issues.
        class C:

            def __init__(self, x):
                self.x = x

            def __hash__(self):
                return self.x

            def __eq__(self, other):
                # print('C.__eq__({self}, {other})'.format_map(locals()))
                if self.x == 2:
                    self.method(self.__class__(1))
                return self.x == other.x

            def __repr__(self):
                return 'C(id={id}, x={self.x})'.format(id=id(self), self=self)

            @per_instance_lru_cache(maxsize=10)
            def method(self, c):
                if c.x > 1:
                    # print('Recur with c.x - 1 =', c.x - 1)
                    c.method(C(c.x - 1))
                return c

        instance = C(0)
        instance.method(C(1))
        instance.method(C(2))
        instance.method(C(3))
        self.assertEqual(instance.method(C(2)), C(2))

    def test_early_detection_of_bad_call(self):
        # Issue #22184
        with self.assertRaises(TypeError):
            class C:

                @per_instance_lru_cache
                def m(self):
                    pass

    def test_lru_method(self):
        class C(int):

            f_cnt = 0

            @per_instance_lru_cache(2)
            def f(self, x):
                self.f_cnt += 1
                return x*10+self

        a = C(5)
        b = C(5)
        c = C(7)

        self.assertEqual(C.f.cache_info(a), (0, 0, 2, 0))

        for x in 1, 2, 2, 3, 1, 1, 1, 2, 3, 3:
            self.assertEqual(a.f(x), x*10 + 5)

        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 0, 0))
        self.assertEqual(C.f.cache_info(a), (4, 6, 2, 2))

        for x in 1, 2, 1, 1, 1, 1, 3, 2, 2, 2:
            self.assertEqual(b.f(x), x*10 + 5)

        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 4, 0))
        self.assertEqual(C.f.cache_info(b), (6, 4, 2, 2))

        for x in 2, 1, 1, 1, 1, 2, 1, 3, 2, 1:
            self.assertEqual(c.f(x), x*10 + 7)

        self.assertEqual((a.f_cnt, b.f_cnt, c.f_cnt), (6, 4, 5))
        self.assertEqual(C.f.cache_info(c), (5, 5, 2, 2))

        self.assertEqual(a.f.cache_info(a), C.f.cache_info(a))
        self.assertEqual(b.f.cache_info(b), C.f.cache_info(b))
        self.assertEqual(c.f.cache_info(c), C.f.cache_info(c))

    def test_pickle(self):
        cls = self.__class__
        for f in cls.cached_meth, cls.cached_prop:
            for proto in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(proto=proto, func=f):
                    f_copy = pickle.loads(pickle.dumps(f, proto))
                    self.assertIs(f_copy, f)

    def test_copy(self):
        cls = self.__class__

        class C:

            def orig(self, x, y):
                return 3 * x + y

        part = functools.partial(C.orig, 2)
        funcs = cls.cached_meth, cls.cached_prop, per_instance_lru_cache(2)(part)

        for f in funcs:
            with self.subTest(func=f):
                f_copy = copy.copy(f)
                self.assertIs(f_copy, f)

    def test_deepcopy(self):
        cls = self.__class__

        class C:

            def orig(self, x, y):
                return 3 * x + y

        part = functools.partial(C.orig, 2)
        funcs = cls.cached_meth, cls.cached_prop, per_instance_lru_cache(2)(part)

        for f in funcs:
            with self.subTest(func=f):
                f_copy = copy.deepcopy(f)
                self.assertIs(f_copy, f)


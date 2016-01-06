#!/usr/bin/env python

import argparse
import cStringIO
import os
import sys

from os.path import exists, join, basename, dirname, realpath
from subprocess import Popen, call, PIPE

# add parent directory to search path (for import tests)
here = dirname(__file__)
root = realpath(join(here, os.pardir))
sys.path.append(root)

COLOR_RED = 31

VERBOSE_MODE = False
DEBUG_MODE = False

def _do_print(message, *args, **kwargs):
    if 'prefix' in kwargs:
        message = "%s: %s" % (kwargs['prefix'], message)
    ann = kwargs.get('ann', '++')
    color = kwargs.get('color', None)
    m = message % args if args else message
    if color is not None:
        sys.stderr.write('\033[%sm' % (color,))
    for line in m.strip().splitlines():
        sys.stderr.write("%s %s\n" % (ann, line))
    if color is not None:
        sys.stderr.write('\033[0m')

def verbose(message, *args, **kwargs):
    if VERBOSE_MODE:
        kwargs['ann'] = '++'
        _do_print(message, *args, **kwargs)

def debug(message, *args, **kwargs):
    if DEBUG_MODE:
        kwargs['ann'] = '**'
        _do_print(message, *args, **kwargs)

def dict_to_str(d):
    return '\n'.join([("%s=%r" % (k,v)) for k,v in d.iteritems()]) + '\n'

def _do_test(test, env, expect_retcode=0):
    prog = test.split()
    if prog[0].endswith('.py'):
        prog = ['python'] + prog
    verbose("running test %s", ' '.join(prog))
    test_proc = Popen(prog, env=env, stdout=PIPE, stderr=PIPE)
    stdout, stderr = test_proc.communicate()
    debug("stdout: '''%s'''", stdout.strip(), prefix=test)
    debug("stderr: '''%s'''", stderr.strip(), prefix=test)
    retcode = test_proc.returncode
    if retcode == expect_retcode:
        verbose("%s passed", test)
    else:
        verbose("%s failed with status %d", test, retcode, color=COLOR_RED)
        verbose("stdout: %s", stdout, prefix=test, color=COLOR_RED)
        verbose("stderr: %s", stderr, prefix=test, color=COLOR_RED)
    return retcode == expect_retcode

def _do_tests(tests, **env):
    env.update(os.environ)
    if VERBOSE_MODE:
        env['VERBOSE_MODE'] = '1'
    if DEBUG_MODE:
        env['DEBUG_MODE'] = '1'
    env['TEST_ROOT'] = here
    env['ROOT'] = root
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = env['PYTHONPATH'] + ":" + root
    else:
        env['PYTHONPATH'] = root
    failures = []
    for test in tests:
        print(test)
        assert exists(test)
        expect_retcode = 1 if test.startswith('testx_') else 0
        if not _do_test(test, env, expect_retcode=expect_retcode):
            failures.append(test)
    return failures

def _parse_tests(tests):
    results = []
    for test in tests:
        test_search = join(here, basename(test))
        if exists(test):
            results.append(test)
        elif exists(test_search):
            results.append(test_search)
        elif exists(test_search + ".sh"):
            results.append(test_search + ".sh")
        elif exists(test_search + ".py"):
            results.append(test_search + ".py")
        else:
            raise ValueError("Unable to find test %s" % (test,))
    return results

def _is_test(path):
    return basename(path).split('_')[0] in set(['test', 'testx'])

if __name__ == "__main__":
    p = argparse.ArgumentParser(usage="%(prog)s [options] [tests]")
    p.add_argument("tests", type=str, nargs="*", default=None,
                   help="tests to run")
    p.add_argument("-w", "--world", type=str, metavar="WORLD", default="",
                   help="world to use")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="be verbose about running tests")
    p.add_argument("-d", "--debug", action="store_true",
                   help="be even more verbose")
    args = p.parse_args()

    VERBOSE_MODE = args.verbose
    DEBUG_MODE = args.debug

    tests_to_run = []
    if args.tests:
        tests_to_run = _parse_tests(args.tests)
    else:
        tests_to_run = [join(here, p) for p in os.listdir(here) \
                        if _is_test(p)]

    if len(tests_to_run) == 0:
        print("no tests to run, exiting")
        raise SystemExit(0)

    verbose("running %d test%s %s", len(tests_to_run),
            "s" if len(tests_to_run) != 1 else "", ' '.join(tests_to_run))

    failed_cases = _do_tests(tests_to_run, TERRARIA_WORLD=args.world)

    if failed_cases:
        print("%s*** failed tests: %s%s" % ('\033[1;31m',
                                            ' '.join(failed_cases),
                                            '\033[0m'))
        raise SystemExit(1)
    else:
        verbose("all tests passed")
else:
    # running as an API for a single test case
    VERBOSE_MODE = 'VERBOSE_MODE' in os.environ
    DEBUG_MODE = 'DEBUG_MODE' in os.environ
    debug("running as a harness for test %s", sys.argv[0])


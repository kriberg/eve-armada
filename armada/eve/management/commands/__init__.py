import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def ok(msg='done'):
    return "%s%s%s" % (bcolors.OKGREEN, msg, bcolors.ENDC)

def fail(msg='fail'):
    return "%s%s%s" % (bcolors.FAIL, msg, bcolors.ENDC)

def start_task(name):
    output = '%s..' % name
    output = output.ljust(70)[:70]
    sys.stdout.write(output)

def end_task():
    sys.stdout.write('[%s]\n' % ok())

def fail_task(message):
    sys.stdout.write('[%s]\n%s' % (fail(), message))


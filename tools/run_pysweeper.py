# Run khubik2's pysweeper unmodified, minus the Tk window: stub `app`, log to stdout.
# Needs a clone of https://github.com/khubik2/pysweeper in ./pysweeper, plus pycryptodome + pyserial.
# Usage: python3 run_pysweeper.py /dev/ttyACM1   (ESP running tools/Bridge)
import sys, time, datetime, types
port = sys.argv[1]
src = open('pysweeper/pysweeper.py').read().replace("if __name__ == '__main__':", "if False:")
ns = {'__name__': 'pysweeper'}
exec(compile(src, 'pysweeper.py', 'exec'), ns)

class Var:
    def __init__(self, v): self.v = v
    def get(self): return self.v
class Text:
    def __setitem__(self, k, v): pass
    def insert(self, pos, s):
        for line in s.rstrip('\n').split('\n'):
            print(datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3], line, flush=True)
    def see(self, *a): pass
ns['app'] = types.SimpleNamespace(rb=Var(0), cbsel=Var(port), keyWarn=Var(True),
                                  rdbg=Var(False), text1=Text(), entry1=Var(''))
ns['startsv']()
while True: time.sleep(1)

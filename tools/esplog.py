# Timestamped ESP serial logger; reconnects if the port drops. Doesn't toggle DTR/RTS (no reset).
# Usage: python3 esplog.py <port, e.g. /dev/serial/by-id/usb-Espressif_...> <logfile>
import serial, time, datetime, sys
PORT=sys.argv[1]
out=open(sys.argv[2],'a',buffering=1)
def ts(): return datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
while True:
    try:
        s=serial.Serial(); s.port=PORT; s.baudrate=115200; s.dtr=False; s.rts=False; s.timeout=0.5; s.open()
        out.write(f'{ts()} ## port open\n'); buf=b''
        while True:
            buf+=s.read(512)
            while b'\n' in buf:
                line,buf=buf.split(b'\n',1)
                out.write(f'{ts()} {line.decode(errors="replace").rstrip()}\n')
    except Exception as e:
        out.write(f'{ts()} ## port lost: {e}\n'); time.sleep(0.5)

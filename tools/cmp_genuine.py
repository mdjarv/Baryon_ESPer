# Compare pysweeper's 0x80/0x81 math with answers captured from a genuine PSP-1000 battery.
# Needs a clone of https://github.com/khubik2/pysweeper in ./pysweeper, plus pycryptodome.
import re
src=open('pysweeper/pysweeper.py').read(); g={}
for n in ['keystore','challenge1_secret','challenge2_secret']:
    exec(re.search(r'^'+n+r' = \{.*?\}',src,re.S|re.M).group(0),g)
for fn in ['MixChallenge1','MixChallenge2','MatrixSwap']:
    exec(re.search(r'^def '+fn+r'\(.*?(?=^\S)',src,re.S|re.M).group(0),g)
exec('newmap='+re.search(r'newmap = (\[.*?\])',src,re.S).group(1),g)
from Crypto.Cipher import AES
def E(v,d): return AES.new(bytes.fromhex(g['keystore'][v]),AES.MODE_ECB).encrypt(bytes(d))
H=lambda b: bytes(b).hex().upper()
samples=[ # (0x80 req incl version, genuine 0x80 reply, PSP 0x81 data, genuine 0x81 reply)
 ('00E1BCF9274831B390','92509309BA806FB2BE97DA6B4634FA94','0129832D8BEFE2BA','5BB11883B940A1EF'),
 ('00BED3E335975F084D','3900087B53E7620E470D9535E4E66C8B','B9F85F16C931BE74','4A915D59B23688DF')]
for req,g80,p81,g81 in samples:
    v=int(req[:2],16); r=bytes.fromhex(req[2:])
    a=E(v,g['MatrixSwap'](g['MixChallenge1'](v,r))); b=g['MatrixSwap'](E(v,a))
    ours80=bytes(a[:8])+bytes(b[:8])
    c2=E(v,g['MatrixSwap'](g['MixChallenge2'](v,bytes(b[:8])))); ours81=E(v,c2)
    print('0x80 genuine',g80,'\n     ours   ',H(ours80),' match:',H(ours80)==g80)
    print('0x81 genuine',g81,'(8 bytes)\n     ours   ',H(ours81),'(16 bytes)')

print('\n--- search 0x81 formula ---')
from Crypto.Cipher import AES as _A
def D(v,d): return _A.new(bytes.fromhex(g['keystore'][v]),_A.MODE_ECB).decrypt(bytes(d))
MS=lambda x: bytes(g['MatrixSwap'](list(x)))
for req,g80,p81,g81 in samples:
    v=0; nb=bytes.fromhex(g80[16:]); pn=bytes.fromhex(p81); r=bytes.fromhex(req[2:]); tgt=bytes.fromhex(g81)
    ins={'nonceB':nb,'psp81':pn,'psp80':r,'nonceB^psp81':bytes(x^y for x,y in zip(nb,pn))}
    hits=[]
    for iname,x in ins.items():
        for mix in ('MixChallenge1','MixChallenge2'):
            d=g[mix](v,x)
            for pre in ('raw','ms'):
                blk=bytes(d) if pre=='raw' else MS(d)
                c=E(v,blk); c2=E(v,c)
                for oname,o in {'c':c,'MS(c)':MS(c),'c2':c2,'MS(c2)':MS(c2),'D(blk)':D(v,blk)}.items():
                    for half in (0,8):
                        if o[half:half+8]==tgt: hits.append(f'{iname} {mix} {pre} {oname}[{half}:{half+8}]')
    print(g81, hits or 'no hit')

print('\n--- is PSP 0x81 data derived from battery nonce? ---')
for req,g80,p81,g81 in samples:
    v=0; nb=bytes.fromhex(g80[16:]); r=bytes.fromhex(req[2:]); a=bytes.fromhex(g80[:16])
    cands={}
    for nm,x in {'nonceB':nb,'a8':bytes.fromhex(g80[:16]),'psp80':r}.items():
        for mix in ('MixChallenge1','MixChallenge2'):
            d=g[mix](v,x)
            for pre,blk in (('raw',bytes(d)),('ms',MS(d))):
                c=E(v,blk); c2=E(v,c)
                for on,o in (('c',c),('MS(c)',MS(c)),('c2',c2),('MS(c2)',MS(c2))):
                    for h in (0,8): cands[f'{nm} {mix} {pre} {on}[{h}]']=o[h:h+8]
    tp=bytes.fromhex(p81); tg=bytes.fromhex(g81)
    print('psp81 hits:',[k for k,x in cands.items() if x==tp])
    print('g81 hits:',[k for k,x in cands.items() if x==tg])

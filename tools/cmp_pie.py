# Verify the corrected (piesweeper) 0x81 formula for key 0x00 against genuine-battery captures.
# Needs pycryptodome.
from Crypto.Cipher import AES
K=bytes.fromhex('5c52d91cf382aca489d88178ec16297b'); S2=bytes.fromhex('f4e04313ad2eb4db')
nm=[0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15]
MS=lambda x: bytes(x[nm[i]] for i in range(16))
E=lambda d: AES.new(K,AES.MODE_ECB).encrypt(bytes(d))
def mix2(c):
    t=[0]*16
    for i,p in enumerate([0,4,8,12,1,5,9,13]): t[p]=c[i]
    for i,p in enumerate([2,6,10,14,3,7,11,15]): t[p]=S2[i]
    return t
for nonce,g81 in [('BE97DA6B4634FA94','5BB11883B940A1EF'),('470D9535E4E66C8B','4A915D59B23688DF')]:
    r2=E(E(MS(mix2(bytes.fromhex(nonce)))))
    print(nonce,'->',r2[:8].hex().upper(),'genuine',g81,'MATCH' if r2[:8].hex().upper()==g81 else 'no')

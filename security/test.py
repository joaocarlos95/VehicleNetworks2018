#Fazer import
# $ sudo pip3 install pycrypto

import Crypto.Hash.MD5 as MD5
from Crypto.PublicKey import RSA


######################################################
# client
######################################################

# read key file
with open('moto.key') as f: key_text = f.read()
key = RSA.importKey(key_text)
f.close()

#texto a para fazer a assinatura
plaintext = 'The rain in Spain falls mainly on the Plain'
plaintext=plaintext.encode('utf-8');

hash = MD5.new(plaintext).digest()
#print(repr(hash))

#sign the hash
signature = key.sign(hash, '')
print(len(signature), RSA.__name__)





######################################################
# server
######################################################

# read key file
with open('moto.key') as f1: key_text2 = f1.read()
key2 = RSA.importKey(key_text2)
f1.close()

pubkey = key2.publickey()

# You send message (plaintext) and signature to Friend.
# Friend knows how to compute hash.
# Friend verifies the message came from you this way:
assert pubkey.verify(hash, signature)
print("ok")

# A different hash should not pass the test.
assert not pubkey.verify(hash[:-1], signature)
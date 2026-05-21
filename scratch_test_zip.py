import os
import pyzipper
import zipfile

class ZipCryptoEncrypter:
    def __init__(self, pwd):
        if isinstance(pwd, str):
            pwd = pwd.encode('utf-8')
        self.pwd = pwd
        self.key0, self.key1, self.key2 = self._init_keys(pwd)

    def _gen_crc_table(self):
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xedb88320
                else:
                    crc >>= 1
            table.append(crc)
        return table

    def _init_keys(self, pwd):
        crctable = self._gen_crc_table()
        key0 = 305419896
        key1 = 591751049
        key2 = 878082192

        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]

        for p in pwd:
            key0 = crc32(p, key0)
            key1 = (key1 + (key0 & 0xFF)) & 0xFFFFFFFF
            key1 = (key1 * 134775813 + 1) & 0xFFFFFFFF
            key2 = crc32(key1 >> 24, key2)
        return key0, key1, key2

    def update_zipinfo(self, zinfo):
        self.zinfo = zinfo
        zinfo.flag_bits |= 0x1
        dt = zinfo.date_time
        dos_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] >> 1)
        zinfo._raw_time = dos_time

    def encryption_header(self):
        self.key0, self.key1, self.key2 = self._init_keys(self.pwd)
        header_bytes = bytearray(os.urandom(11))
        
        # Determine the check byte
        dt = self.zinfo.date_time
        dos_time = (dt[3] << 11) | (dt[4] << 5) | (dt[5] >> 1)
        
        if self.zinfo.flag_bits & 0x8:
            check_byte = (dos_time >> 8) & 0xff
        else:
            check_byte = (self.zinfo.CRC >> 24) & 0xff
            
        header_bytes.append(check_byte)
        
        # Encrypt the header
        encrypted_header = bytearray()
        crctable = self._gen_crc_table()
        
        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]
            
        for b in header_bytes:
            k = self.key2 | 2
            keystream = ((k * (k ^ 1)) >> 8) & 0xFF
            c = b ^ keystream
            encrypted_header.append(c)
            
            # update keys with plaintext byte
            self.key0 = crc32(b, self.key0)
            self.key1 = (self.key1 + (self.key0 & 0xFF)) & 0xFFFFFFFF
            self.key1 = (self.key1 * 134775813 + 1) & 0xFFFFFFFF
            self.key2 = crc32(self.key1 >> 24, self.key2)
            
        return bytes(encrypted_header)

    def encrypt(self, data):
        encrypted_data = bytearray()
        crctable = self._gen_crc_table()
        
        def crc32(ch, crc):
            return (crc >> 8) ^ crctable[(crc ^ ch) & 0xFF]
            
        for b in data:
            k = self.key2 | 2
            keystream = ((k * (k ^ 1)) >> 8) & 0xFF
            c = b ^ keystream
            encrypted_data.append(c)
            
            # update keys with plaintext byte
            self.key0 = crc32(b, self.key0)
            self.key1 = (self.key1 + (self.key0 & 0xFF)) & 0xFFFFFFFF
            self.key1 = (self.key1 * 134775813 + 1) & 0xFFFFFFFF
            self.key2 = crc32(self.key1 >> 24, self.key2)
            
        return bytes(encrypted_data)

    def flush(self):
        return b''

    def finalize_zipinfo(self, zinfo):
        pass

class LegacyZipFile(pyzipper.ZipFile):
    def get_encrypter(self):
        if self.pwd is not None:
            return ZipCryptoEncrypter(self.pwd)
        return None

def test():
    password = b"12345678"
    zip_filename = "test_encrypted.zip"
    
    # Write a file using our LegacyZipFile
    with LegacyZipFile(zip_filename, 'w', compression=pyzipper.ZIP_DEFLATED) as zf:
        zf.setpassword(password)
        zf.writestr("hello.txt", b"Hello, this is a test of legacy ZipCrypto password protection!")
        
    print("[+] Zip file created using LegacyZipFile.")
    
    # Verify we can decrypt it using standard library zipfile.ZipFile
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zf:
            zf.setpassword(password)
            data = zf.read("hello.txt")
            print("[+] Successfully read and decrypted data:", data)
            if data == b"Hello, this is a test of legacy ZipCrypto password protection!":
                print("[+] SUCCESS! The decrypted data matches exactly.")
            else:
                print("[-] FAIL: Data mismatch.")
    except Exception as e:
        print("[-] Verification failed with error:", e)
        
    # Clean up
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

if __name__ == "__main__":
    test()

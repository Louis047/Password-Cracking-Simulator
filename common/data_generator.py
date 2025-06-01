import hashlib
import random
import string

def generate_sample_passwords(count=100):
    """Generate sample passwords for testing"""
    common_passwords = [
        "password123", "admin", "123456", "qwerty", "letmein", 
        "welcome", "password", "12345", "abc123", "test",
        "user", "guest", "login", "pass", "secret"
    ]
    
    passwords = common_passwords.copy()
    
    # Generate additional random passwords
    for _ in range(count - len(common_passwords)):
        length = random.randint(6, 12)
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        passwords.append(password)
    
    return passwords

def generate_hashes(passwords, algorithm='sha256'):
    """Generate hashes for given passwords"""
    hashes = []
    for password in passwords:
        if algorithm == 'sha256':
            hash_obj = hashlib.sha256(password.encode())
        elif algorithm == 'md5':
            hash_obj = hashlib.md5(password.encode())
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        hashes.append(hash_obj.hexdigest())
    
    return hashes

def create_sample_data_files():
    """Create sample data files for testing"""
    passwords = generate_sample_passwords(50)
    target_passwords = passwords[:5]  # First 5 will have corresponding hashes
    hashes = generate_hashes(target_passwords)
    
    # Write password file
    with open('data/password.txt', 'w') as f:
        for password in passwords:
            f.write(f"{password}\n")
    
    # Write hash file
    with open('data/hashes.txt', 'w') as f:
        for hash_val in hashes:
            f.write(f"{hash_val}\n")
    
    print(f"Generated {len(passwords)} passwords and {len(hashes)} target hashes")
    print("Target passwords (for verification):")
    for i, pwd in enumerate(target_passwords):
        print(f"  {pwd} -> {hashes[i]}")

if __name__ == "__main__":
    create_sample_data_files()
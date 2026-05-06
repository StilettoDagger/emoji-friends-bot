def get_unicode_hex(char):
    hex_code = "-".join(hex(ord(c))[2:] for c in char)
    return hex_code, hex_code.replace("-fe0f", "")

print(get_unicode_hex("🧘🏾‍♂️"))

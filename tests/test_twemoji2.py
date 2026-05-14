import requests

char = "🧘🏾‍♂️"
hex_full = "-".join(hex(ord(c))[2:] for c in char)
hex_stripped = hex_full.replace("-fe0f", "")

urls = [
    f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_full}.png",
    f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_stripped}.png"
]

for url in urls:
    r = requests.head(url)
    print(f"{url} -> {r.status_code}")

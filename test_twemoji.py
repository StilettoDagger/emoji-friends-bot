import requests
for h in ["263a", "263a-fe0f", "2764", "2764-fe0f"]:
    r = requests.head(f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{h}.png")
    print(f"{h} -> {r.status_code}")

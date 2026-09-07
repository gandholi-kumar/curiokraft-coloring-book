import base64
import json
import os
import urllib.request

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# Use the multimodal image generation endpoint
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent"

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Generate an image: cute teddy bear image only thick outline 2d image and no shading or grey scaling, just black and white"
                }
            ]
        }
    ]
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))

        # Extract the base64 image data from the response parts
        parts = res_data["candidates"][0]["content"]["parts"]
        image_saved = False

        for part in parts:
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                with open("teddy_bear_outline.png", "wb") as f:
                    f.write(img_bytes)
                print("Image successfully saved as teddy_bear_outline.png")
                image_saved = True
                break

        if not image_saved:
            print("No image data returned in response.")

except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}:")
    print(e.read().decode("utf-8"))
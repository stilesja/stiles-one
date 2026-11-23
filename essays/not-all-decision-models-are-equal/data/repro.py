"""Does a second question in a System One request change the first question's answer?

Sends the same "which department?" choice question about the same customer messages in three request shapes:
  alone      - the department question by itself
  +english   - plus an unrelated yes/no question ("Is the text written in English?")
  +person    - plus a related yes/no question ("Does the customer ask to speak to a person?")
and records the department question's probabilities each time. If questions are evaluated independently, the three
shapes give the same department answer.

Usage:
  python3 -I repro.py jev  [--send]   # TypeSafe Jev; key from TYPESAFE_API_KEY
  python3 -I repro.py d1   [--send]   # Microsoft-Decision-1.1 on Azure; token from `az login`;
                                      # needs D1_ENDPOINT (https://<resource>.services.ai.azure.com/) and D1_DEPLOYMENT
Without --send it prints the request count and sends nothing. Results go to results-<target>.json.
Credentials are read from the environment / az CLI and never printed or written.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

MESSAGES = [
    "where's my package",
    "I was charged twice",
    "my router keeps dropping the connection",
    "I want my money back",
    "cancel it",
    "it's broken",
    "wrong size",
    "change the delivery address",
    "the thing I ordered",
    "help",
]

DEPARTMENT = {
    "type": "choice",
    "instructions": "Which department is the customer asking for?",
    "criteria": {
        "billing": "charges, refunds, invoices or payment methods",
        "orders": "placing, changing or cancelling an order",
        "shipping": "where a package is, delivery dates, tracking or the delivery address",
        "returns": "sending an item back or exchanging it",
        "tech_support": "a product that isn't working or won't connect",
        "none": "none of these fits, or it is unclear what the customer wants",
    },
}
ENGLISH = {"type": "choice", "instructions": "Is the text written in English?",
           "criteria": {"yes": "the text is in English", "no": "the text is not in English"}}
PERSON = {"type": "choice", "instructions": "Does the customer ask to speak to a person?",
          "criteria": {"yes": "the customer asks for a person, an agent or a representative",
                       "no": "the customer doesn't ask for a person"}}

SHAPES = {
    "alone": {"department": DEPARTMENT},
    "+english": {"department": DEPARTMENT, "english": ENGLISH},
    "+person": {"department": DEPARTMENT, "person": PERSON},
}


def target(name):
    if name == "jev":
        def auth():
            key = os.environ.get("TYPESAFE_API_KEY", "")
            if not key:
                sys.exit("set TYPESAFE_API_KEY")
            return "Bearer " + key
        return "https://api.typesafe.ai/v1/systemone", "jev-1.14.0", auth
    if name == "d1":
        endpoint = os.environ.get("D1_ENDPOINT", "").rstrip("/")
        deployment = os.environ.get("D1_DEPLOYMENT", "")
        if not endpoint or not deployment:
            sys.exit("set D1_ENDPOINT and D1_DEPLOYMENT")
        cache = {}

        def auth():
            if "t" not in cache or time.time() > cache["exp"]:
                out = subprocess.run(["az", "account", "get-access-token", "--resource", "https://cognitiveservices.azure.com",
                                      "--query", "accessToken", "-o", "tsv"], capture_output=True, text=True)
                if out.returncode != 0:
                    sys.exit("az account get-access-token failed (run az login)")
                cache["t"], cache["exp"] = out.stdout.strip(), time.time() + 45 * 60
            return "Bearer " + cache["t"]
        return endpoint + "/providers/microsoft/v1/systemone", deployment, auth
    sys.exit("target is jev or d1")


def post(url, auth, body):
    for attempt in range(20):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": auth()})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15)
                continue
            raise SystemExit(f"HTTP {e.code}: {e.read()[:300]!r}")
    raise SystemExit("still rate limited after 20 tries")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    send = "--send" in sys.argv
    url, model, auth = target(name)
    n = len(MESSAGES) * len(SHAPES)
    print(f"{name}: {n} requests to {url.split('/')[2]} model={model}")
    if not send:
        print("nothing sent; add --send")
        return
    rows = []
    for shape, questions in SHAPES.items():
        for text in MESSAGES:
            body = {"model": model, "state": text, "questions": questions}
            resp = post(url, auth, body)
            dep = resp["answers"]["department"]
            rows.append({"shape": shape, "text": text, "model_answered": resp.get("model"),
                         "choice": dep.get("choice"), "confidence": dep.get("confidence"),
                         "probabilities": dep.get("probabilities"),
                         "others": {k: v.get("probabilities") for k, v in resp["answers"].items() if k != "department"},
                         "request": body})
    with open(f"results-{name}.json", "w") as f:
        json.dump(rows, f, indent=1)
    print(f"wrote results-{name}.json ({len(rows)} rows)")


if __name__ == "__main__":
    main()

"""Follow-up to repro.py: what about a multi-question request moves the department answer?

repro.py showed that adding a second question changes the department answer, and that the change is bit-identical
whichever second question (English or person) is added. These shapes separate the remaining explanations:
  alone, +english   repro.py's shapes again, to check the earlier numbers still hold and to capture request ids
  n3, n5            2 and 4 extra yes/no questions: one fixed switch (n2 = n3 = n5) or a growing effect?
  english-first     the same pair as +english with the keys in the other order
  dept-twice        the department question twice under two ids: are both answers the same?
  +noul, +score     a second question of another type (skipped, with the error kept, if the model rejects the type)
Each row keeps the department probabilities, the other answers and the response's request-id headers.

Usage: python3 -I isolate.py [--send]     # Microsoft-Decision-1.1; needs D1_ENDPOINT and D1_DEPLOYMENT, token from az login
Without --send it prints the request count and sends nothing. Results go to isolate-d1.json.
Credentials are read from the az CLI and never printed or written.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repro import DEPARTMENT, ENGLISH, MESSAGES, PERSON  # noqa: E402


def yes_no(question, yes, no):
    return {"type": "choice", "instructions": question, "criteria": {"yes": yes, "no": no}}


POLITE = yes_no("Is the customer being polite?", "the customer is polite", "the customer is not polite")
QUESTION = yes_no("Is the message phrased as a question?", "the message is a question", "the message is not a question")
ENGLISH_NOUL = {"type": "noul", "instructions": "Is the text written in English?"}
URGENCY = {"type": "score", "instructions": "How urgent is the customer's request?",
           "criteria": ["not urgent", "somewhat urgent", "very urgent"]}

SHAPES = {
    "alone": {"department": DEPARTMENT},
    "+english": {"department": DEPARTMENT, "english": ENGLISH},
    "n3": {"department": DEPARTMENT, "english": ENGLISH, "person": PERSON},
    "n5": {"department": DEPARTMENT, "english": ENGLISH, "person": PERSON, "polite": POLITE, "question": QUESTION},
    "english-first": {"english": ENGLISH, "department": DEPARTMENT},
    "dept-twice": {"department": DEPARTMENT, "department_2": DEPARTMENT},
    "+noul": {"department": DEPARTMENT, "english": ENGLISH_NOUL},
    "+score": {"department": DEPARTMENT, "urgency": URGENCY},
}
PROBES = ("+noul", "+score")  # one request each first; skip the shape if the model rejects it


def target():
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


def ids(headers):
    return {k.lower(): v for k, v in headers.items() if "request-id" in k.lower() or k.lower().startswith("x-ms-")}


def post(url, auth, body):
    """(status, json or error text, request-id headers); retries on 429."""
    for _ in range(30):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": auth()})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.load(r), ids(r.headers)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15)
                continue
            return e.code, e.read()[:500].decode(errors="replace"), ids(e.headers)
    raise SystemExit("still rate limited after 30 tries")


def main():
    send = "--send" in sys.argv
    url, model, auth = target()
    n = len(MESSAGES) * len(SHAPES)
    print(f"d1: up to {n} requests to {url.split('/')[2]} model={model}")
    if not send:
        print("nothing sent; add --send")
        return
    rows, rejected = [], {}
    for shape in PROBES:
        status, resp, hdr = post(url, auth, {"model": model, "state": MESSAGES[0], "questions": SHAPES[shape]})
        if status != 200:
            rejected[shape] = {"status": status, "error": resp, "headers": hdr}
            print(f"{shape}: HTTP {status}, skipped")
    for shape, questions in SHAPES.items():
        if shape in rejected:
            continue
        for text in MESSAGES:
            body = {"model": model, "state": text, "questions": questions}
            status, resp, hdr = post(url, auth, body)
            if status != 200:
                rows.append({"shape": shape, "text": text, "status": status, "error": resp, "headers": hdr})
                continue
            answers = resp["answers"]
            rows.append({"shape": shape, "text": text, "status": 200, "model_answered": resp.get("model"),
                         "headers": hdr,
                         "probabilities": answers["department"].get("probabilities"),
                         "others": {k: v for k, v in answers.items() if k != "department"},
                         "request": body})
        print(f"{shape}: done")
    with open("isolate-d1.json", "w") as f:
        json.dump({"rows": rows, "rejected": rejected}, f, indent=1)
    print(f"wrote isolate-d1.json ({len(rows)} rows, {len(rejected)} shapes rejected)")


if __name__ == "__main__":
    main()

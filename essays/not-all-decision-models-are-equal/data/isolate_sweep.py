"""Follow-up to isolate_length.py: where does Decision-1.1's answer change as a request grows?

isolate_length.py showed the department answer depends on the request's input length (one exact set of probabilities
at 158 input tokens or fewer, another at 159 or more), not on how many questions it has. This sends the department
question with one neutral yes/no question whose description is padded with k filler words, so only the length changes,
and records the input tokens and the department probabilities for each k. The second question's content doesn't move
the department answer (isolate.py: +english, +person, +noul and +score give identical answers at similar lengths).

Usage: python3 -I isolate_sweep.py grid FROM TO STEP [--send]   # k = FROM, FROM+STEP, ... TO
       python3 -I isolate_sweep.py bisect MAX [--send]          # narrow each change between neighbouring k to 1 word
Appends one line per request to isolate-sweep-d1.jsonl and skips k values already there. Same environment as isolate.py.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isolate import post, target, yes_no  # noqa: E402
from repro import DEPARTMENT  # noqa: E402

TEXT = "cancel it"
OUT = "isolate-sweep-d1.jsonl"


def questions(k):
    pad = " ".join(["note"] * k)
    return {"department": DEPARTMENT,
            "english": yes_no("Is the text written in English?", ("the text is in English " + pad).strip(),
                              "the text is not in English")}


def load():
    done = {}
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            done[r["k"]] = r
    return done


def ask(url, model, auth, k):
    status, resp, hdr = post(url, auth, {"model": model, "state": TEXT, "questions": questions(k)})
    if status != 200:
        raise SystemExit(f"k={k}: HTTP {status} {resp[:200]}")
    r = {"k": k, "input_tokens": resp["usage"]["input_tokens"], "probabilities": resp["answers"]["department"]["probabilities"],
         "headers": hdr}
    with open(OUT, "a") as f:
        f.write(json.dumps(r) + "\n")
    return r


def changes(done):
    ks = sorted(done)
    return [(a, b) for a, b in zip(ks, ks[1:]) if done[a]["probabilities"] != done[b]["probabilities"]]


def main():
    args = [a for a in sys.argv[1:] if a != "--send"]
    send = "--send" in sys.argv
    url, model, auth = target()
    done = load()
    if args[0] == "grid":
        k0, k1, step = map(int, args[1:4])
        todo = [k for k in range(k0, k1 + 1, step) if k not in done]
        print(f"grid: {len(todo)} requests")
        if not send:
            return
        for k in todo:
            done[k] = ask(url, model, auth, k)
    elif args[0] == "bisect":
        budget = int(args[1])
        if not send:
            print(f"bisect: up to {budget} requests; open gaps {[(a, b) for a, b in changes(done) if b - a > 1]}")
            return
        while budget > 0:
            gaps = [(a, b) for a, b in changes(done) if b - a > 1]
            if not gaps:
                break
            a, b = gaps[0]
            m = (a + b) // 2
            done[m] = ask(url, model, auth, m)
            budget -= 1
    for a, b in changes(done):
        pa, pb = done[a], done[b]
        print(f"change between k={a} ({pa['input_tokens']} tokens, orders {pa['probabilities']['orders']:.3f})"
              f" and k={b} ({pb['input_tokens']} tokens, orders {pb['probabilities']['orders']:.3f})")
    print(f"{len(done)} points, {len(changes(done))} changes")


if __name__ == "__main__":
    main()

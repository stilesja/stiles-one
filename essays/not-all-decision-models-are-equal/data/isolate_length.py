"""Follow-up to isolate.py: is it the request's size, not its question count, that moves the department answer?

isolate.py found three distinct sets of department probabilities, and they line up with the size of the questions
object rather than the number of questions: alone (499 chars); +english, english-first, +noul, +score (579-664);
n3, dept-twice, n5 (889-1229). dept-twice has only two questions but matches n3 and n5. Two shapes split size from count:
  +english-long  two questions, the second padded to about the size of dept-twice
  n3-terse       three questions, the extra two kept tiny so the total stays about the size of +english
If size decides, +english-long matches n3 and n3-terse matches +english. Also records the response's usage
(token counts) for every isolate.py shape on one message. Writes isolate-length-d1.json.

Usage: python3 -I isolate_length.py [--send]   # same environment as isolate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isolate import SHAPES, post, target, yes_no  # noqa: E402
from repro import DEPARTMENT, MESSAGES  # noqa: E402

LONG_ENGLISH = yes_no(
    "Is the text written in English?",
    "the text is written in the English language, whether it is formal or informal, complete sentences or a short "
    "fragment, with or without spelling mistakes, abbreviations, slang or missing punctuation, and whatever it is about",
    "the text is written in a language other than English, such as Spanish, French, German, Chinese, Vietnamese, "
    "Tagalog or any other language, or it mixes languages so that English is not the main language of the text")
TINY_A = yes_no("English?", "yes", "no")
TINY_B = yes_no("Polite?", "yes", "no")

NEW = {
    "+english-long": {"department": DEPARTMENT, "english": LONG_ENGLISH},
    "n3-terse": {"department": DEPARTMENT, "english": TINY_A, "polite": TINY_B},
}


def main():
    send = "--send" in sys.argv
    url, model, auth = target()
    for s, q in NEW.items():
        print(f"{s}: questions JSON chars {len(json.dumps(q))}")
    n = len(MESSAGES) * len(NEW) + len(SHAPES)
    print(f"d1: {n} requests")
    if not send:
        print("nothing sent; add --send")
        return
    rows = []
    for shape, questions in list(NEW.items()):
        for text in MESSAGES:
            status, resp, hdr = post(url, auth, {"model": model, "state": text, "questions": questions})
            rows.append(row(shape, text, questions, status, resp, hdr))
        print(f"{shape}: done")
    text = "cancel it"
    for shape, questions in SHAPES.items():
        status, resp, hdr = post(url, auth, {"model": model, "state": text, "questions": questions})
        rows.append(row(shape, text, questions, status, resp, hdr))
    print("usage sample: done")
    with open("isolate-length-d1.json", "w") as f:
        json.dump(rows, f, indent=1)
    print(f"wrote isolate-length-d1.json ({len(rows)} rows)")


def row(shape, text, questions, status, resp, hdr):
    if status != 200:
        return {"shape": shape, "text": text, "status": status, "error": resp, "headers": hdr}
    return {"shape": shape, "text": text, "status": 200, "model_answered": resp.get("model"), "usage": resp.get("usage"),
            "headers": hdr, "probabilities": resp["answers"]["department"].get("probabilities"),
            "others": {k: v for k, v in resp["answers"].items() if k != "department"},
            "questions_chars": len(json.dumps(questions)), "request": {"state": text, "questions": questions}}


if __name__ == "__main__":
    main()

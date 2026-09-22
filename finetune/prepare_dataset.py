"""
Build a fine-tuning dataset from the interactions the app logs.

Every model call made by the backend is appended to data/finetune/interactions.jsonl
as a chat transcript (system, user, assistant). This script filters and de-duplicates
them and writes train/validation splits in the chat format expected by
train_qlora.py.

Review before training. The whole point of fine-tuning is to teach the model the
outputs you *want*, so open data/finetune/review.jsonl, fix or delete weak
responses (set "keep": false), then run with --use-review.

    python finetune/prepare_dataset.py                 # writes review.jsonl
    python finetune/prepare_dataset.py --use-review    # writes train.jsonl / val.jsonl
"""
import argparse
import hashlib
import json
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA = os.path.join(ROOT, "data", "finetune")
LOG = os.path.join(DATA, "interactions.jsonl")
REVIEW = os.path.join(DATA, "review.jsonl")

TASKS = {"generate_questions", "evaluate_theory", "evaluate_coding", "final_assessment", "ats_review"}


def load(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def usable(record):
    msgs = record.get("messages", [])
    if len(msgs) != 3 or record.get("task") not in TASKS:
        return False
    try:
        out = json.loads(msgs[-1]["content"])
    except (json.JSONDecodeError, KeyError):
        return False
    # Drop empty templates the model sometimes produced before retries.
    if record["task"].startswith("evaluate"):
        return len(str(out.get("detailed_feedback", ""))) >= 20
    if record["task"] == "final_assessment":
        text = str(out.get("overall_assessment", ""))
        return len(text) >= 40 and "sentences" not in text.lower()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--use-review", action="store_true", help="build splits from the reviewed file")
    ap.add_argument("--val", type=float, default=0.1, help="validation fraction")
    args = ap.parse_args()

    if not args.use_review:
        if not os.path.exists(LOG):
            raise SystemExit(f"No interactions logged yet at {LOG}. Run some interviews first.")
        seen, rows = set(), []
        for r in load(LOG):
            if not usable(r):
                continue
            key = hashlib.sha1(r["messages"][1]["content"].encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            rows.append({"keep": True, "task": r["task"], "messages": r["messages"]})
        with open(REVIEW, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        by_task = {}
        for r in rows:
            by_task[r["task"]] = by_task.get(r["task"], 0) + 1
        print(f"Wrote {len(rows)} examples to {REVIEW}: {by_task}")
        print("Edit the assistant messages you want to improve, set keep=false on bad ones, "
              "then run again with --use-review.")
        return

    rows = [r for r in load(REVIEW) if r.get("keep", True)]
    random.seed(7)
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * args.val)) if len(rows) > 10 else 0
    splits = {"val.jsonl": rows[:n_val], "train.jsonl": rows[n_val:]}
    for name, items in splits.items():
        with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
            for r in items:
                f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")
        print(f"{name}: {len(items)} examples")
    if len(rows) < 200:
        print("Tip: a few hundred reviewed examples per task gives noticeably better results than a few dozen.")


if __name__ == "__main__":
    main()

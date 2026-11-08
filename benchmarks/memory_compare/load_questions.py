"""Freeze previously labeled questions without generating new judgments."""

import hashlib
import json
from pathlib import Path

from atrium.session.redact_sensitive_text import redact_sensitive_text


def load_questions(evaluations: Path, directory: Path) -> list[dict]:
    """Keep target identities separate from the corpus selection step."""
    questions = []
    hashes = {}
    for split, name in (("acceptance", "acceptance-2026-10-11"), ("holdout", "holdout-2026-10-15")):
        body = (evaluations / name / "labeled.jsonl").read_bytes()
        hashes[split] = hashlib.sha256(body).hexdigest()
        for line in body.decode().splitlines():
            row = json.loads(line)
            if redact_sensitive_text(row["question"]) != row["question"]:
                raise ValueError("question text requires redaction; do not export this dataset")
            questions.append(
                {
                    key: row[key]
                    for key in (
                        "id",
                        "question",
                        "answer_conversation_id",
                        "also_answers",
                        "strata",
                    )
                }
                | {"split": split}
            )
    (directory / "questions.json").write_text(json.dumps(questions, ensure_ascii=False))
    (directory / "question_hashes.json").write_text(json.dumps(hashes, indent=2))
    return questions

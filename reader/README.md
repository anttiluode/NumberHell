# Soar reader

Does a small-window language model find facts in a huge pile of repos better by **flying**, starting from the list of repo names and diving into a README, then a file, then a passage, than by **flat retrieval** that fills the same budget with the best keyword-matching README chunks?

Both arms get the same character budget per question (default 40,000). The soar arm pays for its map: the list of all repo names counts against its budget.

## Run (Windows, local Ollama)

```
cd E:\DocsHouse\NumberHell\reader
ollama list                                   (pick a model you have, e.g. qwen3:8b)
python soar_reader.py make  --corpus E:\DocsHouse --model qwen3:8b --n 20
python soar_reader.py run   --corpus E:\DocsHouse --model qwen3:8b
python soar_reader.py score
```

- `make` writes `questions.json`. Each question is written by the model from one random README passage that contains a number, without naming the repo; the repo, file and line are the answer key. Open the file and delete questions that don't make sense before running.
- `run` answers every question with both arms and writes `results.json`. The soar arm takes up to 10 model calls per question, so 20 questions with an 8B model takes roughly 15–40 minutes.
- `score` prints: right repo, right answer, both, characters read, steps.
- `--backend stub` runs everything with a fake model to check the plumbing.

## What would count

- Soar is worth something if it gets **both right** more often than flat, or as often with far fewer characters read.
- Flat keyword retrieval is a strong baseline here, because each question was written from a passage and shares words with it. A loss for soar is a real result, not a failure of the test.
- Check `results.json` → `soar.path` to see where it flew. Notes are kept apart from sources, and answers must cite a source (this morning's lure result, turned into a rule).

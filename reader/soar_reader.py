"""Soar reader: does a small-window LLM find facts better by flying (sky -> ground) than by plain retrieval?

Runs on a local folder of repos (e.g. E:\\DocsHouse) with a local model through Ollama.

  python soar_reader.py make   --corpus E:\\DocsHouse --model qwen3:8b --n 30
  python soar_reader.py run    --corpus E:\\DocsHouse --model qwen3:8b
  python soar_reader.py score

make  : the model writes N questions, each from one random passage of one README. The passage's
        repo, file and line are kept as the answer key. Questions must not name the repo.
run   : two arms answer every question with the SAME character budget:
        flat - keyword retrieval fills the budget with the best-matching README chunks, one answer.
        soar - the model flies: sky (repo list) -> README -> folder -> file -> passage, one view
               per step, notes kept apart from sources, answer with a source.
score : correct repo, correct answer, characters read, steps.

No packages needed beyond the Python standard library. --backend stub runs the plumbing without a model.
"""
import argparse, json, random, re, sys, time, urllib.request
from pathlib import Path

TEXT_EXT = {".md", ".txt", ".py", ".js", ".html", ".json", ".csv", ".yml", ".yaml", ".toml", ".ts", ".c", ".cpp", ".rs"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".github"}

# ---------------------------------------------------------------- corpus
class Corpus:
    def __init__(self, root):
        self.root = Path(root)
        self.repos = sorted([p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")], key=lambda p: p.name.lower())
        self._readme = {}
    def readme_path(self, repo):
        d = self.root / repo
        for name in ("README.md", "readme.md", "Readme.md", "README.txt", "README"):
            if (d / name).exists(): return d / name
        return None
    def readme(self, repo):
        if repo not in self._readme:
            p = self.readme_path(repo)
            self._readme[repo] = p.read_text(encoding="utf-8", errors="ignore") if p else ""
        return self._readme[repo]
    def one_liner(self, repo):
        for line in self.readme(repo).splitlines():
            t = line.strip().lstrip("#").strip()
            if len(t) > 3 and not t.startswith(("!", "[!", "<", "|", "```")): return t[:110]
        return "(no README)"
    def sky(self, filt=None):
        """No filter: every repo name (the whole map, coarse). With a filter: names + first lines that match."""
        if not filt: return ", ".join(r.name for r in self.repos)
        f = filt.lower(); hits = [f"{r.name} — {self.one_liner(r.name)}" for r in self.repos if f in r.name.lower() or f in self.one_liner(r.name).lower()]
        return "\n".join(hits) or f"(no repo name or first line contains '{filt}')"
    def listing(self, repo, limit=80):
        d = self.root / repo; out = []
        for p in sorted(d.rglob("*")):
            if any(s in p.parts for s in SKIP_DIRS) or not p.is_file(): continue
            out.append(f"{p.relative_to(d).as_posix()}  ({p.stat().st_size} B)")
            if len(out) >= limit: out.append("..."); break
        return "\n".join(out)
    def read(self, repo, rel, start=1, end=None, maxchars=4000):
        p = (self.root / repo / rel).resolve()
        if not str(p).startswith(str((self.root / repo).resolve())) or not p.is_file(): return None
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = max(1, int(start or 1)); end = min(len(lines), int(end or len(lines)))
        out, n = [], 0
        for i in range(start, end + 1):
            s = f"{i:5d}| {lines[i-1]}"
            if n + len(s) > maxchars: out.append(f"... (cut at line {i-1} of {len(lines)})"); break
            out.append(s); n += len(s) + 1
        return "\n".join(out)

# ---------------------------------------------------------------- model
class Ollama:
    def __init__(self, model, ctx, url="http://localhost:11434"):
        self.model, self.ctx, self.url = model, ctx, url
    def __call__(self, system, user):
        body = {"model": self.model, "stream": False, "format": "json", "think": False,
                "options": {"temperature": 0, "num_ctx": self.ctx},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read())["message"]["content"]

class Stub:
    """Fake model for testing the plumbing: answers with valid but dumb JSON."""
    def __init__(self, corpus): self.c, self.rng = corpus, random.Random(0)
    def __call__(self, system, user):
        if "QUESTION WRITER" in system:
            m = re.search(r"PASSAGE:\n(.*)", user, re.S); line = m.group(1).splitlines()[0] if m else "x"
            return json.dumps({"question": "What does this passage say: " + line[:60] + "?", "answer": line.split()[-1] if line.split() else "x"})
        if "FLAT READER" in system:
            m = re.findall(r"=== (\S+) /", user); return json.dumps({"answer": "?", "source": (m[0] + "/README.md:1") if m else "?"})
        if "step 1 of" in user: return json.dumps({"action": "open", "repo": self.c.repos[0].name})
        if self.rng.random() < 0.4: return json.dumps({"action": "answer", "answer": "?", "source": self.c.repos[0].name + "/README.md:1"})
        return json.dumps({"action": "note", "text": "looked around"})

def parse_json(s):
    s = re.sub(r"<think>.*?</think>", "", s, flags=re.S)
    m = re.search(r"\{.*\}", s, re.S)
    try: return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError: return {}

# ---------------------------------------------------------------- questions
QSYS = """You are a QUESTION WRITER. From the passage, write ONE question whose answer is a short specific fact
(a number, a name, a setting, a result) stated in the passage. The question must make sense to someone who has
NOT seen the passage and must NOT mention the repository name. Reply JSON: {"question": "...", "answer": "..."}"""

def passages(text, k=6):
    lines = text.splitlines(); good = []
    for i in range(len(lines)):
        chunk = "\n".join(lines[i:i + k])
        if re.search(r"\d", chunk) and len(chunk) > 120 and not lines[i].strip().startswith(("```", "!", "<")): good.append((i + 1, chunk))
    return good

def make(args, corpus, llm):
    rng = random.Random(args.seed); qs = []; tries = 0
    repos = [r.name for r in corpus.repos if len(passages(corpus.readme(r.name))) > 0]
    while len(qs) < args.n and tries < args.n * 5:
        tries += 1; repo = rng.choice(repos); line, chunk = rng.choice(passages(corpus.readme(repo)))
        j = parse_json(llm(QSYS, "PASSAGE:\n" + chunk))
        q, a = str(j.get("question", "")).strip(), str(j.get("answer", "")).strip()
        if not q or not a or repo.lower() in q.lower(): continue
        rel = corpus.readme_path(repo).relative_to(corpus.root / repo).as_posix()
        qs.append({"id": len(qs), "question": q, "answer": a, "repo": repo, "file": rel, "line": line})
        print(f"[{len(qs)}/{args.n}] {repo}: {q}  ->  {a}")
    Path(args.questions).write_text(json.dumps(qs, indent=1, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------- flat arm: keyword retrieval, one shot
FSYS = """You are a FLAT READER. Answer the question from the text below only. Give the exact source as repo/file:line.
If the text does not contain the answer, say so. Reply JSON: {"answer": "...", "source": "repo/file:line"}"""

def words(s): return {w for w in re.findall(r"[a-z0-9]{3,}", s.lower())}

def flat(q, corpus, llm, budget):
    qw = words(q["question"]); chunks = []
    for r in corpus.repos:
        lines = corpus.readme(r.name).splitlines()
        for i in range(0, len(lines), 20):
            body = "\n".join(f"{i+k+1:5d}| {l}" for k, l in enumerate(lines[i:i + 20]))
            sc = len(qw & words(body)) + 0.5 * len(qw & words(r.name))
            if sc: chunks.append((sc, r.name, body))
    chunks.sort(key=lambda c: -c[0]); text, used = [], 0
    for sc, repo, body in chunks:
        piece = f"=== {repo} / README.md\n{body}\n"
        if used + len(piece) > budget: continue
        text.append(piece); used += len(piece)
    j = parse_json(llm(FSYS, f"QUESTION: {q['question']}\n\nTEXT:\n" + "".join(text)))
    return {"answer": j.get("answer", ""), "source": j.get("source", ""), "chars": used, "steps": 1}

# ---------------------------------------------------------------- soar arm
SSYS = """You are a reader with a small window exploring a world of repositories much bigger than you.
Altitudes: SKY (all repos, one line each) -> HIGH (one README) -> MID (one repo's file list) -> LOW/GROUND (lines of one file).
Rules:
1. Dive only toward something that stands out for the question. If the view is flat, climb.
2. Your notes are NOT sources. Never answer from a note; answer only from text you read in a view.
3. Answer with the exact source repo/file:line you read it at. If you run out of steps, answer your best guess.
Reply with ONE JSON action:
 {"action":"sky"}                                  see all repo names again
 {"action":"sky","filter":"WORD"}                   repos whose name or first README line contains WORD, with that line
 {"action":"open","repo":"NAME"}                    read its README (first part)
 {"action":"list","repo":"NAME"}                    list its files
 {"action":"read","repo":"NAME","file":"PATH","start":N,"end":M}   read lines
 {"action":"note","text":"..."}                     keep a short note (not a source)
 {"action":"answer","answer":"...","source":"repo/file:line"}"""

def soar(q, corpus, llm, budget, steps):
    view = "SKY (all repo names):\n" + corpus.sky()
    used = len(view); notes, path = [], []
    for t in range(1, steps + 1):
        user = (f"QUESTION: {q['question']}\nstep {t} of {steps}. Characters read so far: {used} of {budget}.\n"
                f"YOUR NOTES (not sources): {notes or 'none'}\nPATH SO FAR: {' > '.join(path) or 'start'}\n"
                + ("LAST STEP: reply with an answer action now.\n" if t == steps else "") + f"\nVIEW:\n{view}")
        j = parse_json(llm(SSYS, user)); a = j.get("action")
        win = max(500, min(budget // steps, budget - used))
        if a == "answer": return {"answer": j.get("answer", ""), "source": j.get("source", ""), "chars": used, "steps": t, "path": path}
        repo = str(j.get("repo", ""))
        if a == "sky": f = j.get("filter"); view = (f"SKY filter '{f}':\n" if f else "SKY:\n") + corpus.sky(f)[:win]; path.append(f"sky {f or ''}".strip())
        elif a == "open" and (corpus.root / repo).is_dir():
            rp = corpus.readme_path(repo); rel = rp.relative_to(corpus.root / repo).as_posix() if rp else None
            view = f"HIGH {repo}/{rel}:\n" + (corpus.read(repo, rel, 1, None, win) if rel else "(no README)"); path.append(f"open {repo}")
        elif a == "list" and (corpus.root / repo).is_dir(): view = f"MID {repo}:\n" + corpus.listing(repo)[:win]; path.append(f"list {repo}")
        elif a == "read" and (corpus.root / repo).is_dir():
            got = corpus.read(repo, str(j.get("file", "")), j.get("start", 1), j.get("end"), win)
            view = f"GROUND {repo}/{j.get('file')}:\n{got}" if got else "(no such file)"; path.append(f"read {repo}/{j.get('file')}:{j.get('start',1)}")
        elif a == "note": notes.append(str(j.get("text", ""))[:200]); notes = notes[-6:]; path.append("note"); continue
        else: view = "(invalid action; reply with one JSON action)"; path.append("invalid"); continue
        used += len(view)
        if used >= budget: view += "\n(BUDGET SPENT: answer now)"
    return {"answer": "", "source": "", "chars": used, "steps": steps, "path": path}

# ---------------------------------------------------------------- scoring
def norm(s): return re.sub(r"\s+", " ", str(s).lower()).strip()
def nums(s): return set(re.findall(r"-?\d+(?:\.\d+)?", str(s)))
def answer_ok(pred, key):
    p, k = norm(pred), norm(key)
    if not p: return False
    if nums(k): return nums(k) <= nums(p)
    return k in p or (len(p) > 2 and p in k)
def repo_ok(src, repo): return norm(src).replace("\\", "/").split("/")[0].strip() == repo.lower()

def run(args, corpus, llm):
    qs = json.loads(Path(args.questions).read_text(encoding="utf-8")); out = []
    for q in qs:
        row = {"id": q["id"]}
        for arm in args.arms:
            t0 = time.time()
            r = flat(q, corpus, llm, args.budget) if arm == "flat" else soar(q, corpus, llm, args.budget, args.steps)
            r.update(seconds=round(time.time() - t0, 1), repo_ok=repo_ok(r["source"], q["repo"]), answer_ok=answer_ok(r["answer"], q["answer"]))
            row[arm] = r
            print(f"q{q['id']:>3} {arm:4s} repo {'Y' if r['repo_ok'] else '.'} answer {'Y' if r['answer_ok'] else '.'}  chars {r['chars']:>6}  steps {r['steps']}")
        out.append(row)
        Path(args.results).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    score(args)

def score(args):
    rows = json.loads(Path(args.results).read_text(encoding="utf-8")); arms = [a for a in ("flat", "soar") if a in rows[0]]
    print(f"\n{len(rows)} questions")
    for a in arms:
        R = [r[a] for r in rows]; n = len(R)
        print(f"{a:5s} right repo {sum(x['repo_ok'] for x in R)}/{n}   right answer {sum(x['answer_ok'] for x in R)}/{n}   "
              f"both {sum(x['repo_ok'] and x['answer_ok'] for x in R)}/{n}   mean chars {sum(x['chars'] for x in R)/n:.0f}   mean steps {sum(x['steps'] for x in R)/n:.1f}")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["make", "run", "score"])
    ap.add_argument("--corpus", default="."); ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--backend", choices=["ollama", "stub"], default="ollama")
    ap.add_argument("--ctx", type=int, default=16384, help="model context in tokens")
    ap.add_argument("--n", type=int, default=30); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=40000, help="characters each arm may read per question")
    ap.add_argument("--steps", type=int, default=10); ap.add_argument("--arms", nargs="+", default=["flat", "soar"])
    ap.add_argument("--questions", default="questions.json"); ap.add_argument("--results", default="results.json")
    args = ap.parse_args()
    if args.cmd == "score": return score(args)
    corpus = Corpus(args.corpus)
    if not corpus.repos: sys.exit(f"no repo folders under {args.corpus}")
    llm = Stub(corpus) if args.backend == "stub" else Ollama(args.model, args.ctx)
    print(f"{len(corpus.repos)} repos, sky view {len(corpus.sky())} characters")
    (make if args.cmd == "make" else run)(args, corpus, llm)

if __name__ == "__main__":
    main()

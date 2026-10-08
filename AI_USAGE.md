# AI Usage

## 1. Which AI tools did I use?

- **Claude Code** (Anthropic, Claude Opus 5.5), used inside VS Code as a coding agent that could read files, run commands and tests, and search the web.

## 2. What did I use them for?

| Task | How AI was used | What I did |
|---|---|---|
| Understanding the brief | Claude read the challenge repository, summarised the requirements and how they'd be judged, and pointed out that **no knowledge-base documents were supplied**. | Asked for the reasoning behind every choice, so I could explain it in an interview, not just submit it. |
| Finding data | I asked Claude to look for public HR/handbook datasets (Kaggle, Hugging Face, open-source handbooks on GitHub). | Decided to use **synthetic documents** instead: none of the public sets matched the brief's topics, and writing our own gave a known correct answer for every evaluation question. |
| Choosing the approach | Claude proposed TF-IDF with extractive answers and explained the alternatives (BM25, embeddings, LLMs, LangChain). | Asked for a simple web UI on top of the CLI, but only after the core requirements (sources, refusals, tests) were done properly. |
| Writing code and tests | Claude wrote the modules and tests step by step, one commit per step. | <!-- TODO: what you reviewed, ran or changed yourself --> |
| Evaluation | Claude built the labelled question set and the evaluation script. | Used the results to choose thresholds, and to decide which failures to fix and which to document. |
| Documentation | Claude drafted the README and this file. | <!-- TODO: what you edited or rewrote --> |

## 3. Examples where AI output was changed, rejected or improved

### Example 1: the "paternity leave" problem (the most important one)

**What the AI first built:** a standard approach that returns the best-matching section if its similarity score is above a threshold.

**Why I didn't accept it:** testing showed it answered *"How much paternity leave do I get?"* with the **holiday carry-over** section, at a score (0.24) as high as many correct answers. The word "leave" matched strongly; "paternity" matched nothing. This is exactly the "confident answer without a real source" the brief warns about, and no threshold value could fix it without also rejecting good answers.

**What changed:** the retriever now detects question words that never appear in the knowledge base. If at least half of the key words are unknown, the system declines and names the missing word (*"The knowledge base doesn't mention 'paternity'"*). If only some are unknown, it answers with a visible caveat. A test pins this behaviour down (`test_partial_match_on_generic_word_is_not_answered`).

### Example 2: plural-stripping replaced by a real stemmer

**What the AI suggested:** a hand-written "strip the trailing s" function, to avoid adding a stemming dependency.

**Why it wasn't good enough:** once the unknown-word check existed, weak stemming caused *false* refusals. "Can I **carry** over holiday?" was declined because the document says "**Carrying** Over Leave".

**What changed:** switched to the Snowball stemmer, a small pure-Python package. The README records why.

### Example 3: rejecting a fix that would only improve the score

**What was tempting:** "How much can I spend on dinner when travelling?" was declined at a score of 0.174, just under the threshold. Lowering the threshold would have "fixed" it in the evaluation.

**Why it was rejected:** checking the results showed its top match was the *Travel* section, not *Meals*. Lowering the threshold would have turned a safe refusal into a **wrong answer**. Adding a "dinner → meals" synonym just for this question would have improved the score without improving the system. I left it as a documented limitation.

---

## 4. My own reflection

<!--
TODO (Azmath): write this section yourself, in your own words. The reviewers
want YOUR thinking here, not AI-written text. Some prompts:

- Which of the decisions above did you push back on or question, and why?
- What did you learn (e.g. how TF-IDF / cosine similarity / stemming work)?
- Where did you NOT trust the AI and verify it yourself (e.g. running the
  evaluation, reading the code, checking a claim in the README)?
- What would you do differently next time when working with an AI tool?
-->

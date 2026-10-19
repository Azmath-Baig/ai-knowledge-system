# AI Usage

## 1. Which AI tools did I use?

- **Claude Code** (Anthropic, Claude Opus 5.5), used inside VS Code as a coding agent that could read files, run commands and tests, and search the web.

## 2. What did I use them for?

| Task | How AI was used | What I did |
|---|---|---|
| Understanding the brief | Claude read the challenge repository, summarised the requirements and how they'd be judged, and pointed out that **no knowledge-base documents were supplied**. | Asked for the reasoning behind every choice, so I could explain it in an interview, not just submit it. |
| Finding data | I asked Claude to look for public HR/handbook datasets (Kaggle, Hugging Face, open-source handbooks on GitHub). | Decided to use **synthetic documents** instead: none of the public sets matched the brief's topics, and writing our own gave a known correct answer for every evaluation question. |
| Choosing the approach | Claude proposed TF-IDF with extractive answers and explained the alternatives (BM25, embeddings, LLMs, LangChain). | Asked for a simple web UI on top of the CLI, but only after the core requirements (sources, refusals, tests) were done properly. |
| Writing code and tests | Claude wrote the modules and tests step by step, one commit per step. | Ran the CLI and web UI myself and tried my own questions, including messy, multi-part ones. Three of the problems this found were fixed, each with a test (see section 4). |
| Evaluation | Claude built the labelled question set and the evaluation script. | Used the results to choose thresholds, and to decide which failures to fix and which to document. |
| Documentation | Claude drafted the README and this file. | Asked for every decision to be written down with its reason and the alternatives rejected, so the README doubles as my interview preparation. |

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

*Drafted with Claude from this project's working session, then checked by me against what actually happened. Everything below is something I did, not a general claim.*

**Testing it myself found problems the automated tests didn't.** After the build, all tests passed and the evaluation looked good. I then used the tool the way a real employee would, with long, informal and multi-part questions, and found three issues:

1. *"what are the leave policy and like if i don't take my annual leave will i get that money as extra?"* was declined with the message *"doesn't mention 'like'"*. The word "like" was being treated as a topic. **Fix:** conversational filler words are now ignored.
2. *"if i don't take my annual leave and come to work will i get my monthly salary and leave salary both or what?"* was **answered** (low confidence) with the *Booking Leave* section, which says nothing about pay. Every word existed in the documents, just in unrelated sections. **Fix:** a weak match with no clear winner is now declined. This was the most important find, because it was a confident-looking answer to a question the documents don't cover.
3. After that fix, the "closest sections" list still showed an expenses section only because it contained the word "salary". I pointed out that this wasn't related to my question. **Fix:** closest sections must now be plausible matches.

Each fix has a test with my original question in it, and the second one was added to the evaluation set. The lesson for me is that a passing test suite only proves the cases someone thought of; real questions are messier.

**I questioned the AI's choices instead of accepting them.** When Claude said embeddings were left out, I asked *why not*. Rather than accepting the explanation, we agreed a bar in advance (more correct answers, and zero out-of-scope questions answered) and measured three models. Embeddings improved ranking but didn't meet the bar, so they were documented but not added. I'd rather explain a measured decision than an assumed one.

**I kept the scope deliberate.** I asked for a simple UI, but only on top of a core that meets every requirement (sources, refusals, tests), not a polished interface over a weak core. I also asked for the reasoning behind each choice, so I can explain the code rather than just submit it.

**What I'd do differently next time:** test it by hand much earlier. All three of my findings would have been cheaper to fix if I had tried real questions before the evaluation set was written.

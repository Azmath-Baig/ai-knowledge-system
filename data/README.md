# Knowledge-base documents

These documents are **synthetic**. The brief describes a NALITS knowledge base but does not
supply one, so these were written to cover the topics the brief lists (employee policies,
IT support, training, holidays, expenses, working arrangements and career development).

Writing them ourselves gives a known ground truth for evaluation (`eval/questions.json`)
and lets us plant realistic difficulties on purpose:

- **Vocabulary mismatch**: "WFH", "PTO" and "reimburse" never appear in the documents.
- **Near-duplicate topics**: annual leave vs public holidays vs study leave vs sickness absence.
- **Deliberate gaps**: there is no maternity / parental leave, pension or salary information,
  so the "I don't know" behaviour can be tested.

## Format

Each file is Markdown with one `# Title` and numbered `## N. Section` headings.
A section is the unit that is indexed and cited, so a citation looks like
`working_arrangements.md — Section 2: Remote Working`.

The loader ignores this file (`README.md`), so it is safe to keep documentation here.

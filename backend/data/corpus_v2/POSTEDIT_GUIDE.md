# Post-editing guide (test sets)

These files are `postedit/test_<lang>.csv`: 200 sentences per language. These references decide the paper's results, so they must be produced by fluent speakers.

For each row, fill in `post_edited_translation`:
- Start from `draft_translation` (machine output) and **correct it fully**: meaning, grammar, and natural wording a trainee would understand.
- **Don't keep machine wording just because it's acceptable.** If you would phrase it differently, rewrite it. This limits the bias toward the machine output.
- **Keep numbers, units and symbols** (230 V, 1.5 sq.mm, Ω) unchanged.
- If the English sentence itself is broken (an extraction error), write `SKIP` in `editor_notes` and leave the translation as your best attempt.

## Terminology: formal register (project decision)
Use **native/standard technical terms, not English loanwords**. The terms are in `../glossary/electrician_glossary.csv`; use the rows with `register = formal` for your language.
- **Use the glossary `term` (or one of its `variants`)** whenever the English sentence contains the glossary's English term. For example, in Hindi "three phase" is त्रिकला (not थ्री फेज, and never तीन चरण), and "earthing" is भूसंपर्कन (not अर्थिंग, and never पृथ्वी).
- **Watch for wrong-sense words in the machine drafts.** They are common:
  - चरण ("stage") for *phase*
  - पृथ्वी / मिट्टी ("planet / soil") for *earthing*
  - जीवित तार ("living wire") for *live wire*
- **Rows marked `loanword_kept`** (cable, fuse, megger, main switch, terminal block) have no established native term, so keep the loanword.
- **Entries marked `proposed`** are suggestions. If one is wrong or unnatural for your language, use the correct term and **record it in `editor_notes`**, so the glossary can be fixed.
- **Other technical words** not in the glossary follow the same principle: use the standard native technical term where one exists.

Record who edited each language and roughly how long it took, for the paper's methodology section.

Leave every row filled. The evaluation only uses a sheet when **all** rows have a post-edited translation.

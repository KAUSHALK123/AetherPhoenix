# QUESTIONS.md: Open Items & Author Decisions

This document captures items requiring final author decision or confirmation for camera-ready submission.

---

### 1. Public / Anonymous Repository URL
- **Current Status:** In accordance with the instructions, no unverified external repository URLs or placeholder text (`TODO`, `TBD`) were inserted into the LaTeX source.
- **Action Required:** If you wish to provide a public code/data availability link (e.g., GitHub, Zenodo, or an anonymous review URL) in the final camera-ready PDF, please supply the exact URL so it can be added to a footnote or section.

---

### 2. Blind Held-Out Test Set
- **Current Status:** As verified during Checkpoint 4, `heldout_blind_TEMPLATE.json` is an unpopulated schema template. The manuscript explicitly discloses in Limitation 1 and Section V.A that no blind held-out evaluation was conducted and that the 50-fault auxiliary set was used strictly as an internal diagnostic suite to identify classification and state bugs.
- **Action Required:** If an independent blind set is subsequently populated by an external evaluator, it should be evaluated strictly post-publication without re-tuning rule weights.

---

### 3. Author Affiliations & Correspondence Marking
- **Current Status:** The author block lists 5 authors (Ramani G, Akshitha V G, Kruthin Shanmuk Yadav CG, Dhanyashree G V, Kaushal K) from AMC Engineering College, Bengaluru, Karnataka, India, with five email addresses.
- **Action Required:** Confirm whether your target conference/publisher requires a specific corresponding author footnote (e.g., `\thanks{Corresponding author: ...}`) or IEEE membership identifiers.

---

### 4. Page Budget & PDF Length
- **Current Status:** Both `main.pdf` and `main_highlighted.pdf` have been compiled with Tectonic and verified to fit **strictly within 6 pages** (exactly 6 pages including all 16 references, 3 tables, 1 figure, worked examples, scenario studies, and full empirical disclosures).
- **Action Required:** No further action required unless the conference specifies a different page count (e.g., 5 pages or extra-page allowance).

# Similar Papers Analysis: Adjacent Research (2023–2026)

This document analyzes 13 research papers published between 2023 and 2026 that are closely related to the architecture, governance, execution, and self-healing mechanisms of **Phoenix Agents**. None of these papers were in the original project BibTeX.

---

### 1. Microsoft UFO: A UI-Focused Agent for Windows OS Interaction
* **Citation**: C. Zhang, L. Li, S. He, D. Zhang, Q. Zhang, et al., "UFO: A UI-Focused Agent for Windows OS Interaction," *Proc. Annual Conference of the North American Chapter of the Association for Computational Linguistics (NAACL)*, 2024.
* **Link**: [https://arxiv.org/abs/2402.07939](https://arxiv.org/abs/2402.07939)
* **What it measures**: Task completion success rate across 9 common Windows applications (Word, Photos, Outlook, File Explorer) on the WindowsBench benchmark.
* **Headline numbers**: Achieved an average task success rate of **81.5%** across standard Windows office workflows using GPT-4V.
* **How it overlaps with Phoenix**: Uses a hierarchical dual-agent framework (AppAgent + ActionAgent) to automate Windows desktop applications via visual perception and Win32 UI control controls.
* **Gap Phoenix fills**: UFO relies on continuous visual LLM inference (GPT-4V) for every UI step, incurring high token costs and latency (2–5 seconds per step). Phoenix introduces a fast deterministic hybrid planner (14.85 ms) with operation-centric permission governance (SAFE vs. AUTONOMOUS) and native document compilation (ReportLab/python-pptx).

---

### 2. OS-Copilot: Towards Generalist Computer Agents with Self-Improvement
* **Citation**: Z. Wu, H. Zhang, W. Liu, Z. Yao, et al., "OS-Copilot: Towards Generalist Computer Agents with Self-Improvement," *Advances in Neural Information Processing Systems (NeurIPS)*, 2024.
* **Link**: [https://arxiv.org/abs/2402.07456](https://arxiv.org/abs/2402.07456)
* **What it measures**: End-to-end task completion rate on the GAIA benchmark across general computer tasks (terminal, web, Excel, PPTX).
* **Headline numbers**: FRIDAY agent built on OS-Copilot scored **35.0%** overall task success on GAIA (outperforming task-specific baselines by ~10%).
* **How it overlaps with Phoenix**: Generalist OS agent interacting with multiple desktop interfaces (bash/terminal, filesystem, web, office tools) with task decomposition.
* **Gap Phoenix fills**: FRIDAY lacks formal human-in-the-loop security boundaries and monotonic permission invariance; it executes bash commands autonomously without parameter-aware risk gating. Phoenix enforces a 4-tier risk policy and contract-enforcing Supervisor validation.

---

### 3. Cradle: Empowering Foundation Agents towards General Computer Control
* **Citation**: W. Tan, Z. Sheng, K. Gao, B. Zhang, et al., "Cradle: Empowering Foundation Agents towards General Computer Control," *Proc. International Conference on Machine Learning (ICML)*, 2024.
* **Link**: [https://arxiv.org/abs/2403.03186](https://arxiv.org/abs/2403.03186)
* **What it measures**: Long-horizon computer control in complex environments (Red Dead Redemption 2, Cities: Skylines, Chrome, CapCut) using purely visual inputs and mouse/keyboard outputs.
* **Headline numbers**: Maintained continuous autonomous gameplay and software operation over 40-minute long-horizon missions.
* **How it overlaps with Phoenix**: Focuses on operating software non-invasively through standard human input interfaces (mouse and keyboard).
* **Gap Phoenix fills**: Cradle is entirely screen/vision-driven, making it brittle to UI layout jitter and slow for structured enterprise data tasks. Phoenix combines deterministic tool adapters, DAG scheduling, and native deliverable generation.

---

### 4. ScreenAgent: A Vision Language Model-Driven Computer Control Agent
* **Citation**: R. Niu, J. Shen, F. Sun, et al., "ScreenAgent: A Vision Language Model-driven Computer Control Agent," *Proc. Association for Computational Linguistics (ACL)*, 2024.
* **Link**: [https://arxiv.org/abs/2402.07945](https://arxiv.org/abs/2402.07945)
* **What it measures**: Precision of UI element localization, grounding accuracy, and multi-step plan execution across desktop environments.
* **Headline numbers**: Achieved **84.1%** UI control grounding accuracy on the ScreenAgent benchmark dataset.
* **How it overlaps with Phoenix**: Implements a Plan-Act-Reflect control loop over GUI screens for desktop automation.
* **Gap Phoenix fills**: ScreenAgent lacks fault-tolerant self-healing with bounded retry policies and deliverable generation engines. Phoenix incorporates bounded $K_{\text{max}}=3$ self-healing and structured document output verification.

---

### 5. GuardAgent: Safeguarding LLMs in Multi-Agent Autonomous Systems
* **Citation**: O. Saha, S. Basu, et al., "GuardAgent: Safeguarding LLMs in Multi-Agent Autonomous Systems," *Proc. International Conference on Machine Learning (ICML)*, 2024.
* **Link**: [https://arxiv.org/abs/2406.18844](https://arxiv.org/abs/2406.18844)
* **What it measures**: Guarding accuracy in detecting safety violations, privacy leaks, and unauthorized actions on EICU-AC (healthcare) and Mind2Web-SC (web automation).
* **Headline numbers**: Intercepted policy violations with **92.4% to 98.1%** accuracy by generating deterministic verification code.
* **How it overlaps with Phoenix**: Dedicated agent responsible for governing the actions of execution agents against defined safety policies.
* **Gap Phoenix fills**: GuardAgent generates dynamic Python code via an LLM to evaluate safety, which adds latency and potential verification hallucinations. Phoenix uses hardcoded, parameter-aware Python policy evaluators with zero LLM inference overhead and monotonic privilege verification.

---

### 6. AutoDefense: Multi-Agent Defense for Large Language Models
* **Citation**: Y. Yin, J. Shang, et al., "AutoDefense: Multi-Agent Defense for Large Language Models," *Proc. Association for Computational Linguistics (ACL)*, 2024.
* **Link**: [https://arxiv.org/abs/2403.04783](https://arxiv.org/abs/2403.04783)
* **What it measures**: Reduction in Attack Success Rate (ASR) against adversarial jailbreak prompts across GPT-3.5 and LLaMA-2.
* **Headline numbers**: Reduced ASR from **55.74% down to 7.95%** using collaborative multi-agent response filtering.
* **How it overlaps with Phoenix**: Deploys a multi-agent filter to intercept and reject dangerous actions before execution.
* **Gap Phoenix fills**: AutoDefense focuses strictly on text-generation jailbreaks; Phoenix extends governance into OS-level physical actions (destructive terminal commands, restricted URLs, hotkeys, file writes).

---

### 7. AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents
* **Citation**: C. Rawles, A. Li, D. Vincent, et al. (Google DeepMind), "AndroidWorld: A Dynamic Benchmarking Environment for Autonomous Agents," *Proc. International Conference on Learning Representations (ICLR)*, 2024.
* **Link**: [https://arxiv.org/abs/2405.14573](https://arxiv.org/abs/2405.14573)
* **What it measures**: Task completion success rate across 116 dynamically parameterized tasks across 20 real Android applications.
* **Headline numbers**: Baseline multimodal agent (M3A) achieved **30.6%** task success rate, highlighting the difficulty of multi-step GUI automation.
* **How it overlaps with Phoenix**: Programmatic system-state validation and dynamic parameterization of end-user task goals.
* **Gap Phoenix fills**: Evaluates mobile rather than desktop systems; Phoenix provides a reference desktop DAG architecture with proactive clarification and native slide/report compilation.

---

### 8. Reflexion: Language Agents with Verbal Reinforcement Learning
* **Citation**: N. Shinn, F. Cassano, E. Berman, A. Gopinath, K. Narasimhan, S. Yao, "Reflexion: Language Agents with Verbal Reinforcement Learning," *Advances in Neural Information Processing Systems (NeurIPS)*, 2023.
* **Link**: [https://arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366)
* **What it measures**: Iterative error recovery and task improvement through verbal self-critique on HumanEval (coding), ALFWorld (decision making), and HotPotQA.
* **Headline numbers**: Boosted HumanEval coding pass@1 from 80% to **91.0%** purely via episodic memory reflection without fine-tuning.
* **How it overlaps with Phoenix**: Evaluates failed execution attempts and stores feedback in episodic memory to guide subsequent recovery.
* **Gap Phoenix fills**: Reflexion re-prompts the LLM across unconstrained trial-and-error loops, ballooning API costs and token usage. Phoenix enforces bounded self-healing ($K_{\text{max}}=3$) using structured error classification, input patching, and adapter switching.

---

### 9. Language Agent Tree Search (LATS) Unifies Reasoning, Acting, and Planning
* **Citation**: A. Zhou, K. Yan, M. Shlapentokh-Rothman, et al., "Language Agent Tree Search Unifies Reasoning, Acting, and Planning," *Proc. International Conference on Machine Learning (ICML)*, 2024.
* **Link**: [https://arxiv.org/abs/2310.04406](https://arxiv.org/abs/2310.04406)
* **What it measures**: Search tree exploration and environmental feedback on HumanEval, WebShop, and HotPotQA.
* **Headline numbers**: Achieved **92.7%** pass@1 on HumanEval using GPT-4 with MCTS tree exploration and external execution feedback.
* **How it overlaps with Phoenix**: Combines environmental feedback with state-backtracking to repair execution failures.
* **Gap Phoenix fills**: LATS requires massive tree search exploration (dozens of LLM rollouts per step), rendering it impractical for low-latency desktop automation. Phoenix prioritizes sub-15 ms deterministic DAG scheduling with bounded local recovery.

---

### 10. Self-Refine: Iterative Refinement with Self-Feedback
* **Citation**: A. Madaan, N. Tandon, P. Gupta, et al., "Self-Refine: Iterative Refinement with Self-Feedback," *Advances in Neural Information Processing Systems (NeurIPS)*, 2023.
* **Link**: [https://arxiv.org/abs/2303.17651](https://arxiv.org/abs/2303.17651)
* **What it measures**: Task improvement via iterative Generate-Feedback-Refine loops across 7 NLP and code generation tasks.
* **Headline numbers**: Improved output quality by **~20%** absolute across tasks without fine-tuning or external reward models.
* **How it overlaps with Phoenix**: Iterative critique and correction loop for output generation.
* **Gap Phoenix fills**: Self-Refine relies on LLM self-critique, which is susceptible to blind-spot hallucinations. Phoenix employs an independent Supervisor Agent that validates deterministic execution contracts (exit code 0, non-empty outputs, physical artifact existence).

---

### 11. WebVoyager: Building an End-to-End Web Agent with Large Multimodal Models
* **Citation**: H. He, W. Yao, K. Ma, W. Yu, Y. Dai, et al., "WebVoyager: Building an End-to-End Web Agent with Large Multimodal Models," *Proc. Association for Computational Linguistics (ACL)*, 2024.
* **Link**: [https://arxiv.org/abs/2401.13919](https://arxiv.org/abs/2401.13919)
* **What it measures**: Task completion success rate across 643 real-world tasks on 15 live commercial websites (Amazon, Booking, GitHub).
* **Headline numbers**: Achieved **55.7%** full task success rate with GPT-4V, outperforming text-only web agents (39.2%).
* **How it overlaps with Phoenix**: Browser automation adapter navigating real web applications to fulfill user goals.
* **Gap Phoenix fills**: WebVoyager operates strictly in the browser. Phoenix bridges browser automation with OS desktop applications, terminal execution, filesystem management, and automated deliverable generation.

---

### 12. AppAgent: Multimodal Agents as Smartphone Users
* **Citation**: C. Zhang, Z. Yang, et al. (Tencent), "AppAgent: Multimodal Agents as Smartphone Users," *Proc. ACM CHI Conference on Human Factors in Computing Systems (CHI)*, 2024.
* **Link**: [https://arxiv.org/abs/2312.13771](https://arxiv.org/abs/2312.13771)
* **What it measures**: Task success rate across 50 tasks across 10 diverse third-party smartphone apps (social media, maps, editing).
* **Headline numbers**: Achieved **84.0%** success rate on everyday smartphone tasks through autonomous app exploration.
* **How it overlaps with Phoenix**: Interacts with GUI applications non-invasively through standardized human gesture/input abstractions.
* **Gap Phoenix fills**: AppAgent focuses on smartphone exploration; Phoenix targets enterprise desktop environments with multi-agent orchestration, proactive goal clarification, and fine-grained security gating.

---

### 13. Structured Uncertainty Guided Clarification for LLM Agents
* **Citation**: S. R. Babu, S. Sengupta, et al., "Structured Uncertainty guided Clarification for LLM Agents," *arXiv preprint arXiv:2604.0919*, 2026.
* **Link**: [https://arxiv.org/abs/2604.0919](https://arxiv.org/abs/2604.0919)
* **What it measures**: Ambiguity detection precision, clarifying question efficiency, and Expected Value of Perfect Information (EVPI) on the ClarifyBench benchmark.
* **Headline numbers**: Reduced unnecessary user interruptions by **43.2%** while improving final task success by **19.5%** on underspecified tool-calling queries.
* **How it overlaps with Phoenix**: Proactively detects underspecified task parameters and solicits clarification before executing tool actions.
* **Gap Phoenix fills**: Focuses strictly on conversational tool-call parameters; Phoenix integrates the Clarification Engine directly into a full desktop execution lifecycle (DAG planning, permission verification, supervisor validation, and multi-format deliverable generation).

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_patent_document(filename="d:/PROJECTS/Major/research/docx/AetherPhoenix_Patent_Application.docx"):
    doc = docx.Document()

    # Configure A4 page setup with 1-inch margins
    for section in doc.sections:
        section.page_width = Inches(8.27)  # A4 width
        section.page_height = Inches(11.69) # A4 height
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        # Configure Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("INDIAN PATENT APPLICATION — COMPLETE SPECIFICATION")
        hrun.font.name = "Times New Roman"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(128, 128, 128)

    # Base style configurations
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    def add_section_heading(title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title_text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_body_paragraph(text, indent=0.0):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(indent)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_claim_paragraph(claim_num, text):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.4)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        run_num = p.add_run(f"{claim_num}.\t")
        run_num.bold = True
        run_num.font.name = 'Times New Roman'
        run_num.font.size = Pt(12)
        
        run_body = p.add_run(text)
        run_body.font.name = 'Times New Roman'
        run_body.font.size = Pt(12)
        return p

    def add_claim_subclause(letter, text):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.7)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        run_l = p.add_run(f"{letter}.\t")
        run_l.font.name = 'Times New Roman'
        run_l.font.size = Pt(12)
        
        run_b = p.add_run(text)
        run_b.font.name = 'Times New Roman'
        run_b.font.size = Pt(12)
        return p

    # SECTION 1
    add_section_heading("SECTION 1 — TITLE OF THE INVENTION")
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(14)
    r_title = p_title.add_run("A SYSTEM AND METHOD FOR EVENT-DRIVEN MULTI-AGENT DESKTOP AND BROWSER AUTOMATION WITH HYBRID PLANNING, PERMISSION GOVERNANCE, AND BOUNDED SELF-HEALING")
    r_title.bold = True
    r_title.font.name = 'Times New Roman'
    r_title.font.size = Pt(12)

    # SECTION 2
    add_section_heading("SECTION 2 — FIELD OF THE INVENTION")
    add_body_paragraph(
        "The present invention relates generally to the technical field of automated computing system interaction, "
        "and more particularly relates to intelligent desktop and browser automation systems operative across heterogeneous "
        "operating environments. Specifically, the present invention pertains to multi-agent software frameworks and "
        "asynchronous event-driven orchestration pipelines configured for interpreting, decomposing, and executing complex, "
        "multi-step goals expressed in natural language. The invention encompasses specialized tool adapters and sub-systems "
        "for automating operating system terminal sessions, local and remote file systems, web browsers, graphical desktop user "
        "interfaces, structured document generation pipelines encompassing Portable Document Format (PDF) files and presentation "
        "slides, optical character recognition (OCR) routines, and version control systems including Git repositories. The present "
        "invention further pertains to multi-tier permission governance mechanisms, contract-based output supervision engines, "
        "and deterministic, bounded self-healing architectures for autonomous execution recovery in computerized environments."
    )
    add_body_paragraph(
        "In modern computing infrastructures, human operators frequently execute administrative, analytical, document synthesis, "
        "and integration workflows that span across multiple disconnected software boundaries, including shell terminals, web browsers, "
        "native desktop client applications, graphical windowing systems, and file management interfaces. Automated execution across "
        "such heterogeneous boundaries requires precise coordination between natural language comprehension models, deterministic "
        "operating system abstractions, strict safety verification mechanisms, and runtime fault-recovery protocols. The field of "
        "the invention therefore resides at the intersection of natural language task decomposition, directed acyclic graph (DAG) "
        "dependency orchestration, policy-based access control governance, and automated exception remediation in multi-agent "
        "computing architectures."
    )

    # SECTION 3
    add_section_heading("SECTION 3 — BACKGROUND OF THE INVENTION")
    add_body_paragraph(
        "Traditional robotic process automation (RPA) tools and procedural macro scripting solutions rely upon rigid, deterministic "
        "sequences of screen coordinates, absolute selector paths, and static command invocations. When graphical user interface "
        "layouts shift, document structures vary, dynamic web page elements load asynchronously, or underlying operating system file "
        "paths change, conventional RPA routines fail catastrophically and possess no autonomous capability to diagnose failure contexts "
        "or synthesize alternate execution paths. Concurrently, recent attempts to deploy single-agent large language model (LLM) loops "
        "for computer control combine goal interpretation, step-by-step planning, tool invocation, execution supervision, and error "
        "remediation within a singular monolithic prompting loop. This unified approach induces catastrophic state confusion over extended "
        "execution horizons, exhausts memory context windows, and fails to provide formal, schema-based verification of intermediate task outputs."
    )
    add_body_paragraph(
        "Furthermore, unconstrained autonomous agents interacting directly with host operating systems present severe security and "
        "stability hazards, as they lack deterministic permission gates and can execute destructive or irreversible operations, such as "
        "unintended file deletion, privilege escalation, and unauthorized network transmission, without explicit human oversight. Existing "
        "workflow orchestration engines, such as Apache Airflow, require directed acyclic graphs (DAGs) to be authored manually in advance "
        "by software engineers and cannot dynamically synthesize execution graphs from open-ended natural language goals at runtime. Prior "
        "to the present invention, there exists no unified computing architecture that integrates sub-15-millisecond natural language "
        "DAG generation, multi-tier risk-based permission gating, invariant contract validation, and bounded multi-strategy self-healing "
        "within a fully decoupled, event-driven orchestration pipeline."
    )

    # SECTION 4
    add_section_heading("SECTION 4 — SUMMARY OF THE INVENTION")
    add_body_paragraph(
        "It is an objective of the present invention to provide an event-driven multi-agent system and computerized method that "
        "resolves the aforementioned limitations of traditional robotic process automation and monolithic language model agents. "
        "The present invention provides an end-to-end computing framework comprising a Planner Agent, a Pipeline Orchestrator, "
        "a Permission Manager, a Worker Agent with specialized tool adapters, a Supervisor Agent, a Healing Agent, and an asynchronous "
        "Event Bus that coordinates workflow execution and streams real-time telemetry to client interfaces."
    )
    add_body_paragraph(
        "In accordance with the present invention, the system acquires an unconstrained natural language user goal and decomposes "
        "the goal into a Directed Acyclic Graph (DAG) of interdependent execution tasks at runtime. The task decomposition is executed "
        "via a hybrid planning engine comprising a deterministic rule-based decomposition path and an artificial intelligence fallback path. "
        "The deterministic rule-based path evaluates the natural language input against parameterized intent templates to synthesize "
        "fully formed execution DAGs in sub-15-millisecond latency without invoking external inference models, while the fallback path "
        "invokes a large language model governed by strict JSON schema definitions when open-ended intent patterns are encountered."
    )
    add_body_paragraph(
        "The present invention further incorporates a Permission Manager operating a four-tier risk classification matrix comprising "
        "LOW, MEDIUM, HIGH, and CRITICAL classifications. Each task node in the synthesized DAG is assigned a risk tier based on the "
        "invoked tool adapter, requested system arguments, and target resource impact. Tasks classified under HIGH or CRITICAL risk "
        "tiers are automatically intercepted and gated behind an asynchronous synchronization lock, requiring explicit user approval "
        "prior to execution, while LOW and MEDIUM tasks proceed autonomously without pipeline interruption."
    )
    add_body_paragraph(
        "The present invention further provides a Pipeline Orchestrator configured to resolve execution sequences across the DAG "
        "via topological sorting, dispatch independent task branches concurrently via asynchronous task gather routines, and maintain "
        "a per-node lifecycle state machine tracking PENDING, READY, RUNNING, COMPLETED, FAILED, and BLOCKED states. A Worker Agent "
        "dispatches ready tasks to modular tool adapters comprising a browser automation adapter utilizing headless browser drivers, "
        "a desktop automation adapter utilizing graphical user interface inspection and programmatic input drivers, a terminal adapter "
        "executing shell subprocesses, presentation slide and document synthesis adapters, optical character recognition modules, "
        "and version control tool adapters."
    )
    add_body_paragraph(
        "The present invention further provides a Supervisor Agent that validates intermediate task execution outputs against "
        "pre-registered contract assertions, verifying return exit codes, non-empty stdout streams, and structural schema invariants. "
        "Upon detection of a contract violation or runtime exception, the Supervisor Agent emits a failure event to a Healing Agent. "
        "The Healing Agent classifies the failure against a fixed diagnostic taxonomy comprising timeout exceptions, file not found errors, "
        "syntax errors, invalid argument errors, and permission denials. The Healing Agent executes a bounded recovery protocol constrained "
        "by a maximum retry threshold of three iterations, selectively applying parameterized retries, input patching, tool substitution, "
        "or dynamic topological replanning."
    )
    add_body_paragraph(
        "The present invention coordinates all inter-agent communications and state transitions via an asynchronous pub/sub Event Bus "
        "transmitting typed events including goal submission, plan creation, task readiness, permission requests, permission grants, "
        "task execution, contract validation, healing dispatch, and workflow completion. A notification service streams real-time "
        "telemetry and execution logs to client interfaces over bidirectional WebSocket channels, providing comprehensive auditability "
        "and interactive governance."
    )

    # SECTION 5
    add_section_heading("SECTION 5 — DETAILED DESCRIPTION OF THE INVENTION")
    add_body_paragraph(
        "Referring to the accompanying drawings and specifications, the architecture and operational methodology of the overall system (100) "
        "are described in detail. The overall system (100) comprises a Goal Input Interface (101), a Planner Agent (102) containing a "
        "TaskDecompositionEngine (103), an LLM Fallback Engine (104), and a DAG Constructor (105), a Permission Manager (106) operating "
        "a Risk Assessment Matrix (107) and a User Approval Interface (108), a Pipeline Orchestrator (109) maintaining a SharedWorkflowState "
        "repository (110), a Worker Agent (111) coupled to a ToolRegistry (112) comprising a BrowserToolAdapter (113), a DesktopToolAdapter (114), "
        "a TerminalToolAdapter (115), and Document Adapters (116), a Supervisor Agent (117) operating a Contract Validation Module (118), "
        "a Healing Agent (119) comprising an Error Classification Module (120) and a Recovery Strategy Engine (121), an EventBus (122), "
        "a WebSocket Notification Service (123), a Historical Execution Log (124), and an Output Presentation Layer (125)."
    )
    add_body_paragraph(
        "The Goal Input Interface (101) receives an unconstrained natural language prompt from a user client via an HTTP POST endpoint "
        "or an asynchronous WebSocket frame. The Goal Input Interface (101) validates the payload, establishes a unique workflow identifier, "
        "and publishes a 'goal.submitted' event onto the EventBus (122). The Planner Agent (102) subscribes to the 'goal.submitted' event "
        "and routes the natural language string to the TaskDecompositionEngine (103)."
    )
    add_body_paragraph(
        "The TaskDecompositionEngine (103) executes a deterministic rule-based analysis by applying regular expression pattern extractors "
        "and keyword classification trees against the natural language string. The deterministic decomposition identifies operational intents "
        "such as directory reorganization, web research, desktop application manipulation, presentation generation, document conversion, "
        "or shell command execution. When an intent pattern is matched, the TaskDecompositionEngine (103) generates a structured list of task "
        "specifications without initiating an external artificial intelligence model call, achieving a decomposition latency of less than "
        "15 milliseconds. If the input string fails to match deterministic intent templates, the Planner Agent (102) routes the prompt to the "
        "LLM Fallback Engine (104), which invokes a large language model constrained by strict JSON schema definitions to generate the task list."
    )
    add_body_paragraph(
        "The DAG Constructor (105) receives the decomposed task list and constructs a mathematical Directed Acyclic Graph denoted as "
        "G = (V, E), wherein V = {v_1, v_2, ..., v_n} represents the set of task nodes and E represents directed dependency edges "
        "specifying precedence constraints. Formally, each task node v_i is defined as a 5-tuple: "
        "v_i = <id_i, tau_i, theta_i, r_i, S_i>, where id_i is a unique task identifier, tau_i denotes the required tool adapter type, "
        "theta_i denotes the input parameter dictionary, r_i denotes the risk classification tier, and S_i denotes the set of immediate "
        "prerequisite task identifiers that must complete prior to the activation of task v_i."
    )
    add_body_paragraph(
        "The DAG Constructor (105) emits a 'plan.created' event to the EventBus (122), which delivers the synthesized plan to the Permission "
        "Manager (106). The Permission Manager (106) inspects each task node v_i using the Risk Assessment Matrix (107). The Risk Assessment "
        "Matrix (107) categorizes tasks into four distinct risk tiers: LOW (read-only operations, web navigation, text parsing), "
        "MEDIUM (file creation, non-destructive document synthesis), HIGH (file modification, package installations, active script execution), "
        "and CRITICAL (destructive file deletions, administrative shell execution, external repository modification). For tasks classified as "
        "HIGH or CRITICAL, the Permission Manager (106) sets an internal asynchronous event lock and dispatches a 'permission.requested' "
        "event via the WebSocket Notification Service (123) to the User Approval Interface (108). The User Approval Interface (108) displays "
        "a visual modal to the operator detailing the exact command, target path, and risk level. Upon receiving an operator grant, the "
        "Permission Manager (106) releases the asynchronous lock and publishes a 'permission.granted' event; conversely, if the operator "
        "denies the request or an approval timeout expires, the node is marked as BLOCKED."
    )
    add_body_paragraph(
        "The Pipeline Orchestrator (109) receives the approved execution plan and initializes the SharedWorkflowState repository (110). "
        "The Pipeline Orchestrator (109) applies a topological sort algorithm to graph G to determine valid execution tiers. Tasks possessing "
        "no unresolved dependencies (S_i = empty) are transitioned from PENDING to READY state and published as 'task.ready' events. "
        "Independent task nodes belonging to identical topological tiers are dispatched concurrently using asynchronous multi-task routines "
        "such as asyncio.gather(). As tasks transition through lifecycle states, the SharedWorkflowState repository (110) records timestamps, "
        "active worker assignments, and intermediate artifacts."
    )
    add_body_paragraph(
        "The Worker Agent (111) subscribes to 'task.ready' events, retrieves the corresponding task tuple v_i, and identifies the appropriate "
        "adapter from the ToolRegistry (112). When the tool type tau_i specifies web automation, the task is dispatched to the BrowserToolAdapter (113), "
        "which controls headless browser instances via Playwright drivers to navigate URLs, fill forms, click selectors, and extract DOM trees. "
        "When tau_i specifies native window management, the DesktopToolAdapter (114) leverages accessibility frameworks (pywinauto) and coordinate "
        "automation (PyAutoGUI) to launch applications and simulate input events. When tau_i specifies operating system commands, the "
        "TerminalToolAdapter (115) executes asynchronous shell subprocesses in isolated execution contexts. For specialized tasks, Document "
        "Adapters (116) execute slide deck generation via python-pptx, PDF compilation via ReportLab, OCR text extraction via Tesseract, "
        "and Git repository management via GitPython."
    )
    add_body_paragraph(
        "Upon completion of task execution by a tool adapter, the Worker Agent (111) generates an output payload O_i and publishes a "
        "'task.executed' event. The Supervisor Agent (117) intercepts the 'task.executed' event and invokes the Contract Validation Module (118). "
        "The Contract Validation Module (118) executes a formal invariant verification function Psi(v_i, O_i) defined as: "
        "Psi(v_i, O_i) = (exit_code == 0) and (O_i satisfies Schema(v_i)). Specifically, the validation verifies that the operating system process "
        "exited with code zero, standard error streams contain no unhandled exceptions, stdout is non-empty where data synthesis is expected, "
        "and generated file artifacts exist on disk with valid file size thresholds. If Psi(v_i, O_i) evaluates to TRUE, the Supervisor Agent (117) "
        "marks the task as COMPLETED and publishes 'task.completed', enabling the Pipeline Orchestrator (109) to evaluate downstream dependents."
    )
    add_body_paragraph(
        "If Psi(v_i, O_i) evaluates to FALSE, the Supervisor Agent (117) marks the task as FAILED and publishes a 'task.failed' event containing "
        "the raw error trace. The Healing Agent (119) intercepts 'task.failed' and routes the context to the Error Classification Module (120). "
        "The Error Classification Module (120) classifies the failure into a deterministic taxonomy C defined as: "
        "C = {TIMEOUT, FILE_NOT_FOUND, SYNTAX_ERROR, INVALID_ARGUMENTS, PERMISSION_DENIED}. The Recovery Strategy Engine (121) inspects the "
        "classified category, verifies that the task's retry counter k_i has not exceeded the bounded maximum threshold K_max = 3, and selects "
        "one of four deterministic remediation strategies: (a) Parameterized Retry with exponential backoff for transient timeouts; (b) Input "
        "Patching to correct file paths or malformed command arguments; (c) Tool Substitution to execute an equivalent task using an alternate tool "
        "adapter; or (d) Topological Replanning, wherein the Planner Agent (102) dynamically mutates the downstream sub-graph of G. If k_i > K_max, "
        "the Healing Agent (119) escalates the failure to the user interface and halts dependent branches."
    )
    add_body_paragraph(
        "Throughout workflow execution, all state transitions, validation results, and diagnostic events emitted onto the EventBus (122) "
        "are ingested by the WebSocket Notification Service (123) and streamed to the client application, while concurrently being persisted "
        "in the Historical Execution Log (124). Upon successful resolution of all terminal DAG nodes, the Pipeline Orchestrator (109) emits "
        "a 'workflow.completed' event, prompting the Output Presentation Layer (125) to render interactive popcards, file download links, "
        "and terminal execution summaries."
    )

    # SECTION 6
    add_section_heading("SECTION 6 — DETAILED DESCRIPTION OF THE DRAWING")
    add_body_paragraph(
        "FIG. 1 illustrates a comprehensive block diagram of the event-driven multi-agent automation system (100) according to an exemplary "
        "embodiment of the present invention, depicting structural relationships, inter-agent data paths, and event communication flows."
    )
    add_body_paragraph(
        "As shown in FIG. 1, the natural language user request enters the system (100) through the Goal Input Interface (101), which is "
        "operatively connected via bidirectional communication lines to the EventBus (122). The EventBus (122) serves as the central asynchronous "
        "communication backbone of the system (100). The Goal Input Interface (101) transmits the validated user prompt to the Planner Agent (102). "
        "Within the Planner Agent (102), the incoming goal is initially routed to the TaskDecompositionEngine (103) for deterministic sub-15ms "
        "rule-based decomposition. When open-ended instructions require generative comprehension, the TaskDecompositionEngine (103) communicates "
        "with the LLM Fallback Engine (104). The outputs of either decomposition path are delivered to the DAG Constructor (105), which synthesizes "
        "the execution graph G = (V, E) and publishes a 'plan.created' event to the EventBus (122)."
    )
    add_body_paragraph(
        "The EventBus (122) delivers the execution graph to the Permission Manager (106). The Permission Manager (106) passes each node through "
        "the Risk Assessment Matrix (107). For tasks identified as HIGH or CRITICAL risk, the Permission Manager (106) engages an asynchronous "
        "lock and routes an authorization request to the User Approval Interface (108). The User Approval Interface (108) communicates operator "
        "authorization decisions back to the Permission Manager (106)."
    )
    add_body_paragraph(
        "The approved execution graph is delivered to the Pipeline Orchestrator (109), which is operatively coupled to the SharedWorkflowState "
        "repository (110). The Pipeline Orchestrator (109) performs topological dependency resolution and emits 'task.ready' events across the "
        "EventBus (122) to the Worker Agent (111). The Worker Agent (111) is connected to the ToolRegistry (112), which manages dispatch across "
        "the BrowserToolAdapter (113), the DesktopToolAdapter (114), the TerminalToolAdapter (115), and the Document Adapters (116). The tool "
        "adapters interact directly with host system interfaces, including web engines, GUI windowing servers, operating system shells, and file storage."
    )
    add_body_paragraph(
        "Upon task execution, the Worker Agent (111) routes the execution result O_i via 'task.executed' events on the EventBus (122) to the "
        "Supervisor Agent (117). The Supervisor Agent (117) utilizes the Contract Validation Module (118) to verify schema invariants and exit "
        "codes. If validation succeeds, a 'task.completed' event is returned to the Pipeline Orchestrator (109). If validation fails, a 'task.failed' "
        "event is dispatched to the Healing Agent (119). Within the Healing Agent (119), the failure is processed by the Error Classification "
        "Module (120) and passed to the Recovery Strategy Engine (121). The Recovery Strategy Engine (121) executes bounded recovery by issuing "
        "remediation instructions back to the Worker Agent (111) or triggering topological graph mutation in the Planner Agent (102)."
    )
    add_body_paragraph(
        "Finally, all lifecycle telemetry and output artifacts generated throughout the execution are captured from the EventBus (122) by the "
        "WebSocket Notification Service (123) and the Historical Execution Log (124), which feed the Output Presentation Layer (125) for client display."
    )

    # SECTION 7
    add_section_heading("SECTION 7 — ABSTRACT OF THE INVENTION")
    add_body_paragraph(
        "An event-driven multi-agent system and method for autonomous desktop and browser automation are disclosed. The system resolves "
        "the brittleness of macro-based robotic process automation and the state confusion and security hazards of unconstrained monolithic "
        "language model loops. The architecture comprises a four-agent operational model consisting of a Planner Agent, a Worker Agent, a "
        "Supervisor Agent, and a Healing Agent, coordinated asynchronously via a typed pub/sub Event Bus. A hybrid planning engine decomposes "
        "natural language goals into a Directed Acyclic Graph (DAG) with a sub-15ms decomposition latency (12.18ms measured rule-based decomposition, "
        "14.85ms full planner latency). A Permission Manager classifies tasks across a four-tier risk matrix (LOW, MEDIUM, HIGH, CRITICAL) "
        "and gates high-risk operations behind asynchronous human approval. The Worker Agent dispatches approved tasks to modular tool adapters "
        "at 0.25ms dispatch latency with an aggregate throughput exceeding 3,891 tasks per second. The Supervisor Agent enforces contract invariants "
        "Psi(v_i, O_i), and upon failure, the Healing Agent classifies errors against a fixed taxonomy C = {TIMEOUT, FILE_NOT_FOUND, SYNTAX_ERROR, "
        "INVALID_ARGUMENTS, PERMISSION_DENIED} and executes bounded self-healing constrained by a maximum retry budget K_max = 3."
    )

    # SECTION 8 — SHORTER CLAIMS
    add_section_heading("SECTION 8 — CLAIMS")
    add_body_paragraph("We claim:", indent=0.0)

    # Claim 1
    add_claim_paragraph(1, "A multi-agent desktop and browser automation system (100) comprising:")
    add_claim_subclause("a", "a goal input interface (101) configured to receive a natural language goal;")
    add_claim_subclause("b", "a hybrid planner agent (102) configured to decompose the natural language goal into a Directed Acyclic Graph (DAG) of dependent task nodes (105);")
    add_claim_subclause("c", "a permission manager (106) configured to evaluate task risk levels using a risk assessment matrix (107) and gate high-risk tasks behind user approval (108);")
    add_claim_subclause("d", "a pipeline orchestrator (109) configured to topologically schedule and execute tasks while tracking state in a shared workflow state repository (110);")
    add_claim_subclause("e", "a worker agent (111) configured to execute tasks using modular tool adapters (112) comprising browser (113), desktop (114), terminal (115), and document adapters (116);")
    add_claim_subclause("f", "a supervisor agent (117) configured to validate task execution outputs against contract invariants using a validation module (118);")
    add_claim_subclause("g", "a healing agent (119) configured to classify execution failures (120) and execute bounded self-healing remediation (121); and")
    add_claim_subclause("h", "an asynchronous event bus (122) configured to coordinate inter-agent communication and stream telemetry via a notification service (123).")

    # Claim 2
    add_claim_paragraph(2, "The system as claimed in claim 1, wherein the hybrid planner agent (102) comprises a deterministic rule-based decomposition engine (103) for sub-15ms graph generation and a schema-constrained generative fallback engine (104).")

    # Claim 3
    add_claim_paragraph(3, "The system as claimed in claim 1, wherein the permission manager (106) halts tasks categorized as HIGH or CRITICAL risk using an asynchronous synchronization lock until explicit approval is received from the user approval interface (108).")

    # Claim 4
    add_claim_paragraph(4, "The system as claimed in claim 1, wherein the healing agent (119) categorizes failures into a fixed taxonomy comprising timeout, file not found, syntax error, invalid arguments, and permission denial, and executes parameterized retry, input patching, tool substitution, or topological replanning within a maximum retry budget of three iterations.")

    # Claim 5
    add_claim_paragraph(5, "A computer-implemented method for multi-agent automation, comprising receiving a natural language goal, decomposing the goal into a DAG of tasks using hybrid planning, classifying task risk tiers, gating high-risk tasks behind user approval, executing approved tasks via tool adapters, validating task outputs against contract invariants, performing bounded error recovery, and streaming execution telemetry over an event bus.")

    try:
        doc.save(filename)
        print(f"Updated patent application document saved at: {filename}")
    except PermissionError:
        alt_filename = "d:/PROJECTS/Major/research/docx/AetherPhoenix_Patent_Application_Updated.docx"
        doc.save(alt_filename)
        print(f"Primary file locked by another application. Saved updated document to: {alt_filename}")

if __name__ == "__main__":
    create_patent_document()

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_border(cell, **kwargs):
    """
    Set cell borders for a clean architectural drawing placeholder frame.
    kwargs: top, bottom, left, right
    values: dict(sz=12, val='single', color='888888')
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{kwargs.get("top", {}).get("val", "single")}" w:sz="{kwargs.get("top", {}).get("sz", "12")}" w:space="0" w:color="{kwargs.get("top", {}).get("color", "888888")}"/>\n'
        f'  <w:left w:val="{kwargs.get("left", {}).get("val", "single")}" w:sz="{kwargs.get("left", {}).get("sz", "12")}" w:space="0" w:color="{kwargs.get("left", {}).get("color", "888888")}"/>\n'
        f'  <w:bottom w:val="{kwargs.get("bottom", {}).get("val", "single")}" w:sz="{kwargs.get("bottom", {}).get("sz", "12")}" w:space="0" w:color="{kwargs.get("bottom", {}).get("color", "888888")}"/>\n'
        f'  <w:right w:val="{kwargs.get("right", {}).get("val", "single")}" w:sz="{kwargs.get("right", {}).get("sz", "12")}" w:space="0" w:color="{kwargs.get("right", {}).get("color", "888888")}"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)

def set_cell_background(cell, fill_hex="FAFAFA"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def generate_patent_with_drawings(filename="d:/PROJECTS/Major/research/docx/AetherPhoenix_Patent_Application_With_Drawings.docx"):
    doc = docx.Document()

    # Section 1: Main Specification (A4, 1-inch margins)
    main_section = doc.sections[0]
    main_section.page_width = Inches(8.27)
    main_section.page_height = Inches(11.69)
    main_section.top_margin = Inches(1.0)
    main_section.bottom_margin = Inches(1.0)
    main_section.left_margin = Inches(1.0)
    main_section.right_margin = Inches(1.0)
    
    # Specification Header
    header = main_section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hrun = hp.add_run("INDIAN PATENT APPLICATION — COMPLETE SPECIFICATION")
    hrun.font.name = "Times New Roman"
    hrun.font.size = Pt(8.5)
    hrun.font.color.rgb = RGBColor(120, 120, 120)

    # Base styling
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)

    def add_section_heading(title_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title_text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11.5)
        return p

    def add_body_paragraph(text, indent=0.0):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(indent)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)
        return p

    def add_claim_paragraph(claim_num, text):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        run_num = p.add_run(f"{claim_num}.\t")
        run_num.bold = True
        run_num.font.name = 'Times New Roman'
        run_num.font.size = Pt(11)
        
        run_body = p.add_run(text)
        run_body.font.name = 'Times New Roman'
        run_body.font.size = Pt(11)
        return p

    def add_claim_subclause(letter, text):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.65)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.space_before = Pt(1.5)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        run_l = p.add_run(f"{letter}.\t")
        run_l.font.name = 'Times New Roman'
        run_l.font.size = Pt(11)
        
        run_b = p.add_run(text)
        run_b.font.name = 'Times New Roman'
        run_b.font.size = Pt(11)
        return p

    # FORM 2 HEADER
    p_f2 = doc.add_paragraph()
    p_f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_f2.paragraph_format.space_after = Pt(2)
    r = p_f2.add_run("FORM 2\nTHE PATENTS ACT, 1970\n(39 of 1970)\n&\nTHE PATENTS RULES, 2003\nCOMPLETE SPECIFICATION\n(See section 10 and rule 13)")
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11)

    # SECTION 1
    add_section_heading("SECTION 1 — TITLE OF THE INVENTION")
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(10)
    r_title = p_title.add_run("\"A SYSTEM AND METHOD FOR EVENT-DRIVEN MULTI-AGENT DESKTOP AND BROWSER AUTOMATION WITH HYBRID PLANNING, PERMISSION GOVERNANCE, AND BOUNDED SELF-HEALING\"")
    r_title.bold = True
    r_title.font.name = 'Times New Roman'
    r_title.font.size = Pt(11)

    p_app = doc.add_paragraph()
    p_app.paragraph_format.space_after = Pt(6)
    p_app.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_app = p_app.add_run("APPLICANT(S):\nName: AetherPhoenix Research Group\nNationality: Indian\nAddress: Department of Computer Science and Engineering, India\n\nPREAMBLE TO THE DESCRIPTION:\nThe following specification particularly describes the invention and the manner in which it is to be performed.")
    r_app.font.name = 'Times New Roman'
    r_app.font.size = Pt(10.5)

    # SECTION 2
    add_section_heading("SECTION 2 — FIELD OF THE INVENTION")
    add_body_paragraph(
        "The present invention relates generally to intelligent computing automation systems, and more particularly to multi-agent software architectures and event-driven orchestration pipelines for executing multi-step goals expressed in natural language across desktop and browser environments. The invention encompasses specialized tool adapters for operating system terminal subprocesses, file systems, web browser drivers, desktop graphical user interfaces, structured document synthesis engines (PDF, PPT), optical character recognition (OCR) routines, and Git version control repositories. The invention further pertains to multi-tier risk-based permission governance, invariant contract supervision, and bounded self-healing recovery mechanisms."
    )
    add_body_paragraph(
        "Modern computerized workflows require operators to coordinate across heterogeneous computing boundaries including shell command lines, web browsers, native desktop applications, and file managers. The field of the invention resides at the intersection of runtime natural language task decomposition into Directed Acyclic Graphs (DAGs), asynchronous dependency scheduling, fine-grained access control gating, and deterministic exception remediation in multi-agent frameworks."
    )

    # SECTION 3
    add_section_heading("SECTION 3 — BACKGROUND OF THE INVENTION")
    add_body_paragraph(
        "Traditional robotic process automation (RPA) tools and static macro scripts rely upon hardcoded coordinates, absolute element selectors, and rigid procedural sequences. When graphical interfaces change, web DOM elements render asynchronously, or file paths vary, conventional RPA scripts break catastrophically without autonomous diagnostic or recovery capabilities. Concurrently, monolithic single-loop Large Language Model (LLM) agents combine task planning, execution, supervision, and error recovery within a single prompting loop, inducing severe state confusion over extended execution horizons, context exhaustion, and lack of schema-based output verification."
    )
    add_body_paragraph(
        "Furthermore, unconstrained autonomous agents acting directly upon host operating systems create severe security hazards, as they lack deterministic permission gates and may execute destructive operations (such as unintended file deletion, administrative privilege escalation, or unauthorized network transmission) without human oversight. In addition, existing workflow orchestrators (such as Apache Airflow) require DAGs to be authored manually in advance by software developers and cannot generate dynamic execution graphs from natural language goals at runtime. Prior to the present invention, no unified architecture combined sub-15ms DAG synthesis, multi-tier risk permission gating, contract validation, and bounded self-healing within a fully decoupled, event-driven pipeline."
    )

    # SECTION 4
    add_section_heading("SECTION 4 — SUMMARY OF THE INVENTION")
    add_body_paragraph(
        "The present invention provides an event-driven multi-agent system and computer-implemented method for autonomous desktop and browser automation. The system acquires an unconstrained natural language goal and decomposes it at runtime into a Directed Acyclic Graph (DAG) of interdependent task nodes via a hybrid planning engine. The hybrid planning engine comprises a deterministic rule-based decomposition path that matches parameterized intent templates in sub-15ms latency without external model calls, and a schema-constrained LLM fallback path for open-ended instructions."
    )
    add_body_paragraph(
        "A Permission Manager evaluates each synthesized task node against a four-tier risk classification matrix (LOW, MEDIUM, HIGH, CRITICAL). Tasks classified under HIGH or CRITICAL risk are halted behind an asynchronous synchronization lock and gated behind explicit user approval via an interactive interface, while LOW and MEDIUM tasks execute autonomously. A Pipeline Orchestrator performs topological sorting, executes independent branches concurrently via asynchronous multi-task routines, and tracks per-node lifecycle states (PENDING, READY, RUNNING, COMPLETED, FAILED, BLOCKED)."
    )
    add_body_paragraph(
        "A Worker Agent dispatches ready tasks to modular tool adapters comprising a browser automation adapter (Playwright), a desktop GUI adapter (pywinauto, PyAutoGUI), a terminal shell adapter, document synthesis adapters (python-pptx, ReportLab), an OCR adapter, and a Git version control adapter. A Supervisor Agent intercepts task outputs and validates them against formal contract assertions (exit codes and schema invariants). Upon validation failure, a Healing Agent classifies the error against a fixed taxonomy (TIMEOUT, FILE_NOT_FOUND, SYNTAX_ERROR, INVALID_ARGUMENTS, PERMISSION_DENIED) and executes bounded remediation constrained by a maximum retry threshold of three iterations, applying parameterized retry, input patching, tool substitution, or topological replanning. An asynchronous pub/sub Event Bus decouples all agents, while a notification service streams real-time telemetry to client interfaces over WebSocket channels."
    )

    # SECTION 5
    add_section_heading("SECTION 5 — DETAILED DESCRIPTION OF THE INVENTION")
    add_body_paragraph(
        "Referring to the architecture of the overall system (100), the framework comprises a Goal Input Interface (101), a Planner Agent (102) having a TaskDecompositionEngine (103), an LLM Fallback Engine (104), and a DAG Constructor (105), a Permission Manager (106) operating a Risk Assessment Matrix (107) and a User Approval Interface (108), a Pipeline Orchestrator (109) maintaining a SharedWorkflowState repository (110), a Worker Agent (111) coupled to a ToolRegistry (112) containing a BrowserToolAdapter (113), a DesktopToolAdapter (114), a TerminalToolAdapter (115), and Document Adapters (116), a Supervisor Agent (117) operating a Contract Validation Module (118), a Healing Agent (119) comprising an Error Classification Module (120) and a Recovery Strategy Engine (121), an EventBus (122), a WebSocket Notification Service (123), a Historical Execution Log (124), and an Output Presentation Layer (125)."
    )
    add_body_paragraph(
        "The Goal Input Interface (101) receives a natural language prompt from a client over HTTP/WebSocket, assigns a unique workflow identifier, and publishes a 'goal.submitted' event onto the EventBus (122). The Planner Agent (102) routes the prompt to the TaskDecompositionEngine (103), which applies regex extractors and classification trees to synthesize task lists in under 15ms. If no rule pattern matches, the LLM Fallback Engine (104) generates structured tasks conforming to strict JSON schema definitions. The DAG Constructor (105) builds a Directed Acyclic Graph G = (V, E), wherein each task node v_i is defined by the formal 5-tuple: v_i = <id_i, tau_i, theta_i, r_i, S_i>, where id_i is the task identifier, tau_i is the required tool adapter, theta_i represents input arguments, r_i denotes the risk tier, and S_i represents prerequisite dependency task identifiers."
    )
    add_body_paragraph(
        "The Permission Manager (106) inspects task nodes using the Risk Assessment Matrix (107), categorizing tasks into LOW (read-only operations), MEDIUM (non-destructive file creation), HIGH (file modifications, active scripts), and CRITICAL (destructive file deletions, administrative commands). For HIGH and CRITICAL nodes, the Permission Manager (106) activates an asynchronous lock and dispatches a 'permission.requested' event via the WebSocket Notification Service (123) to the User Approval Interface (108). Upon approval, the lock is released and a 'permission.granted' event is emitted; if denied or timed out, the node is set to BLOCKED."
    )
    add_body_paragraph(
        "The Pipeline Orchestrator (109) resolves dependencies in graph G via topological sorting and manages lifecycle states in the SharedWorkflowState repository (110). Ready nodes are dispatched as 'task.ready' events to the Worker Agent (111), which invokes the corresponding adapter from the ToolRegistry (112), including BrowserToolAdapter (113), DesktopToolAdapter (114), TerminalToolAdapter (115), or Document Adapters (116). Upon task completion, the Worker Agent (111) emits a 'task.executed' event containing result payload O_i."
    )
    add_body_paragraph(
        "The Supervisor Agent (117) intercepts the payload and executes an invariant contract verification Psi(v_i, O_i) via the Contract Validation Module (118), defined as: Psi(v_i, O_i) = (exit_code == 0) and (O_i satisfies Schema(v_i)). If Psi evaluates to TRUE, the task is marked COMPLETED and 'task.completed' is emitted. If Psi evaluates to FALSE, the Supervisor Agent (117) emits 'task.failed'. The Healing Agent (119) classifies the failure via the Error Classification Module (120) into taxonomy C = {TIMEOUT, FILE_NOT_FOUND, SYNTAX_ERROR, INVALID_ARGUMENTS, PERMISSION_DENIED}. The Recovery Strategy Engine (121) enforces a retry budget K_max = 3 and executes: (a) Parameterized Retry with backoff; (b) Input Patching; (c) Tool Substitution; or (d) Topological Replanning via the Planner Agent (102). Workflow telemetry is captured in the Historical Execution Log (124) and displayed via the Output Presentation Layer (125)."
    )

    # SECTION 6
    add_section_heading("SECTION 6 — DETAILED DESCRIPTION OF DRAWINGS")
    add_body_paragraph(
        "FIG. 1 illustrates a block diagram of the overall multi-agent automation system (100). The Goal Input Interface (101) receives natural language goals and connects to the EventBus (122). The Planner Agent (102) coordinates the TaskDecompositionEngine (103), LLM Fallback Engine (104), and DAG Constructor (105) to output execution graph G. The Permission Manager (106) evaluates task nodes against the Risk Assessment Matrix (107) and User Approval Interface (108). The Pipeline Orchestrator (109) tracks task states in the SharedWorkflowState repository (110) and dispatches tasks to the Worker Agent (111), which invokes adapters (113–116) from the ToolRegistry (112). Task outputs are validated by the Supervisor Agent (117) and Contract Validation Module (118), while failures are remediated by the Healing Agent (119), Error Classification Module (120), and Recovery Strategy Engine (121). Telemetry flows through the WebSocket Notification Service (123), Historical Execution Log (124), and Output Presentation Layer (125)."
    )
    add_body_paragraph(
        "FIG. 2 illustrates a flowchart of the hybrid planning and risk-gated permission pipeline. A natural language goal is parsed via the deterministic rule path (103) in sub-15ms, or routed to the LLM fallback path (104). The DAG Constructor (105) generates graph G = (V, E). The Permission Manager (106) evaluates each task's risk tier (107); LOW and MEDIUM tasks proceed immediately, whereas HIGH and CRITICAL tasks trigger an asynchronous approval modal (108). Upon approval, tasks enter the topological execution queue; upon denial, nodes transition to BLOCKED."
    )
    add_body_paragraph(
        "FIG. 3 illustrates a state transition diagram of the contract validation and bounded self-healing lifecycle. Upon task execution, the Supervisor Agent (117) checks exit codes and output schemas Psi(v_i, O_i). Valid outputs transition the task node to COMPLETED. If validation fails, the Healing Agent (119) classifies the failure into taxonomy C (120), increments retry counter k_i <= 3, and selects a recovery strategy (121) from parameterized retry, input patching, tool substitution, or topological replanning. If k_i > 3, the failure is escalated and execution halts."
    )

    # SECTION 7
    add_section_heading("SECTION 7 — ABSTRACT OF THE INVENTION")
    add_body_paragraph(
        "An event-driven multi-agent system (100) and method for desktop and browser automation are disclosed. The system eliminates the brittleness of static macro automation and the state confusion of monolithic language model loops. The architecture comprises a Planner Agent (102), a Worker Agent (111), a Supervisor Agent (117), and a Healing Agent (119) coordinated asynchronously via an Event Bus (122). A hybrid planning engine decomposes natural language goals into a Directed Acyclic Graph (DAG) in sub-15ms latency (12.18ms decomposition, 14.85ms full planner). A Permission Manager (106) classifies tasks across a four-tier risk matrix (LOW, MEDIUM, HIGH, CRITICAL) and gates high-risk operations behind asynchronous human approval. The Worker Agent (111) executes approved tasks across browser, desktop GUI, terminal, and document adapters at 0.25ms dispatch latency. The Supervisor Agent (117) enforces invariant contract assertions Psi(v_i, O_i), and the Healing Agent (119) diagnoses failures against taxonomy C = {TIMEOUT, FILE_NOT_FOUND, SYNTAX_ERROR, INVALID_ARGUMENTS, PERMISSION_DENIED} to execute bounded self-healing with a maximum retry budget K_max = 3."
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

    # =========================================================================
    # FORMAL DRAWING SHEETS (FIG. 1, FIG. 2, FIG. 3)
    # =========================================================================
    figures_info = [
        (
            1, 3,
            "FIG. 1",
            "OVERALL SYSTEM ARCHITECTURE BLOCK DIAGRAM",
            "Paste/Insert your System Architecture Diagram here.\nEnsure callout labels match reference numbers (100) through (125):\n"
            "• Goal Input Interface (101), Planner Agent (102), TaskDecompositionEngine (103), LLM Fallback (104), DAG Constructor (105)\n"
            "• Permission Manager (106), Risk Matrix (107), User Approval Interface (108)\n"
            "• Pipeline Orchestrator (109), SharedWorkflowState (110)\n"
            "• Worker Agent (111), ToolRegistry (112), Browser (113), Desktop (114), Terminal (115), Document (116)\n"
            "• Supervisor Agent (117), Contract Validation (118), Healing Agent (119), Error Classifier (120), Recovery Engine (121), EventBus (122)"
        ),
        (
            2, 3,
            "FIG. 2",
            "HYBRID PLANNING & RISK-GATED PERMISSION FLOWCHART",
            "Paste/Insert your Goal Decomposition & Permission Flowchart here.\n"
            "Flow components:\n"
            "• User Goal Acquisition → Deterministic Pattern Matching (Sub-15ms) vs. LLM Fallback Schema Parsing\n"
            "• DAG Construction G = (V, E)\n"
            "• Task Risk Tier Evaluation (LOW / MEDIUM / HIGH / CRITICAL)\n"
            "• Asynchronous Human Approval Lock Modal for HIGH/CRITICAL → Approved (TOPOLOGICAL QUEUE) vs. Denied/Timeout (BLOCKED)"
        ),
        (
            3, 3,
            "FIG. 3",
            "CONTRACT VALIDATION & BOUNDED SELF-HEALING LIFECYCLE DIAGRAM",
            "Paste/Insert your Execution & Healing Lifecycle State Diagram here.\n"
            "Flow components:\n"
            "• Worker Task Execution → Supervisor Invariant Check Ψ(v_i, O_i) = (exit_code == 0 ∧ O_i ⊨ Schema(v_i))\n"
            "• Pass → COMPLETED State | Fail → Healing Agent Diagnostic Taxonomy Classification (C)\n"
            "• Retry Counter Check (k_i ≤ 3) → Bounded Remediation (Retry / Patch / Substitute / Replan)\n"
            "• Retry Counter Exhaustion (k_i > 3) → Escalation Alert & Workflow Branch Halt"
        ),
    ]

    for sheet_no, total_sheets, fig_label, fig_title, placeholder_desc in figures_info:
        # Add Page Break for each Drawing Sheet
        doc.add_page_break()
        
        # Drawing Sheet Header Table
        tbl_hdr = doc.add_table(rows=1, cols=2)
        tbl_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER
        c_left = tbl_hdr.cell(0, 0)
        c_right = tbl_hdr.cell(0, 1)
        c_left.width = Inches(3.5)
        c_right.width = Inches(2.77)
        
        p_l = c_left.paragraphs[0]
        p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_l.paragraph_format.space_before = Pt(0)
        p_l.paragraph_format.space_after = Pt(0)
        r_l = p_l.add_run("NAME OF APPLICANT: AetherPhoenix Research Group\nTOTAL SHEETS: 3")
        r_l.bold = True
        r_l.font.name = "Times New Roman"
        r_l.font.size = Pt(9.5)
        
        p_r = c_right.paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_r.paragraph_format.space_before = Pt(0)
        p_r.paragraph_format.space_after = Pt(0)
        r_r = p_r.add_run(f"SHEET NO.: {sheet_no} OF {total_sheets}")
        r_r.bold = True
        r_r.font.name = "Times New Roman"
        r_r.font.size = Pt(9.5)

        # Drawing Title
        p_fig_t = doc.add_paragraph()
        p_fig_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig_t.paragraph_format.space_before = Pt(14)
        p_fig_t.paragraph_format.space_after = Pt(10)
        r_ft = p_fig_t.add_run(f"{fig_label} — {fig_title}")
        r_ft.bold = True
        r_ft.font.name = "Times New Roman"
        r_ft.font.size = Pt(11)

        # Drawing Image Placeholder Box (Single Cell Table with custom border and height)
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.27)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_border(cell, top=dict(sz=12, val="dashed", color="777777"),
                              bottom=dict(sz=12, val="dashed", color="777777"),
                              left=dict(sz=12, val="dashed", color="777777"),
                              right=dict(sz=12, val="dashed", color="777777"))
        set_cell_background(cell, "F8F9FA")
        
        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(60)
        cp.paragraph_format.space_after = Pt(6)
        
        r_box1 = cp.add_run(f"[ PASTE / INSERT {fig_label} IMAGE HERE ]\n\n")
        r_box1.bold = True
        r_box1.font.name = "Times New Roman"
        r_box1.font.size = Pt(12)
        r_box1.font.color.rgb = RGBColor(60, 60, 60)
        
        r_box2 = cp.add_run(placeholder_desc)
        r_box2.font.name = "Times New Roman"
        r_box2.font.size = Pt(9.5)
        r_box2.font.color.rgb = RGBColor(100, 100, 100)
        
        cp_end = cell.add_paragraph()
        cp_end.paragraph_format.space_after = Pt(60)

        # Drawing Sheet Footer / Signature Block
        p_sig = doc.add_paragraph()
        p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_sig.paragraph_format.space_before = Pt(16)
        p_sig.paragraph_format.space_after = Pt(0)
        r_sig = p_sig.add_run("_____________________________________\nSignature of Applicant / Patent Agent")
        r_sig.font.name = "Times New Roman"
        r_sig.font.size = Pt(10)

    try:
        doc.save(filename)
        print(f"Successfully generated patent application with drawing sheets at: {filename}")
    except PermissionError:
        alt_filename = "d:/PROJECTS/Major/research/docx/AetherPhoenix_Patent_Application_With_Drawing_Sheets.docx"
        doc.save(alt_filename)
        print(f"Primary file locked. Successfully saved to: {alt_filename}")

if __name__ == "__main__":
    generate_patent_with_drawings()

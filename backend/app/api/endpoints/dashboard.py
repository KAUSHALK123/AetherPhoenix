from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.services.observability import get_observability_service

router = APIRouter()
obs_service = get_observability_service()


@router.get("/stats")
async def get_dashboard_stats():
    """Get aggregated dashboard statistics."""
    try:
        return obs_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def get_workflows():
    """Get active and historical workflows."""
    try:
        return obs_service.get_workflows()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow_details(workflow_id: str):
    """Get detailed state of a single workflow by ID."""
    details = obs_service.get_workflow_by_id(workflow_id)
    if not details:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return details


@router.get("/events")
async def get_recent_events(workflow_id: Optional[str] = None):
    """Get a rolling log of recent execution events."""
    try:
        return obs_service.get_recent_events(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_class=HTMLResponse)
async def get_dashboard_ui():
    """Serves the rich web dashboard for real-time observability."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AetherPhoenix Event Observability Dashboard</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-color: #0b0f19;
            --panel-bg: rgba(17, 24, 39, 0.75);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.15);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.15);
            --warning: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.15);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.15);
            --info: #3b82f6;
            --info-glow: rgba(59, 130, 246, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            overflow-x: hidden;
            background-image: 
                radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.07) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(59, 130, 246, 0.07) 0px, transparent 50%);
            background-attachment: fixed;
            min-height: 100vh;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 40px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(12px);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-section h1 {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #a78bfa, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo-section h1::before {
            content: '';
            display: inline-block;
            width: 14px;
            height: 14px;
            background: #8b5cf6;
            border-radius: 50%;
            box-shadow: 0 0 12px #8b5cf6;
        }

        .refresh-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: var(--text-secondary);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 30px 40px;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            backdrop-filter: blur(12px);
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--primary);
        }

        .stat-card.running::before { background: var(--info); }
        .stat-card.completed::before { background: var(--success); }
        .stat-card.failed::before { background: var(--danger); }
        .stat-card.retries::before { background: var(--warning); }

        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .stat-label {
            font-size: 14px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
        }

        /* Main Workspace Panels */
        .main-layout {
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }

        /* Glassmorphism Panel */
        .panel {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            height: 600px;
        }

        .panel-header {
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }

        /* Workflows List */
        .workflows-list {
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding-right: 4px;
        }

        .workflow-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .workflow-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.12);
        }

        .workflow-item.active {
            background: var(--primary-glow);
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.1);
        }

        .wf-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }

        .wf-goal {
            font-weight: 500;
            font-size: 15px;
            max-width: 70%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .status-badge {
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 20px;
            text-transform: uppercase;
        }

        .status-badge.running { background: var(--info-glow); color: var(--info); }
        .status-badge.completed { background: var(--success-glow); color: var(--success); }
        .status-badge.failed { background: var(--danger-glow); color: var(--danger); }
        .status-badge.pending { background: rgba(255, 255, 255, 0.05); color: var(--text-secondary); }

        .progress-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 10px;
        }

        .progress-bar-bg {
            flex: 1;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 0.4s ease;
        }

        .progress-text {
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 600;
        }

        /* Detail Panel */
        .detail-panel {
            flex: 1;
            overflow-y: auto;
            padding-right: 4px;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: var(--text-secondary);
            gap: 10px;
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            stroke: var(--text-secondary);
        }

        /* Workflow Detail Views */
        .detail-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 20px;
        }

        .detail-title h2 {
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .detail-meta {
            display: flex;
            gap: 15px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .tasks-grid {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .task-card {
            background: rgba(255, 255, 255, 0.015);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px;
            transition: border-color 0.2s ease;
        }

        .task-card:hover {
            border-color: rgba(255, 255, 255, 0.12);
        }

        .task-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .task-name-section {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .task-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .task-icon.completed { background: var(--success-glow); color: var(--success); }
        .task-icon.running { background: var(--info-glow); color: var(--info); }
        .task-icon.failed { background: var(--danger-glow); color: var(--danger); }
        .task-icon.pending { background: rgba(255, 255, 255, 0.05); color: var(--text-secondary); }

        .task-title {
            font-weight: 600;
            font-size: 15px;
        }

        .task-desc {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }

        .task-footer-details {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 12px;
            color: var(--text-secondary);
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 10px;
        }

        .task-badge {
            background: rgba(255, 255, 255, 0.04);
            padding: 2px 8px;
            border-radius: 4px;
        }

        .validation-details {
            margin-top: 12px;
            padding: 12px;
            background: rgba(239, 68, 68, 0.05);
            border: 1px dashed rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            font-size: 13px;
        }

        .validation-details.passed {
            background: rgba(16, 185, 129, 0.05);
            border-color: rgba(16, 185, 129, 0.2);
        }

        .validation-details h4 {
            font-weight: 600;
            margin-bottom: 6px;
        }

        /* Recent Events Log Console */
        .console-panel {
            background: #060913;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            font-family: 'Fira Code', monospace;
            height: 350px;
            display: flex;
            flex-direction: column;
        }

        .console-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 12px;
            margin-bottom: 12px;
        }

        .console-title {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .console-body {
            flex: 1;
            overflow-y: auto;
            font-size: 13px;
            line-height: 1.6;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding-right: 4px;
        }

        .log-row {
            display: flex;
            gap: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.01);
            padding-bottom: 4px;
        }

        .log-time {
            color: var(--text-secondary);
            min-width: 90px;
        }

        .log-source {
            font-weight: 500;
            min-width: 140px;
        }

        .log-source.PLANNER { color: #d946ef; }
        .log-source.WORKER { color: #f59e0b; }
        .log-source.SUPERVISOR { color: #3b82f6; }
        .log-source.EXECUTION_ENGINE { color: #10b981; }

        .log-type {
            font-weight: 500;
            min-width: 200px;
        }

        .log-message {
            color: var(--text-primary);
            flex: 1;
        }

        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-section">
            <h1>AetherPhoenix Supervisor Dashboard</h1>
        </div>
        <div class="refresh-status">
            <div class="pulse-dot"></div>
            <span>Connected - Live Monitoring Feed</span>
        </div>
    </header>

    <div class="container">
        <!-- Stats Row -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-label">Total Workflows</div>
                <div class="stat-value" id="stat-total">0</div>
            </div>
            <div class="stat-card running">
                <div class="stat-label">Active Running</div>
                <div class="stat-value" id="stat-running">0</div>
            </div>
            <div class="stat-card completed">
                <div class="stat-label">Completed</div>
                <div class="stat-value" id="stat-completed">0</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-label">Failed</div>
                <div class="stat-value" id="stat-failed">0</div>
            </div>
            <div class="stat-card retries">
                <div class="stat-label">Total Retries</div>
                <div class="stat-value" id="stat-retries">0</div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-layout">
            <!-- Left: Workflows list -->
            <div class="panel">
                <div class="panel-header">
                    <h3 class="panel-title">Workflows</h3>
                </div>
                <div class="workflows-list" id="workflowsList">
                    <!-- Loaded dynamically -->
                </div>
            </div>

            <!-- Right: Details of selected workflow -->
            <div class="panel">
                <div class="panel-header">
                    <h3 class="panel-title">Workflow Execution Trace</h3>
                </div>
                <div class="detail-panel" id="detailPanel">
                    <div class="empty-state">
                        <svg fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        <p>Select a workflow from the list to view tracing details</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom: Live logs -->
        <div class="console-panel">
            <div class="console-header">
                <div class="console-title">Live System Event Stream</div>
            </div>
            <div class="console-body" id="consoleBody">
                <!-- Log rows loaded dynamically -->
            </div>
        </div>
    </div>

    <script>
        let selectedWorkflowId = null;

        async function updateStats() {
            try {
                const res = await fetch('/api/v1/dashboard/stats');
                const data = await res.json();
                document.getElementById('stat-total').innerText = data.total_workflows || 0;
                document.getElementById('stat-running').innerText = data.running_workflows || 0;
                document.getElementById('stat-completed').innerText = data.completed_workflows || 0;
                document.getElementById('stat-failed').innerText = data.failed_workflows || 0;
                document.getElementById('stat-retries').innerText = data.total_retries || 0;
            } catch (err) {
                console.error("Failed to update stats", err);
            }
        }

        async function updateWorkflows() {
            try {
                const res = await fetch('/api/v1/dashboard/workflows');
                const data = await res.json();
                const container = document.getElementById('workflowsList');
                container.innerHTML = '';

                if (data.length === 0) {
                    container.innerHTML = '<div class="empty-state"><p>No active or completed workflows found</p></div>';
                    return;
                }

                data.forEach(wf => {
                    const activeClass = (selectedWorkflowId === wf.workflow_id) ? 'active' : '';
                    const item = document.createElement('div');
                    item.className = `workflow-item ${activeClass}`;
                    item.onclick = () => selectWorkflow(wf.workflow_id);

                    // Clean status display
                    const cleanStatus = wf.status.includes('.') ? wf.status.split('.').pop() : wf.status;

                    item.innerHTML = `
                        <div class="wf-header">
                            <div class="wf-goal" title="${wf.goal}">${wf.goal || "Goal not defined"}</div>
                            <span class="status-badge ${cleanStatus.toLowerCase()}">${cleanStatus}</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${wf.progress_percentage}%"></div>
                            </div>
                            <span class="progress-text">${wf.progress_percentage}%</span>
                        </div>
                    `;
                    container.appendChild(item);
                });
            } catch (err) {
                console.error("Failed to update workflows list", err);
            }
        }

        async function selectWorkflow(id) {
            selectedWorkflowId = id;
            updateWorkflows();
            updateWorkflowDetails();
        }

        async function updateWorkflowDetails() {
            if (!selectedWorkflowId) return;

            try {
                const res = await fetch(`/api/v1/dashboard/workflows/${selectedWorkflowId}`);
                if (!res.ok) {
                    selectedWorkflowId = null;
                    return;
                }
                const wf = await res.json();
                const container = document.getElementById('detailPanel');

                const cleanStatus = wf.status.includes('.') ? wf.status.split('.').pop() : wf.status;

                let tasksHtml = '';
                const sortedTasks = Object.values(wf.tasks);

                if (sortedTasks.length === 0) {
                    tasksHtml = '<p class="empty-state">No tasks generated for this workflow.</p>';
                } else {
                    sortedTasks.forEach(task => {
                        const statusClean = task.status.includes('.') ? task.status.split('.').pop() : task.status;
                        
                        // Icon mapping
                        let iconHtml = '●';
                        if (statusClean === 'COMPLETED') {
                            iconHtml = `<svg width="12" height="12" fill="currentColor" viewBox="0 0 16 16"><path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z"/></svg>`;
                        } else if (statusClean === 'RUNNING') {
                            iconHtml = `<span style="animation: spin 1s linear infinite; display: inline-block;">↻</span>`;
                        } else if (statusClean === 'FAILED') {
                            iconHtml = '✕';
                        }

                        // Validation panel
                        let validationHtml = '';
                        if (wf.validations && wf.validations[task.task_id]) {
                            const val = wf.validations[task.task_id];
                            validationHtml = `
                                <div class="validation-details ${val.is_valid ? 'passed' : ''}">
                                    <h4>QA Validation Report (${val.decision})</h4>
                                    ${val.issues.length > 0 ? `<ul>${val.issues.map(i => `<li>${i}</li>`).join('')}</ul>` : '<p>All validation success criteria satisfied.</p>'}
                                </div>
                            `;
                        }

                        // Risk level
                        const riskHtml = task.risk_level ? `<span class="task-badge">Risk: ${task.risk_level}</span>` : '';

                        tasksHtml += `
                            <div class="task-card">
                                <div class="task-card-header">
                                    <div class="task-name-section">
                                        <div class="task-icon ${statusClean.toLowerCase()}">${iconHtml}</div>
                                        <div class="task-title">${task.task_name}</div>
                                    </div>
                                    <span class="status-badge ${statusClean.toLowerCase()}">${statusClean}</span>
                                </div>
                                <div class="task-desc">${task.description || "No description provided"}</div>
                                <div class="task-footer-details">
                                    <span class="task-badge">Category: ${task.category}</span>
                                    ${riskHtml}
                                    <span class="task-badge">Retries: ${task.retry_count}</span>
                                    ${task.dependencies.length > 0 ? `<span class="task-badge">Deps: ${task.dependencies.map(d => d.substring(0, 8)).join(', ')}</span>` : ''}
                                </div>
                                ${validationHtml}
                            </div>
                        `;
                    });
                }

                container.innerHTML = `
                    <div class="detail-header">
                        <div class="detail-title">
                            <h2>${wf.goal}</h2>
                            <div class="detail-meta">
                                <div class="meta-item">ID: ${wf.workflow_id.substring(0, 8)}...</div>
                                <div class="meta-item">Duration: ${wf.execution_duration ? wf.execution_duration.toFixed(1) : 0}s</div>
                            </div>
                        </div>
                        <span class="status-badge ${cleanStatus.toLowerCase()}">${cleanStatus}</span>
                    </div>
                    <div class="tasks-grid">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 5px;">Execution Steps</h3>
                        ${tasksHtml}
                    </div>
                `;
            } catch (err) {
                console.error("Failed to update workflow details", err);
            }
        }

        async function updateEvents() {
            try {
                const res = await fetch('/api/v1/dashboard/events');
                const data = await res.json();
                const container = document.getElementById('consoleBody');
                container.innerHTML = '';

                if (data.length === 0) {
                    container.innerHTML = '<div style="color: var(--text-secondary); text-align: center; margin-top: 40px;">No events emitted in current session.</div>';
                    return;
                }

                data.forEach(e => {
                    const row = document.createElement('div');
                    row.className = 'log-row';

                    // Parse timestamp to HH:MM:SS
                    const date = new Date(e.timestamp);
                    const timeStr = date.toTimeString().split(' ')[0];

                    row.innerHTML = `
                        <span class="log-time">[${timeStr}]</span>
                        <span class="log-source ${e.source_component}">${e.source_component}</span>
                        <span class="log-type">${e.event_type}</span>
                        <span class="log-message">${JSON.stringify(e.payload)}</span>
                    `;
                    container.appendChild(row);
                });
            } catch (err) {
                console.error("Failed to update events stream", err);
            }
        }

        // Live looping
        function poll() {
            updateStats();
            updateWorkflows();
            updateWorkflowDetails();
            updateEvents();
        }

        poll();
        setInterval(poll, 2000);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)

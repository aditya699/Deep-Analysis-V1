from datetime import datetime
import base64
import re
from typing import Dict, Any, List
from azure.storage.blob.aio import BlobServiceClient
from app.db.mongo import log_error, get_db
from azure.storage.blob import BlobBlock
from pymongo.database import Database

async def create_html_report(session_id: str) -> str:
    """
    Generate a clean, modern HTML report by fetching the latest analysis data from database.
    
    Parameters:
    - session_id: The session ID to fetch data for
    
    Returns:
    - HTML content as string
    """
    # Get database connection
    db = await get_db()
    deep_analysis_collection = db["deep_analysis"]
    
    # Get current timestamp for the report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Fetch the latest analysis data from database (sorted by created_at desc)
    analysis_doc = await deep_analysis_collection.find_one(
        {"session_id": session_id},
        sort=[("created_at", -1)]  # Get the latest document
    )
    
    if not analysis_doc:
        raise ValueError(f"No analysis data found for session {session_id}")
    
    # Extract data from the document
    summary = analysis_doc.get("summary", "No summary available")
    kpi_analyses = analysis_doc.get("kpi_analyses", [])
    csv_info = analysis_doc.get("csv_info", {})
    
    # Get dataset info
    total_columns = csv_info.get("total_columns", 0)
    column_names = csv_info.get("column_names", [])
    
    # Convert markdown to HTML for proper formatting
    def markdown_to_html(text):
        """Convert basic markdown formatting to HTML"""
        if not text:
            return "No content available"
        
        # Convert markdown to HTML
        html = text
        
        # Headers
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Bold text
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        
        # Italic text
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Lists - handle bullet points
        lines = html.split('\n')
        in_list = False
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                processed_lines.append(f'<li>{stripped[2:].strip()}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                processed_lines.append(line)
        
        if in_list:
            processed_lines.append('</ul>')
        
        html = '\n'.join(processed_lines)
        
        # Convert line breaks to <br> tags, but not inside HTML tags
        html = re.sub(r'\n(?![<>])', '<br>\n', html)
        
        # Clean up extra breaks around HTML elements
        html = re.sub(r'<br>\s*(</?(?:h[1-6]|ul|li|strong|em)>)', r'\1', html)
        html = re.sub(r'(</?(?:h[1-6]|ul|li|strong|em)>)\s*<br>', r'\1', html)
        
        return html
    
    # Convert summary from markdown to HTML
    summary_html = markdown_to_html(summary)
    
    # Modern CSS with enhanced AI agent feel
    css_styles = """
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #8b5cf6;
            --secondary: #f8fafc;
            --accent: #06b6d4;
            --accent-light: #22d3ee;
            --text: #0f172a;
            --text-light: #64748b;
            --text-muted: #94a3b8;
            --border: #e2e8f0;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --ai-glow: #8b5cf6;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            --gradient-ai: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-success: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            min-height: 100vh;
            position: relative;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            z-index: -1;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }
        
        /* Header with AI Agent Feel */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #8b5cf6 100%);
            color: white;
            padding: 4rem 0;
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-xl);
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(120, 219, 255, 0.3) 0%, transparent 50%);
            animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-10px) rotate(1deg); }
        }
        
        .header-content {
            position: relative;
            z-index: 1;
        }
        
        .ai-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            padding: 0.5rem 1rem;
            border-radius: 2rem;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .ai-badge::before {
            content: '🤖';
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .header h1 {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            text-shadow: 0 4px 8px rgba(0,0,0,0.2);
            background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            font-size: 1.3rem;
            opacity: 0.95;
            font-weight: 400;
            margin-bottom: 1rem;
        }
        
        .completion-status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--gradient-success);
            padding: 0.75rem 1.5rem;
            border-radius: 2rem;
            font-weight: 600;
            box-shadow: var(--shadow-lg);
            animation: slideInUp 1s ease-out 0.5s both;
        }
        
        .completion-status::before {
            content: '✅';
            font-size: 1.2rem;
        }
        
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Main Content */
        .main-content {
            padding: 2rem 0;
        }
        
        /* Summary Section with AI Enhancement */
        .summary-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
            backdrop-filter: blur(20px);
            border-radius: 1.5rem;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        .summary-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-ai);
            border-radius: 1.5rem 1.5rem 0 0;
        }
        
        .summary-card h2 {
            color: var(--primary);
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            position: relative;
        }
        
        .summary-card h2::before {
            content: '🧠';
            font-size: 1.8rem;
            animation: brainPulse 3s ease-in-out infinite;
        }
        
        @keyframes brainPulse {
            0%, 100% { transform: scale(1); filter: hue-rotate(0deg); }
            50% { transform: scale(1.1); filter: hue-rotate(20deg); }
        }
        
        .dataset-info {
            background: var(--secondary);
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
            border-left: 4px solid var(--accent);
        }
        
        .dataset-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .stat-item {
            text-align: center;
            padding: 1rem;
            background: white;
            border-radius: 0.5rem;
            box-shadow: var(--shadow);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .stat-label {
            color: var(--text-light);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Enhanced KPI Cards with AI Feel */
        .kpi-grid {
            display: grid;
            gap: 2.5rem;
            margin-top: 2rem;
        }
        
        .kpi-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
            backdrop-filter: blur(20px);
            border-radius: 1.5rem;
            overflow: hidden;
            box-shadow: var(--shadow-xl);
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        
        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }
        
        .kpi-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 25px 50px -12px rgba(102, 126, 234, 0.25);
        }
        
        .kpi-card:hover::before {
            opacity: 1;
        }
        
        .kpi-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #8b5cf6 100%);
            color: white;
            padding: 2rem;
            position: relative;
            overflow: hidden;
        }
        
        .kpi-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
            animation: shimmer 4s linear infinite;
            pointer-events: none;
        }
        
        @keyframes shimmer {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .kpi-header h3 {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0;
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .kpi-header h3::before {
            content: '⚡';
            font-size: 1.5rem;
            animation: sparkle 2s ease-in-out infinite;
        }
        
        @keyframes sparkle {
            0%, 100% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.2) rotate(180deg); }
        }
        
        .kpi-content {
            padding: 2.5rem;
            position: relative;
        }
        
        /* Enhanced Chart Section */
        .chart-container {
            text-align: center;
            margin: 2rem 0;
            background: linear-gradient(135deg, rgba(248, 250, 252, 0.8) 0%, rgba(241, 245, 249, 0.8) 100%);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.5);
            position: relative;
            overflow: hidden;
        }
        
        .chart-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent) 0%, var(--primary) 50%, var(--accent-light) 100%);
        }
        
        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 0.75rem;
            box-shadow: var(--shadow-lg);
            transition: transform 0.3s ease;
        }
        
        .chart-container img:hover {
            transform: scale(1.02);
        }
        
        .no-chart {
            padding: 4rem;
            color: var(--text-muted);
            font-style: italic;
            font-size: 1.1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }
        
        .no-chart::before {
            content: '📊';
            font-size: 3rem;
            opacity: 0.5;
            animation: float 3s ease-in-out infinite;
        }
        
        /* Enhanced Content Sections */
        .content-section {
            margin: 2.5rem 0;
        }
        
        .content-section h4 {
            color: var(--primary);
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            position: relative;
            padding-bottom: 0.5rem;
        }
        
        .content-section h4::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 3rem;
            height: 2px;
            background: var(--gradient-ai);
            border-radius: 1px;
        }
        
        .business-analysis {
            background: linear-gradient(135deg, rgba(240, 249, 255, 0.9) 0%, rgba(224, 242, 254, 0.9) 100%);
            backdrop-filter: blur(10px);
            border-left: 4px solid var(--accent);
            padding: 2rem;
            border-radius: 1rem;
            line-height: 1.8;
            position: relative;
            box-shadow: var(--shadow);
        }
        
        .business-analysis::before {
            content: '💡';
            position: absolute;
            top: 1rem;
            right: 1rem;
            font-size: 1.5rem;
            opacity: 0.6;
            animation: pulse 2s infinite;
        }
        
        /* Styling for converted markdown content */
        .business-analysis h1, .business-analysis h2, .business-analysis h3 {
            color: var(--primary);
            margin: 1.5rem 0 1rem 0;
            font-weight: 700;
        }
        
        .business-analysis h1 { font-size: 1.8rem; }
        .business-analysis h2 { font-size: 1.5rem; }
        .business-analysis h3 { font-size: 1.3rem; }
        
        .business-analysis ul {
            margin: 1rem 0;
            padding-left: 1.5rem;
        }
        
        .business-analysis li {
            margin: 0.5rem 0;
            line-height: 1.6;
        }
        
        .business-analysis strong {
            color: var(--primary-dark);
            font-weight: 600;
        }
        
        .business-analysis em {
            color: var(--text-light);
            font-style: italic;
        }
        
        .explanation-section h1, .explanation-section h2, .explanation-section h3 {
            color: var(--primary);
            margin: 1.5rem 0 1rem 0;
            font-weight: 700;
        }
        
        .explanation-section h1 { font-size: 1.8rem; }
        .explanation-section h2 { font-size: 1.5rem; }
        .explanation-section h3 { font-size: 1.3rem; }
        
        .explanation-section ul {
            margin: 1rem 0;
            padding-left: 1.5rem;
        }
        
        .explanation-section li {
            margin: 0.5rem 0;
            line-height: 1.6;
        }
        
        .explanation-section strong {
            color: var(--primary-dark);
            font-weight: 600;
        }
        
        .explanation-section em {
            color: var(--text-light);
            font-style: italic;
        }
        
        .code-section {
            background: #1e293b;
            color: #e2e8f0;
            border-radius: 0.75rem;
            overflow: hidden;
            margin: 1rem 0;
        }
        
        .code-header {
            background: #334155;
            padding: 0.75rem 1rem;
            font-size: 0.875rem;
            font-weight: 500;
            border-bottom: 1px solid #475569;
        }
        
        .code-content {
            padding: 1.5rem;
            overflow-x: auto;
        }
        
        .code-content pre {
            margin: 0;
            font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        
        .explanation-section {
            background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%);
            border-left: 4px solid var(--warning);
            padding: 1.5rem;
            border-radius: 0.5rem;
            line-height: 1.7;
        }
        
        .steps-section {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border-left: 4px solid var(--success);
            padding: 1.5rem;
            border-radius: 0.5rem;
        }
        
        .steps-list {
            list-style: none;
            counter-reset: step-counter;
        }
        
        .steps-list li {
            counter-increment: step-counter;
            margin: 0.75rem 0;
            padding-left: 2rem;
            position: relative;
            line-height: 1.6;
        }
        
        .steps-list li::before {
            content: counter(step-counter);
            position: absolute;
            left: 0;
            top: 0;
            background: var(--success);
            color: white;
            width: 1.5rem;
            height: 1.5rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem 0;
            color: var(--text-light);
            border-top: 1px solid var(--border);
            margin-top: 3rem;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 0 0.5rem;
            }
            
            .kpi-content {
                padding: 1rem;
            }
            
            .dataset-stats {
                grid-template-columns: 1fr;
            }
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Loading animation */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .kpi-card {
            animation: fadeInUp 0.6s ease-out forwards;
        }
        
        .kpi-card:nth-child(1) { animation-delay: 0.1s; }
        .kpi-card:nth-child(2) { animation-delay: 0.2s; }
        .kpi-card:nth-child(3) { animation-delay: 0.3s; }
        .kpi-card:nth-child(4) { animation-delay: 0.4s; }
        .kpi-card:nth-child(5) { animation-delay: 0.5s; }
    """
    
    # Start building HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Deep Analysis Report - {session_id}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>{css_styles}</style>
    </head>
    <body>
        <!-- Header -->
        <header class="header">
            <div class="container">
                <div class="header-content">
                    <div class="ai-badge">AI Agent Analysis Complete</div>
                    <h1>Deep Analysis Report</h1>
                    <p>Powered by Advanced AI • Generated on {timestamp}</p>
                    <div class="completion-status">Analysis Successfully Completed</div>
                </div>
            </div>
        </header>
        
        <!-- Main Content -->
        <main class="main-content">
            <div class="container">
                <!-- Executive Summary -->
                <div class="summary-card">
                    <h2>Executive Summary</h2>
                    
                    <!-- Dataset Information -->
                    <div class="dataset-info">
                        <h4>🔍 AI Analysis Overview</h4>
                        <div class="dataset-stats">
                            <div class="stat-item">
                                <div class="stat-number">{total_columns}</div>
                                <div class="stat-label">Columns Processed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">{len(kpi_analyses)}</div>
                                <div class="stat-label">KPIs Analyzed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">100%</div>
                                <div class="stat-label">Analysis Complete</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-number">AI</div>
                                <div class="stat-label">Powered Analysis</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- AI Generated Summary -->
                    <div class="content-section">
                        <h4>🤖 AI-Generated Insights</h4>
                        <div class="business-analysis">
                            {summary_html}
                        </div>
                    </div>
                </div>
                
                <!-- KPI Analysis Cards -->
                <div class="kpi-grid">
    """
    
    # Add KPI analysis cards
    for i, analysis in enumerate(kpi_analyses):
        kpi_name = analysis.get("kpi_name", "Unknown KPI")
        business_analysis = analysis.get("business_analysis", "No business analysis available")
        code = analysis.get("code", "No code available")
        code_explanation = analysis.get("code_explanation", "No code explanation available")
        chart_url = analysis.get("chart_url", "")
        analysis_steps = analysis.get("analysis_steps", "No analysis steps available")
        
        # Convert markdown content to HTML for proper formatting
        business_analysis_html = markdown_to_html(business_analysis)
        code_explanation_html = markdown_to_html(code_explanation)
        
        html_content += f"""
                    <div class="kpi-card">
                        <div class="kpi-header">
                            <h3>{kpi_name}</h3>
                        </div>
                        <div class="kpi-content">
                            <!-- Chart -->
                            <div class="chart-container">
        """
        
        if chart_url:
            html_content += f'<img src="{chart_url}" alt="Chart for {kpi_name}" loading="lazy">'
        else:
            html_content += '<div class="no-chart">📊 No visualization available</div>'
        
        html_content += f"""
                            </div>
                            
                            <!-- Business Analysis -->
                            <div class="content-section">
                                <h4>💼 Business Analysis</h4>
                                <div class="business-analysis">
                                    {business_analysis_html}
                                </div>
                            </div>
                            
                            <!-- Code -->
                            <div class="content-section">
                                <h4>💻 Analysis Code</h4>
                                <div class="code-section">
                                    <div class="code-header">Python Code</div>
                                    <div class="code-content">
                                        <pre>{code}</pre>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Code Explanation -->
                            <div class="content-section">
                                <h4>📝 Code Explanation</h4>
                                <div class="explanation-section">
                                    {code_explanation_html}
                                </div>
                            </div>
                            
                            <!-- Analysis Steps -->
                            <div class="content-section">
                                <h4>🔍 Analysis Steps</h4>
                                <div class="steps-section">
        """
        
        # Handle analysis steps - could be string or list
        if isinstance(analysis_steps, str):
            # If it's a string, split by numbered points or newlines
            steps = [step.strip() for step in analysis_steps.split('\n') if step.strip()]
            html_content += '<ol class="steps-list">'
            for step in steps:
                # Remove leading numbers if present
                clean_step = re.sub(r'^\d+\.\s*', '', step)
                if clean_step:
                    html_content += f'<li>{clean_step}</li>'
            html_content += '</ol>'
        elif isinstance(analysis_steps, list):
            html_content += '<ol class="steps-list">'
            for step in analysis_steps:
                html_content += f'<li>{step}</li>'
            html_content += '</ol>'
        else:
            html_content += f'<p>{analysis_steps}</p>'
        
        html_content += """
                                </div>
                            </div>
                        </div>
                    </div>
        """
    
    # Close HTML
    html_content += """
                </div>
            </div>
        </main>
        
        <!-- Footer -->
        <footer class="footer">
            <div class="container">
                <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--success);">✅</span>
                        <span>Analysis Complete</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--primary);">🤖</span>
                        <span>AI Powered</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="color: var(--accent);">⚡</span>
                        <span>Real-time Processing</span>
                    </div>
                </div>
                <p>&copy; 2025 Deep Analysis Platform • Advanced AI Analytics Engine</p>
                <p style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                    🧠 Intelligent insights delivered by our AI agent
                </p>
            </div>
        </footer>
        
        <script>
            // Enhanced interactions and AI-like loading effects
            document.addEventListener('DOMContentLoaded', function() {
                // Simulate AI processing completion
                setTimeout(() => {
                    document.body.classList.add('analysis-complete');
                }, 500);
                
                // Progressive card loading with AI feel
                const cards = document.querySelectorAll('.kpi-card');
                cards.forEach((card, index) => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(50px) scale(0.95)';
                    
                    setTimeout(() => {
                        card.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0) scale(1)';
                        
                        // Add completion checkmark
                        setTimeout(() => {
                            const header = card.querySelector('.kpi-header h3');
                            if (header && !header.querySelector('.completion-check')) {
                                const check = document.createElement('span');
                                check.className = 'completion-check';
                                check.innerHTML = '✅';
                                check.style.marginLeft = 'auto';
                                check.style.fontSize = '1.2rem';
                                check.style.opacity = '0';
                                check.style.transform = 'scale(0)';
                                check.style.transition = 'all 0.3s ease';
                                header.appendChild(check);
                                
                                setTimeout(() => {
                                    check.style.opacity = '1';
                                    check.style.transform = 'scale(1)';
                                }, 100);
                            }
                        }, 400);
                    }, index * 200 + 300);
                });
                
                // Enhanced code section interactions
                const codeHeaders = document.querySelectorAll('.code-header');
                codeHeaders.forEach(header => {
                    header.style.cursor = 'pointer';
                    header.style.transition = 'all 0.3s ease';
                    
                    header.addEventListener('mouseenter', function() {
                        this.style.background = '#475569';
                        this.style.transform = 'translateX(5px)';
                    });
                    
                    header.addEventListener('mouseleave', function() {
                        this.style.background = '#334155';
                        this.style.transform = 'translateX(0)';
                    });
                    
                    header.addEventListener('click', function() {
                        const content = this.nextElementSibling;
                        const isHidden = content.style.display === 'none';
                        
                        content.style.transition = 'all 0.3s ease';
                        
                        if (isHidden) {
                            content.style.display = 'block';
                            content.style.opacity = '0';
                            content.style.transform = 'translateY(-10px)';
                            this.innerHTML = '💻 Python Code (Click to collapse)';
                            
                            setTimeout(() => {
                                content.style.opacity = '1';
                                content.style.transform = 'translateY(0)';
                            }, 10);
                        } else {
                            content.style.opacity = '0';
                            content.style.transform = 'translateY(-10px)';
                            this.innerHTML = '💻 Python Code (Click to expand)';
                            
                            setTimeout(() => {
                                content.style.display = 'none';
                            }, 300);
                        }
                    });
                    
                    // Initialize as collapsed
                    header.innerHTML = '💻 Python Code (Click to expand)';
                    header.nextElementSibling.style.display = 'none';
                });
                
                // Add scroll-triggered animations
                const observerOptions = {
                    threshold: 0.1,
                    rootMargin: '0px 0px -50px 0px'
                };
                
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards';
                        }
                    });
                }, observerOptions);
                
                document.querySelectorAll('.content-section').forEach(section => {
                    observer.observe(section);
                });
                
                // Add typing effect to AI insights
                const summaryText = document.querySelector('.business-analysis');
                if (summaryText) {
                    summaryText.style.position = 'relative';
                    summaryText.style.overflow = 'hidden';
                    
                    const cursor = document.createElement('span');
                    cursor.innerHTML = '|';
                    cursor.style.animation = 'blink 1s infinite';
                    cursor.style.color = 'var(--primary)';
                    cursor.style.fontWeight = 'bold';
                    
                    const style = document.createElement('style');
                    style.textContent = `
                        @keyframes blink {
                            0%, 50% { opacity: 1; }
                            51%, 100% { opacity: 0; }
                        }
                    `;
                    document.head.appendChild(style);
                    
                    setTimeout(() => {
                        summaryText.appendChild(cursor);
                        setTimeout(() => cursor.remove(), 3000);
                    }, 1000);
                }
            });
        </script>
    </body>
    </html>
    """
    
    return html_content

async def upload_report_to_blob(html_content: str, blob_client: BlobServiceClient, session_id: str) -> str:
    """
    Upload the HTML report to Azure Blob Storage using optimized streaming.
    
    Parameters:
    - html_content: The HTML content of the report
    - blob_client: Azure Blob Service Client
    - session_id: The session ID to use in the blob name
    
    Returns:
    - The URL of the uploaded report
    """
    try:
        # Azure setup
        container_name = "images-analysis"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"reports/{session_id}/analysis_report_{timestamp}.html"
        blob_client_container = blob_client.get_container_client(container_name).get_blob_client(blob_name)
        
        # Azure block upload setup
        block_list = []
        current_block_data = bytearray()
        block_counter = 0
        azure_block_size = 4 * 1024 * 1024  # 4MB Azure blocks
        
        # Convert HTML content to bytes
        content_bytes = html_content.encode('utf-8')
        total_size = len(content_bytes)
        
        print("🚀 TRUE STREAMING: Processing report without storing full content...")
        
        # Create container if needed
        try:
            await blob_client.get_container_client(container_name).create_container()
        except:
            pass
        
        # Process content in chunks
        for i in range(0, total_size, azure_block_size):
            chunk = content_bytes[i:i + azure_block_size]
            current_block_data.extend(chunk)
            
            # Upload block when it reaches 4MB or is the last chunk
            if len(current_block_data) >= azure_block_size or i + azure_block_size >= total_size:
                block_id = base64.b64encode(f"block-{block_counter:06d}".encode()).decode()
                
                print(f"📤 Uploading Azure block {block_counter + 1}: {len(current_block_data)} bytes")
                
                await blob_client_container.stage_block(
                    block_id=block_id,
                    data=bytes(current_block_data)
                )
                
                block_list.append(BlobBlock(block_id=block_id))
                block_counter += 1
                
                print(f"✅ Block uploaded. Memory freed. Total blocks: {len(block_list)}")
                
                # Clear block data - free memory!
                current_block_data = bytearray()
        
        # Commit all blocks to create final blob
        print(f"🔗 Committing {len(block_list)} blocks to create final blob...")
        
        await blob_client_container.commit_block_list(
            block_list=block_list,
            content_type="text/html"
        )
        
        file_url = blob_client_container.url
        
        print(f"✅ TRUE STREAMING COMPLETE!")
        print(f"📊 Total file size: {total_size} bytes")
        print(f"📊 Azure blocks created: {len(block_list)}")
        print(f"💾 Max memory used: ~{azure_block_size//1024//1024}MB (one block)")
        print(f"🔗 File URL: {file_url}")
        
        return file_url
        
    except Exception as e:
        await log_error(e, "deep_analysis/report.py", "upload_report_to_blob")
        raise 
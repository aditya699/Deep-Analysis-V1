from datetime import datetime
import base64
import re
from typing import Dict, Any, List
from azure.storage.blob.aio import BlobServiceClient
from app.db.mongo import log_error
from azure.storage.blob import BlobBlock

async def create_html_report(session_id: str, db_collection) -> str:
    """
    Generate a beautiful HTML report by pulling data directly from the database.
    
    Parameters:
    - session_id: The session ID to fetch data for
    - db_collection: MongoDB collection containing the analysis data
    
    Returns:
    - HTML content as string
    """
    # Get current timestamp for the report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Fetch the analysis data from database
    analysis_doc = await db_collection.find_one(
        {"session_id": session_id},
        sort=[("created_at", -1)]  # Get the latest session document
    )
    if not analysis_doc:
        raise ValueError(f"No analysis data found for session {session_id}")
    
    # Get summary and KPI analyses
    summary = analysis_doc.get("summary", "")
    kpi_analyses = analysis_doc.get("kpi_analyses", [])
    kpi_status = analysis_doc.get("kpi_status", {})
    
    # Get only the analyzed KPIs (status = 1)
    analyzed_kpis = [kpi for kpi, status in kpi_status.items() if status == 1]
    
    # Filter analyses to only include analyzed KPIs and sort by created_at
    kpi_analyses = [
        analysis for analysis in kpi_analyses 
        if analysis["kpi_name"] in analyzed_kpis
    ]
    kpi_analyses.sort(key=lambda x: x["created_at"], reverse=True)  # Sort by created_at in descending order
    
    # Get the latest analysis for each KPI (first one after sorting)
    latest_analyses = {}
    for analysis in kpi_analyses:
        kpi_name = analysis["kpi_name"]
        if kpi_name not in latest_analyses:  # First occurrence will be the latest due to sorting
            latest_analyses[kpi_name] = analysis
    
    # Convert to list for processing
    kpi_analyses = list(latest_analyses.values())
    
    # CSS styles as a separate string to avoid Python syntax issues
    css_styles = """
        :root {
            --primary-color: #1a73e8;
            --secondary-color: #f5f7fa;
            --accent-color: #4285f4;
            --text-color: #202124;
            --light-text: #5f6368;
            --border-color: #dadce0;
            --success-color: #0f9d58;
            --info-color: #137cbd;
            --warning-color: #f9a825;
            --box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            --primary-color-rgb: 26, 115, 232;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #f8f9fa;
            padding-bottom: 40px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            color: white;
            padding: 40px 0;
            margin-bottom: 40px;
        }
        
        header .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
            letter-spacing: 0.5px;
        }
        
        header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .summary-section {
            background-color: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 40px;
            box-shadow: var(--box-shadow);
        }
        
        .summary-section h2 {
            color: var(--primary-color);
            font-size: 1.8rem;
            margin-bottom: 20px;
            font-weight: 400;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
        }
        
        .kpi-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        
        .kpi-tag {
            background-color: var(--secondary-color);
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 0.9rem;
            color: var(--primary-color);
            border: 1px solid var(--border-color);
        }
        
        .kpi-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .kpi-card {
            background-color: rgba(var(--primary-color-rgb), 0.05);
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.3s ease;
            cursor: pointer;
            border-left: 4px solid var(--primary-color);
        }
        
        .kpi-card:hover {
            transform: translateY(-5px);
        }
        
        .kpi-card h3 {
            color: var(--primary-color);
            margin-bottom: 10px;
            font-weight: 500;
        }
        
        .kpi-section {
            background-color: white;
            border-radius: 8px;
            margin-bottom: 40px;
            overflow: hidden;
            box-shadow: var(--box-shadow);
        }
        
        .kpi-header {
            background: linear-gradient(to right, var(--primary-color), var(--accent-color));
            color: white;
            padding: 20px 25px;
            position: relative;
        }
        
        .kpi-header h2 {
            font-size: 1.8rem;
            font-weight: 400;
        }
        
        .kpi-content {
            padding: 25px;
        }
        
        .visualization {
            text-align: center;
            margin: 20px 0 30px;
            padding: 10px;
            background-color: var(--secondary-color);
            border-radius: 8px;
        }
        
        .visualization img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: var(--box-shadow);
        }
        
        .analysis-container, .insights-container {
            margin-bottom: 30px;
        }
        
        .analysis-container h3, .insights-container h3 {
            font-size: 1.4rem;
            color: var(--primary-color);
            margin-bottom: 15px;
            font-weight: 500;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }
        
        .analysis-content {
            background-color: var(--secondary-color);
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', Courier, monospace;
            white-space: pre-wrap;
            overflow-x: auto;
            border-left: 4px solid var(--info-color);
            margin-bottom: 20px;
        }
        
        .code-section {
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            overflow-x: auto;
        }
        
        .code-section pre {
            margin: 0;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .code-explanation {
            background-color: rgba(19, 124, 189, 0.1);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid var(--info-color);
        }
        
        .code-explanation ol {
            margin-left: 20px;
            padding-left: 0;
        }
        
        .code-explanation li {
            margin-bottom: 10px;
            line-height: 1.6;
        }
        
        .kpi-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: var(--box-shadow);
            border-top: 4px solid var(--primary-color);
        }
        
        .metric-card h4 {
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 1.1rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-color);
        }
        
        .back-to-top {
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            position: fixed;
            bottom: 30px;
            right: 30px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            transition: background-color 0.3s;
        }
        
        .back-to-top:hover {
            background-color: var(--accent-color);
        }
        
        footer {
            margin-top: 40px;
            text-align: center;
            color: var(--light-text);
            font-size: 0.9rem;
        }
        
        .navbar {
            position: sticky;
            top: 0;
            background-color: white;
            box-shadow: var(--box-shadow);
            z-index: 100;
            margin-bottom: 40px;
        }
        
        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
        }
        
        .logo {
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .nav-links {
            display: flex;
            gap: 20px;
        }
        
        .nav-link {
            color: var(--text-color);
            text-decoration: none;
            padding: 8px 12px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        
        .nav-link:hover {
            background-color: var(--secondary-color);
            color: var(--primary-color);
        }
        
        @media (max-width: 768px) {
            .kpi-header h2 {
                font-size: 1.5rem;
            }
            
            .kpi-content {
                padding: 15px;
            }
            
            header h1 {
                font-size: 2rem;
            }
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--accent-color);
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .kpi-section {
            animation: fadeIn 0.5s ease-out forwards;
        }
        
        .kpi-section:nth-child(1) { animation-delay: 0.1s; }
        .kpi-section:nth-child(2) { animation-delay: 0.2s; }
        .kpi-section:nth-child(3) { animation-delay: 0.3s; }
        .kpi-section:nth-child(4) { animation-delay: 0.4s; }
        .kpi-section:nth-child(5) { animation-delay: 0.5s; }
        
        .analysis-steps-container {
            margin: 30px 0;
        }
        
        .analysis-steps {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .analysis-step {
            background-color: white;
            border-radius: 8px;
            box-shadow: var(--box-shadow);
            overflow: hidden;
        }
        
        .step-message {
            border-left: 4px solid var(--info-color);
        }
        
        .step-code {
            border-left: 4px solid var(--primary-color);
        }
        
        .step-header {
            background-color: var(--secondary-color);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }
        
        .step-number {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .step-type {
            font-size: 0.9rem;
            color: var(--light-text);
            text-transform: capitalize;
        }
        
        .step-content {
            padding: 20px;
            line-height: 1.6;
        }
        
        .step-code-content {
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            overflow-x: auto;
        }
        
        .step-code-content pre {
            margin: 0;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            line-height: 1.5;
        }
    """
    
    # Start building the HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Deep Analysis Report</title>
        <style>
        {css_styles}
        </style>
    </head>
    <body>
        <!-- Back to top button -->
        <button class="back-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">↑</button>
        
        <!-- Header -->
        <header>
            <div class="container">
                <h1>Deep Analysis Report</h1>
                <p>Generated on {timestamp}</p>
            </div>
        </header>
        
        <!-- Navigation -->
        <nav class="navbar">
            <div class="container nav-container">
                <div class="logo">Deep Analysis</div>
                <div class="nav-links">
                    <a href="#summary" class="nav-link">Summary</a>
                    <a href="#kpis" class="nav-link">KPIs</a>
                </div>
            </div>
        </nav>
        
        <!-- Summary Section -->
        <section id="summary" class="container">
            <div class="summary-section">
                <h2>Executive Summary</h2>
                <p>This report presents a comprehensive deep analysis of {len(analyzed_kpis)} key performance indicators derived from the dataset. Each KPI is analyzed with detailed metrics, visualizations, and business insights to support data-driven decision making.</p>
                
                <div class="executive-insights-container">
                    <h3 style="margin-top: 20px; color: var(--primary-color);">AI-Generated Summary</h3>
                    <div class="executive-insights-content">{summary}</div>
                </div>
                
                <h3 style="margin-top: 20px; color: var(--primary-color);">Analyzed KPIs</h3>
                <div class="kpi-list">
    """
    
    # Add only the analyzed KPIs to the list
    for kpi in analyzed_kpis:
        html_content += f'<span class="kpi-tag">{kpi}</span>\n'
    
    html_content += """
                </div>
                
                <h3 style="margin-top: 25px; color: var(--primary-color);">Quick Navigation</h3>
                <div class="kpi-cards">
    """
    
    # Add only the analyzed KPIs to the navigation cards
    for kpi in analyzed_kpis:
        kpi_id = kpi.replace(' ', '_')
        html_content += f"""
            <div class="kpi-card" onclick="document.getElementById('{kpi_id}').scrollIntoView({{behavior: 'smooth'}})">
                <h3>{kpi}</h3>
                <p>View analysis and insights</p>
            </div>
        """
    
    html_content += """
                </div>
            </div>
        </section>
        
        <!-- KPIs Section -->
        <section id="kpis" class="container">
    """
    
    # Add only the analyzed KPIs to the main content
    for analysis in kpi_analyses:
        kpi_name = analysis["kpi_name"]
        kpi_id = kpi_name.replace(' ', '_')
        
        html_content += f"""
            <div id="{kpi_id}" class="kpi-section">
                <div class="kpi-header">
                    <h2>{kpi_name}</h2>
                </div>
                <div class="kpi-content">
        """
        
        # Add visualization if available
        if analysis.get("chart_url"):
            html_content += f"""
                    <div class="visualization">
                        <img src="{analysis['chart_url']}" alt="Visualization for {kpi_name}">
                    </div>
            """
        else:
            html_content += """
                    <div class="visualization">
                        <p style="padding: 40px; color: var(--light-text);">No visualization available</p>
                    </div>
            """
        
        # Add analysis results
        html_content += f"""
                    <div class="analysis-container">
                        <h3>Analysis Results</h3>
                        <div class="analysis-content">
                            {analysis.get('analysis', 'No analysis available')}
                        </div>
                    </div>
        """
        
        # Add analysis steps if available
        if analysis.get('analysis_steps'):
            html_content += """
                    <div class="analysis-steps-container">
                        <h3>Analysis Process</h3>
                        <div class="analysis-steps">
            """
            
            for i, step in enumerate(analysis['analysis_steps'], 1):
                step_class = "step-message" if step['type'] == "message" else "step-code"
                html_content += f"""
                            <div class="analysis-step {step_class}">
                                <div class="step-header">
                                    <span class="step-number">Step {i}</span>
                                    <span class="step-type">{step['type']}</span>
                                </div>
                """
                
                if step['content']:
                    html_content += f"""
                                <div class="step-content">
                                    {step['content']}
                                </div>
                    """
                
                if step['code']:
                    html_content += f"""
                                <div class="step-code-content">
                                    <pre>{step['code']}</pre>
                                </div>
                    """
                
                html_content += """
                            </div>
                """
            
            html_content += """
                        </div>
                    </div>
            """
        
        # Add code section if available
        if analysis.get('code'):
            html_content += f"""
                    <div class="code-section">
                        <h3>Analysis Code</h3>
                        <pre>{analysis['code']}</pre>
                    </div>
            """
        
        # Add code explanation if available
        if analysis.get('code_explanation'):
            html_content += f"""
                    <div class="code-explanation">
                        <h3>Code Explanation</h3>
                        {analysis['code_explanation']}
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    # Add footer
    html_content += """
        </section>
        
        <!-- Footer -->
        <footer class="container">
            <p>© 2025 Deep Analysis. All rights reserved.</p>
            <p style="margin-top: 10px;">Generated with ❤️ by Deep Analysis</p>
        </footer>
        
        <script>
            // JavaScript for interactive elements
            document.addEventListener('DOMContentLoaded', function() {
                // Show/hide back to top button based on scroll position
                window.addEventListener('scroll', function() {
                    const backToTopButton = document.querySelector('.back-to-top');
                    if (window.scrollY > 300) {
                        backToTopButton.style.display = 'flex';
                    } else {
                        backToTopButton.style.display = 'none';
                    }
                });
                
                // Initially hide the button
                document.querySelector('.back-to-top').style.display = 'none';
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
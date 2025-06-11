# Deep Analysis V1

A powerful AI-driven data analysis platform powered by specialized agents that combine intelligent chat capabilities with automated deep data analysis. This system enables users to interact with their data through natural language while providing comprehensive automated analysis through a team of specialized AI agents.

## 🎯 Core Features

### 🤖 Deep Analysis Agent
- **Manager Agent**: Intelligent identification and prioritization of key performance indicators from your data
- **Analyst Agent**: Automated analysis and visualization generation for each KPI
- **Business Agent**: Detailed business analysis with actionable insights
- **Code Agent**: Automated Python code generation and execution for data analysis
- **Report Agent**: Beautiful HTML report generation with dynamic visualizations and insights

### 💬 Chat Agent System
- **Query Agent**: Natural language understanding and processing of user questions
- **Context Agent**: Maintains conversation context and history for better understanding
- **Smart Questions Agent**: Suggests relevant questions to explore your data
- **Code Interpreter Agent**: Handles code generation and execution for complex queries
- **Visualization Agent**: Creates and manages charts, tables, and other visualizations
- **Feedback Agent**: Processes user feedback to improve future interactions

## 🛠️ Technical Features

- **True Streaming**: Efficient file processing without storing full content in memory
- **Azure Integration**: Secure file storage and management
- **MongoDB**: Robust session and data management
- **OpenAI Integration**: Advanced language model capabilities for agent operations
- **Container Support**: Docker containerization for easy deployment
- **API Documentation**: Auto-generated API documentation with FastAPI

## 📋 Prerequisites

- Python 3.8+
- MongoDB
- OpenAI API Key
- Azure Storage Account
- Docker (optional)

## 🚀 Getting Started

1. Clone the repository:
```bash
git clone [repository-url]
cd Deep-Analysis-V1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## 📁 Project Structure

```
app/
├── auth/         # Authentication system
├── chat/         # Chat agent system and message handling
├── container/    # Docker configuration
├── core/         # Core application logic
├── db/           # Database operations
├── deep_analysis/# Deep analysis agent system
├── llm/          # Language model integration
└── sessions/     # Session management
```

## 🔐 Security

For security concerns, please email meenakshi.bhtt@gmail.com

## 📞 Support

For support, please open an issue in the GitHub repository or contact
meenakshi.bhtt@gmail.com 
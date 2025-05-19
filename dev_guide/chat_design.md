# 📊 CSV Chatbot Backend – Chat Module

This document outlines the backend design for the **Chat Feature** of the CSV-Aware Chatbot, including the database schemas, REST API endpoints, and message structure.

---

## 🚀 Overview

Users can:
- Upload a CSV file and start a session
- Ask natural-language questions about the CSV
- Get smart replies: text, code, charts, downloadable Excel
- View chat history
- Provide feedback on responses

---

## 🗃️ MongoDB Collections

### 1. `sessions`
Stores uploaded CSV metadata and context.

```json
{
  "_id": "session_uuid",
  "file_name": "sales.csv",
  "file_url": "https://blob/abc.csv",
  "user_id": "user_123",
  "created_at": "2025-05-18T...",
  "columns": ["Region", "Revenue", "Date"],
  "meta": {
    "row_count": 1000,
    "size_kb": 104.5
  },
  "status": "active"
}
````

---

### 2. `messages`

Stores each user and assistant message, with multi-modal support.

```json
{
  "_id": "msg_uuid",
  "session_id": "session_uuid",
  "role": "user" | "assistant",
  "content_type": "text" | "code" | "image" | "table" | "error",
  "content": "Show revenue by region",
  "code": "df.groupby(...)",
  "metadata": {
    "image_url": "https://blob/plot.png",
    "chart_type": "bar",
    "download_link": "https://blob/report.xlsx"
  },
  "timestamp": "2025-05-18T...",
  "edited": false,
  "replied_to": "msg_uuid" // optional
}
```

---

### 3. `feedback`

User thumbs up/down on assistant replies.

```json
{
  "_id": "feedback_id",
  "message_id": "msg_uuid",
  "session_id": "session_uuid",
  "user_id": "user_123",
  "rating": "thumbs_up" | "thumbs_down",
  "comment": "Wrong chart",
  "timestamp": "2025-05-18T..."
}
```

---

## 🔌 API Endpoints – Chat Feature

### 📁 Upload

#### `POST /upload_csv`

Upload a CSV and start a session.

Returns:

```json
{
  "session_id": "uuid",
  "file_url": "...",
  "file_name": "sales.csv",
  "preview_data": [ {...}, {...} ]
}
```

---

### 💬 Chat & History

#### `POST /chat_csv`

Send a message, get a smart reply with text/code/chart.

```json
Request:
{
  "session_id": "uuid",
  "message": "Show sales trend"
}

Response:
{
  "messages": [
    {
      "message_id": "msg-001",
      "role": "user",
      "content_type": "text",
      "content": "Show sales trend",
      "timestamp": "...",
      "metadata": {}
    },
    {
      "message_id": "msg-002",
      "role": "assistant",
      "content_type": "image",
      "content": "Here's your chart",
      "code": "...",
      "metadata": {
        "image_url": "...",
        "chart_type": "line",
        "download_link": "..."
      },
      "timestamp": "..."
    }
  ]
}
```

---

#### `GET /session/{session_id}/history`

Returns all chat messages for the session.

---

#### `PATCH /message/{message_id}/edit`

Edit a previous user message.

```json
{
  "new_content": "Show by category"
}
```

---

### 📤 Feedback

#### `POST /message/{message_id}/feedback`

Submit thumbs up/down and optional comment.

```json
{
  "rating": "thumbs_down",
  "comment": "Wrong chart"
}
```

---

### 📦 File Export

#### `GET /export/{session_id}`

Returns link to download latest generated Excel.

```json
{
  "download_link": "https://blob/export_abc.xlsx"
}
```

---

## 🧠 Message Types

| `content_type` | Description                          |
| -------------- | ------------------------------------ |
| `text`         | Plain answer                         |
| `code`         | Python or Pandas code                |
| `image`        | Chart (matplotlib/seaborn)           |
| `table`        | Tabular output                       |
| `file`         | Downloadable Excel                   |
| `error`        | Something failed (e.g., LLM or exec) |

---

## 🔮 Future Extensions

* LLM streaming response (`/chat_stream`)
* SQL agent support for large files
* LangChain tool support
* Prompt versioning (`prompt_version`)
* Feedback analytics dashboard

---

## 🛡️ Security Notes

* All uploads go to secure Azure Blob Storage
* Files are session-scoped
* Code execution runs in sandbox (restricted kernel)

---

## 📌 Tech Stack

* Backend: FastAPI + MongoDB
* Storage: Azure Blob Storage
* LLMs: OpenAI / OSS (Mistral, GPT, Claude)
* Frontend: React (Next.js, Tailwind)

```

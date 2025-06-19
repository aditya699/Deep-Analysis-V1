# Deep Analysis Frontend

A modern React TypeScript frontend for the Deep Analysis CSV chat application.

## Features

🚀 **Core Features:**
- **CSV Upload**: Drag & drop or click to upload CSV files (up to 30MB)
- **AI Chat**: Interactive chat with your CSV data using OpenAI
- **Smart Questions**: Auto-generated suggested questions about your data
- **Deep Analysis**: Automated multi-KPI analysis with visual reports
- **Session Management**: View, search, and manage your analysis sessions
- **Real-time Feedback**: Thumbs up/down feedback system

🎨 **Modern UI/UX:**
- Responsive design with Tailwind CSS
- Smooth animations with Framer Motion
- Beautiful loading states and transitions
- Dark mode syntax highlighting for code
- Toast notifications for user feedback

🔐 **Authentication:**
- Email-based passwordless authentication
- Secure JWT token management with auto-refresh
- Protected routes and session management

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API communication
- **React Hot Toast** for notifications
- **Framer Motion** for animations
- **React Dropzone** for file uploads
- **React Markdown** for message rendering
- **React Syntax Highlighter** for code display

## Getting Started

### Prerequisites

- Node.js 16+ 
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   ```
   http://localhost:3000
   ```

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   └── LoadingSpinner.tsx
├── contexts/           # React contexts
│   └── AuthContext.tsx
├── pages/             # Page components
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   └── ChatSession.tsx
├── services/          # API services
│   └── api.ts
├── types/             # TypeScript type definitions
│   └── index.ts
├── App.tsx            # Main app component
├── main.tsx           # Entry point
└── index.css          # Global styles
```

## API Integration

The frontend integrates with the following backend endpoints:

### Authentication
- `POST /auth/request-login` - Request login email
- `POST /auth/verify-password` - Verify password and get token
- `POST /auth/refresh-token` - Refresh access token

### CSV Chat
- `POST /chat/upload_csv` - Upload CSV file
- `POST /chat/chat` - Send message to AI
- `POST /chat/feedback` - Submit message feedback
- `POST /chat/chat_summary` - Generate chat summary

### Sessions
- `GET /sessions/get_all_sessions` - Get user sessions
- `GET /sessions/get_session_by_id` - Get specific session
- `DELETE /sessions/delete_session` - Delete session
- `GET /sessions/get_session_messages` - Get session messages

### Deep Analysis
- `POST /deep_analysis/start` - Start deep analysis
- `GET /deep_analysis/status/{session_id}` - Get analysis status

## Environment Configuration

The app is configured to proxy API requests to `http://localhost:8000`. 

To change the backend URL, update the `target` in `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend-url:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

## Usage

### 1. Login
- Enter your email address
- Check your email for the password
- Enter the password to access the application

### 2. Upload CSV
- Drag and drop a CSV file or click to select
- File must be under 30MB
- Wait for upload and smart questions generation

### 3. Chat with Data
- Use suggested smart questions or ask your own
- AI will analyze your data and provide insights
- Code and visualizations are automatically generated
- Provide feedback with thumbs up/down

### 4. Deep Analysis
- Click "Deep Analysis" button in chat session
- Wait for automated KPI analysis to complete
- Download comprehensive HTML report

### 5. Session Management
- View all your sessions on the dashboard
- Search sessions by filename
- Delete old sessions
- Resume chat sessions anytime

## Customization

### Styling
The app uses Tailwind CSS with a custom theme. Primary colors can be changed in `tailwind.config.js`:

```javascript
colors: {
  primary: {
    50: '#f0f9ff',
    500: '#0ea5e9',  // Main brand color
    600: '#0284c7',
    // ...
  }
}
```

### Animations
Animations are handled by Framer Motion. Customize in component files or add new animations in `index.css`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
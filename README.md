# AI Chatbot with LLM Integration

A comprehensive AI chatbot system built with FastAPI, featuring LLM integration, tool usage, conversation management, and security features.

## 🚀 Features

### Core Features
- **LLM Integration**: OpenAI GPT-4 integration with prompt management and token handling
- **Tool Usage**: Built-in tools for web search, calculations, weather, and time
- **Conversation Management**: Session-based chat with context retention
- **Authentication**: JWT-based auth with Google OAuth support
- **Security**: Input sanitization, rate limiting, and abuse detection
- **Real-time Chat**: WebSocket support for live conversations
- **Modern UI**: Responsive web interface for testing

### Technical Features
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic for database schema management
- **API**: RESTful API with comprehensive endpoints
- **WebSocket**: Real-time bidirectional communication
- **Security**: XSS protection, rate limiting, input validation
- **Context Management**: Conversation history and user preferences

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL database
- OpenAI API key
- Google OAuth credentials (optional)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai_chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env_template.txt .env
   # Edit .env with your configuration
   ```

5. **Configure database**
   ```bash
   # Update DATABASE_URL in .env
   # Run database migrations
   alembic upgrade head
   ```

6. **Start the application**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/ai_chatbot_db

# JWT Configuration
SECRET_KEY=your-secret-key-here-make-it-long-and-random
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Security Configuration
MAX_MESSAGE_LENGTH=5000
MAX_REQUESTS_PER_HOUR=100
RATE_LIMIT_WINDOW=3600
```

## 🗄️ Database Schema

### Tables
- **users**: User accounts and authentication
- **tokens**: JWT token management
- **chat_sessions**: Chat session management
- **chat_messages**: Message history
- **conversation_contexts**: Conversation context storage

### Migrations
Run database migrations:
```bash
alembic upgrade head
```

## 🔌 API Endpoints

### Authentication
- `POST /signup` - Register new user
- `POST /login` - User login
- `POST /logout` - User logout
- `GET /me` - Get current user info

### Chatbot
- `POST /chat` - Send message to AI
- `GET /chat/sessions` - Get user sessions
- `GET /chat/sessions/{session_id}` - Get specific session
- `GET /chat/sessions/{session_id}/messages` - Get session messages
- `POST /chat/sessions` - Create new session
- `DELETE /chat/sessions/{session_id}` - Delete session

### WebSocket
- `WS /ws/chat` - Real-time chat endpoint

### OAuth
- `GET /auth/google` - Start Google OAuth
- `GET /auth/google/redirect` - Google OAuth redirect
- `POST /auth/google/callback` - Handle OAuth callback

### Admin
- `GET /admin/security/stats` - Security statistics

## 🛠️ Tools Available

The chatbot can use the following tools:

1. **Web Search**: Search the web for current information
2. **Calculator**: Perform mathematical calculations
3. **Time**: Get current date and time
4. **Weather**: Get weather information (requires API key)

## 🔒 Security Features

- **Input Sanitization**: XSS protection and HTML filtering
- **Rate Limiting**: Per-user and per-IP rate limiting
- **Abuse Detection**: Suspicious activity detection
- **Token Management**: Secure JWT token handling
- **Session Validation**: UUID-based session validation

## 🎨 Frontend

A modern, responsive web interface is available at `/static/index.html` with:

- User authentication (login/signup)
- Real-time chat interface
- Message history
- Typing indicators
- Mobile-responsive design

## 🚀 Usage Examples

### Basic Chat
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### Create Session
```bash
curl -X POST "http://localhost:8000/chat/sessions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
  -d '{"title": "My Chat Session"}'
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat?token=YOUR_TOKEN');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## 📁 Project Structure

```
ai_chatbot/
├── main.py                 # FastAPI application
├── models.py              # Database models
├── schemas.py             # Pydantic schemas
├── auth.py                # Authentication logic
├── oauth.py               # OAuth integration
├── database.py            # Database configuration
├── llm_integration.py     # OpenAI integration
├── tools.py               # Chatbot tools
├── chatbot_orchestrator.py # Chat orchestration
├── security.py            # Security features
├── websocket_chat.py      # WebSocket handling
├── static/                # Frontend files
│   └── index.html        # Web interface
├── alembic/               # Database migrations
├── requirements.txt       # Python dependencies
└── env_template.txt      # Environment template
```

## 🔧 Development

### Running in Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
# Add test files and run with pytest
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 🐳 Docker Support

Use the provided `docker-compose.yml` for containerized deployment:

```bash
docker-compose up -d
```

## 📊 Monitoring

### Security Statistics
Access security stats at `/admin/security/stats` (admin only):

```json
{
  "blocked_ips": 0,
  "suspicious_ips": 0,
  "active_requests": 0,
  "rate_limit_window": 3600,
  "max_requests_per_hour": 100
}
```

## 🔮 Future Enhancements

- [ ] Redis integration for production rate limiting
- [ ] More advanced tools (file processing, API integrations)
- [ ] Conversation analytics and insights
- [ ] Multi-language support
- [ ] Voice chat integration
- [ ] Advanced context management
- [ ] Plugin system for custom tools

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API endpoints

## 🔗 Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) 
# Flight Booking Assistant - Production Deployment Guide

## Architecture Overview

The application is built with:
- **Backend**: FastAPI with async support
- **Frontend**: Vanilla JavaScript with responsive HTML/CSS
- **Services**: OpenAI GPT-4 for NLP, Amadeus API for flight data
- **Storage**: Redis for session management (optional)

## Project Structure

```
Gen_AI/
├── app/
│   ├── api/            # API endpoints
│   │   ├── chat.py     # Chat endpoints
│   │   └── health.py   # Health check endpoints
│   ├── core/           # Core configuration
│   │   ├── config.py   # Settings management
│   │   └── logging.py  # Logging configuration
│   ├── models/         # Pydantic models
│   │   └── schemas.py  # Request/Response schemas
│   ├── services/       # Business logic
│   │   ├── chat_service.py   # Chat handling
│   │   └── flight_service.py # Flight data processing
│   ├── static/         # Frontend assets
│   │   ├── css/        # Stylesheets
│   │   └── js/         # JavaScript files
│   ├── templates/      # HTML templates
│   └── main.py         # FastAPI application
├── docker-compose.yml  # Docker orchestration
├── Dockerfile          # Container definition
├── pyproject.toml      # Dependencies
└── run.py              # Application runner
```

## Setup Instructions

### 1. Environment Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Update with your credentials:
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Amadeus API Configuration  
API_KEY=your_amadeus_api_key
API_SECRET=your_amadeus_api_secret

# Optional: Redis for session persistence
REDIS_URL=redis://localhost:6379
```

### 2. Local Development

Install dependencies with uv:
```bash
uv sync
```

Run the development server:
```bash
uv run python run.py
```

Or use uvicorn directly:
```bash
uv run uvicorn app.main:app --reload --port 8000
```

Access the application:
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Docker Deployment

Build and run with Docker Compose:
```bash
docker-compose up --build
```

For production with daemon mode:
```bash
docker-compose up -d --build
```

### 4. Production Configuration

For production deployment, update the following in `.env`:

```env
DEBUG=false
LOG_LEVEL=INFO
MAX_WORKERS=4
CORS_ORIGINS=["https://yourdomain.com"]
```

## API Endpoints

### Chat Endpoints

**POST /api/chat/**
Send a message to the chatbot
```json
{
  "message": "Find flights from NYC to London on Dec 15",
  "session_id": "optional-session-id"
}
```

**GET /api/chat/history/{session_id}**
Get chat history for a session

**DELETE /api/chat/session/{session_id}**
Clear a chat session

### Health Check

**GET /api/health/**
Check application health status

## Features

1. **Intelligent Flight Search**: Natural language processing for flight queries
2. **Session Management**: Maintains conversation context
3. **Real-time Flight Data**: Integration with Amadeus API
4. **Responsive UI**: Works on desktop and mobile devices
5. **Dark Mode**: Toggle between light and dark themes
6. **Error Handling**: Comprehensive error handling and logging
7. **Production Ready**: Docker support, health checks, and monitoring

## Monitoring & Logs

Logs are stored in `app.log` with rotation:
- Max size: 10MB per file
- Keep last 5 backup files

View logs:
```bash
tail -f app.log
```

For Docker:
```bash
docker-compose logs -f web
```

## Performance Optimization

1. **Caching**: Sessions are cached in memory (or Redis if configured)
2. **Async Operations**: All API calls are async for better performance
3. **Connection Pooling**: Efficient connection management
4. **Static File Serving**: Frontend assets served efficiently

## Security Considerations

1. **API Keys**: Never commit `.env` files to version control
2. **CORS**: Configure allowed origins for production
3. **Input Validation**: All inputs validated with Pydantic
4. **Error Messages**: Sensitive information hidden in production
5. **Rate Limiting**: Consider adding rate limiting for production

## Troubleshooting

### Common Issues

1. **API Keys Invalid**: Verify your OpenAI and Amadeus credentials
2. **Port Already in Use**: Change port in `run.py` or docker-compose
3. **Dependencies Missing**: Run `uv sync` to install all dependencies
4. **Docker Build Fails**: Ensure Docker daemon is running

### Health Check

Check if the service is running:
```bash
curl http://localhost:8000/api/health/
```

## Scaling Considerations

For high traffic:
1. Deploy behind a load balancer (nginx/HAProxy)
2. Use Redis for session persistence
3. Increase worker count in production
4. Consider using a CDN for static assets
5. Implement rate limiting and caching

## Support

For issues or questions, please refer to the documentation or contact the development team.
# AI Travel Booking Assistant

A modern AI-powered travel booking assistant built with FastAPI that helps users find hotels, plan itineraries, and make travel bookings using natural language processing.

## Features

- **AI-Powered Chat Interface**: Natural language travel planning and booking
- **Hotel Search**: Find and book hotels using Amadeus API integration
- **Travel Itinerary Planning**: Generate custom travel itineraries
- **Real-time Streaming**: Stream travel suggestions in real-time
- **Authentication**: Secure user authentication with Descope
- **REST API**: Comprehensive API endpoints for all features
- **Web Interface**: Premium booking UI with responsive design

## Tech Stack

- **Backend**: FastAPI (Python 3.12+)
- **AI/ML**: OpenAI GPT, LangChain
- **APIs**: Amadeus Travel API
- **Authentication**: Descope
- **Server**: Uvicorn
- **Package Management**: UV

## Prerequisites

Before running this application, make sure you have:

- Python 3.12 or higher
- UV package manager ([Installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- API keys for:
  - OpenAI ([Get API key](https://platform.openai.com/api-keys))
  - Amadeus ([Get credentials](https://developers.amadeus.com))
  - Descope ([Get Project ID](https://app.descope.com))

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Gen_AI
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` file with your actual API keys:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here

   # Amadeus API Configuration
   API_Key=your_amadeus_api_key_here
   API_Secret=your_amadeus_api_secret_here

   # Descope Authentication Configuration
   DESCOPE_PROJECT_ID=your_descope_project_id_here
   ```

## Running the Application

### Option 1: Using the development script (Recommended)
```bash
./start-dev.sh
```

### Option 2: Using Python directly
```bash
python run.py
```

### Option 3: Using UV
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The application will be available at:
- **Main App**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **ReDoc Documentation**: http://localhost:8001/redoc
- **Chat Interface**: http://localhost:8001/chat
- **Authentication**: http://localhost:8001/auth

## API Endpoints

### Core Endpoints
- `GET /` - Premium booking interface
- `GET /chat` - Chat interface
- `GET /auth` - Authentication page
- `GET /health` - Health check

### API Routes
- `POST /api/chat` - Chat with AI assistant
- `GET /api/hotels/search` - Search hotels
- `POST /api/travel/itinerary` - Generate travel itinerary
- `POST /api/travel/streaming` - Stream travel suggestions
- `POST /api/auth/*` - Authentication endpoints

## Project Structure

```
Gen_AI/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                 # API route handlers
│   │   ├── auth.py         # Authentication routes
│   │   ├── chat.py         # Chat API endpoints
│   │   ├── hotel.py        # Hotel search endpoints
│   │   ├── travel_itinerary.py  # Travel planning
│   │   └── travel_streaming.py  # Streaming endpoints
│   ├── core/               # Core application logic
│   │   ├── config.py       # Configuration settings
│   │   ├── logging.py      # Logging configuration
│   │   ├── prompt_templates.py  # AI prompt templates
│   │   └── prompt_utils.py # Prompt utilities
│   ├── services/           # Business logic services
│   │   ├── chat_service.py # Chat service
│   │   ├── hotel_service_backup.py  # Hotel booking logic
│   │   ├── response_hierarchy_service.py  # Response processing
│   │   └── travel_service_optimized.py   # Travel planning service
│   ├── middleware/         # Custom middleware
│   ├── templates/          # HTML templates
│   └── static/            # Static files
├── run.py                  # Application runner
├── start-dev.sh           # Development startup script
├── pyproject.toml         # Project dependencies
├── docker-compose.yml     # Docker configuration
├── Dockerfile             # Docker image definition
└── .env.example          # Environment variables template
```

## Development

### Running in Development Mode
The application supports hot reloading in development mode. Use any of the running options above, and the server will automatically restart when you make changes to the code.

### Environment Configuration
The application uses environment-based configuration. Key settings can be controlled via environment variables or the `.env` file.

### Logging
Application logs are written to `app.log` and console output. Log level and format can be configured through environment variables.

## Docker Support

### Using Docker Compose (Recommended)
```bash
docker-compose up --build
```

### Using Docker directly
```bash
# Build the image
docker build -t ai-travel-assistant .

# Run the container
docker run -p 8001:8001 --env-file .env ai-travel-assistant
```

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required API keys are set in your `.env` file
2. **Port Already in Use**: Change the port in `run.py` or kill the process using port 8001
3. **UV Not Found**: Install UV package manager following their installation guide
4. **Python Version**: Ensure you're using Python 3.12 or higher

### Checking Application Status
- Visit http://localhost:8001/health for application health status
- Check `app.log` for detailed application logs
- Use http://localhost:8001/docs for interactive API testing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the logs in `app.log`
- Visit the API documentation at `/docs`
- Review the troubleshooting section above
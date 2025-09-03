# Flight Booking Agent - AI-Powered Flight Search Assistant

An intelligent flight booking assistant that uses OpenAI's GPT-4o-mini and Amadeus APIs to help users find and analyze flight options through natural language queries.

## 🚀 Features

- **Natural Language Processing**: Ask questions in plain English about flights
- **Real-time Flight Search**: Fetches live flight data from Amadeus API
- **Intelligent Analysis**: GPT-4o-mini analyzes and presents the best flight options
- **Interactive Chat Interface**: Continuous conversation for refining searches
- **Comprehensive Flight Details**: Prices, airlines, timings, and routes

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key with GPT-4o-mini access
- Amadeus API credentials (Client ID and Secret)
- pip package manager

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Gen_AI
```

### 2. Install Required Packages

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install python-dotenv langchain langchain-experimental langchain-openai openai amadeus pandas tabulate
```

### 3. Set Up Environment Variables

Create a `.env` file in the project root with your API credentials:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Amadeus API Configuration
API_Key=your_amadeus_client_id
API_Secret=your_amadeus_client_secret
```

**Important**: Never commit your `.env` file to version control!

## 🔑 Getting API Keys

### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API keys section
4. Create a new API key
5. Ensure you have credits/billing set up for GPT-4o-mini access

### Amadeus API Credentials
1. Visit [Amadeus for Developers](https://developers.amadeus.com)
2. Create a free account
3. Create a new app in the dashboard
4. Copy your Client ID and Client Secret
5. Note: Test environment is free with limited calls

## 💻 Usage

### Running the Interactive Chat

```bash
python llm_script.py
```

The system will:
1. Start an interactive chat session
2. Wait for your flight-related query
3. Extract flight details from your query
4. Search for flights using Amadeus API
5. Analyze results with GPT-4o-mini
6. Present the best options

### Example Queries

- "Find me the cheapest flights from Delhi to Mumbai on March 15, 2025"
- "Show flights from New York to London next Friday"
- "What are the morning flights from Bangalore to Chennai tomorrow?"
- "I need to fly from Paris to Rome on December 25th"

### Sample Output

```
Enter your query: Find cheapest flights from Delhi to Mumbai on October 3, 2025

Query: System Prompt: You are an assistant that helps to answer queries...
Answer: The cheapest flights from Delhi to Mumbai on October 3, 2025:

| Airline | Departure | Arrival | Price |
|---------|-----------|---------|-------|
| AIR INDIA | 21:10 | 23:35 | EUR 57.89 |
| AIR INDIA | 12:15 | 14:35 | EUR 61.04 |
```

## 📁 Project Structure

```
Gen_AI/
├── .env                    # API credentials (create this)
├── requirements.txt        # Python dependencies
├── llm_script.py          # Main chat interface
├── data_script.py         # Flight search & data processing
├── test_integration.py    # Test script for API verification
└── README.md              # This file
```

## 🧪 Testing Your Setup

Run the test script to verify all APIs are working:

```bash
python test_integration.py
```

This will test:
- OpenAI API connection
- Amadeus API authentication
- Flight search functionality
- Data processing pipeline

## 🐛 Troubleshooting

### Common Issues & Solutions

#### 1. OpenAI API Errors

**Error**: `insufficient_quota`
- **Solution**: Add billing/payment method to your OpenAI account

**Error**: `model_not_found`
- **Solution**: Ensure you have access to GPT-4o-mini model

#### 2. Amadeus API Errors

**Error**: `[401] Unauthorized`
- **Solution**: Check your API_Key and API_Secret in `.env`

**Error**: `[429] Too Many Requests`
- **Solution**: You've hit rate limits. Wait and retry or upgrade your Amadeus account

#### 3. Module Import Errors

**Error**: `ModuleNotFoundError`
- **Solution**: Install missing packages:
```bash
pip install langchain langchain-experimental langchain-openai amadeus pandas
```

#### 4. No Flights Found

- Ensure date is in the future (not past)
- Use YYYY-MM-DD format for dates
- Verify airport codes are valid (e.g., DEL, BOM, JFK)

## 🔧 Configuration Options

### Modify Search Parameters

In `data_script.py`, you can adjust:

```python
# Maximum number of flight results
max=10  # Line 99

# Model selection
model="gpt-4o-mini"  # Line 67
```

### Adjust LLM Response Style

In `data_script.py`, modify the prompt at line 161:

```python
main_prompt = f"""
    "You are an assistant that helps to answer queries..."
"""
```

## 📊 API Limits

### Free Tier Limits

**Amadeus Test Environment:**
- 500 API calls per month
- Limited to test data after quota
- No real bookings possible

**OpenAI:**
- Depends on your billing plan
- GPT-4o-mini is more cost-effective than GPT-4

## 🚦 Exit Commands

- Type `quit` to exit the chat interface
- Use `Ctrl+C` to force stop the program

## 📝 Notes

- Flight prices are returned in EUR by default
- The system searches for direct and connecting flights
- Results are limited to 10 flights to optimize performance
- All times are shown in local timezone of departure/arrival

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Verify your API credentials
3. Ensure all dependencies are installed
4. Check API service status pages

## ⚠️ Security Notice

- Never share your API keys
- Add `.env` to `.gitignore`
- Rotate keys regularly
- Use environment variables for production
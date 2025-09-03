# Quick Start Guide

## 🚀 Run in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Create `.env` File
```env
OPENAI_API_KEY=<your_openai_key>
API_Key=<your_amadeus_client_id>
API_Secret=<your_amadeus_client_secret>
```

### Step 3: Test Setup
```bash
python test_integration.py
```

### Step 4: Start Chatting
```bash
python llm_script.py
```

## 📝 Example Session

```
$ python llm_script.py

Enter your query (or type 'quit' to exit): Find cheapest flights from Delhi to Mumbai tomorrow

Extracting fields from Query
*********************************************************************
Information extracted: 
- Origin: DEL
- Destination: BOM  
- Date: 2025-09-04
- Adults: 1
*********************************************************************

Query: Find cheapest flights from Delhi to Mumbai tomorrow
Answer: The cheapest flights are:
1. Air India - EUR 57.89 - Departs 21:10
2. Air India - EUR 61.04 - Departs 12:15

Enter your query (or type 'quit' to exit): quit
Exiting chat. Goodbye!
```

## ⚡ Common Commands

| Command | Description |
|---------|-------------|
| `python llm_script.py` | Start the flight search chat |
| `python test_integration.py` | Test API connections |
| `quit` | Exit the application |

## 🔍 Query Examples

1. **Basic Search**: "Flights from London to Paris on January 15"
2. **Cheapest Options**: "Find cheapest flights Delhi to Mumbai next week"
3. **Time Specific**: "Morning flights from NYC to Boston tomorrow"
4. **Flexible**: "Any flights from Berlin to Rome in March"

## ❓ Need Help?

- Check if `.env` file exists with correct keys
- Ensure Python 3.8+ is installed
- Verify internet connection
- See full README.md for detailed troubleshooting
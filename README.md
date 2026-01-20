# QR Code Research Project

A research system for collecting and analyzing QR codes found in the wild. Submit QR code photos via SMS, automatically extract location data, decode the QR content, safely browse destinations, capture screenshots, and classify the type of content with AI assistance.

## Features

- **SMS-based submission**: Text QR code photos to a phone number for instant processing
- **Duplicate detection**: Automatically identifies repeat QR codes while logging each sighting location
- **EXIF extraction**: Captures GPS coordinates, timestamp, and device metadata
- **Safe browsing**: Navigates to QR destinations in isolated browser environment
- **AI classification**: Uses Claude to categorize QR codes (promotional, malicious, etc.)
- **Automatic screenshots**: Captures landing page images for visual analysis
- **Cost optimization**: Skips re-analysis of duplicates to minimize API costs
- **SQLite database**: Stores all data locally for research and analysis

## Project Structure

```
qr-research/
├── app.py              # Flask webhook server (main entry point)
├── processor.py        # EXIF extraction and QR decoding
├── safe_browser.py     # Isolated web browsing with Playwright
├── classifier.py       # AI classification with Claude API
├── database.py         # SQLite database models and operations
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (create from .env.example)
├── data/
│   ├── images/         # Original QR code photos
│   ├── screenshots/    # Landing page screenshots
│   └── qr_research.db  # SQLite database
└── README.md
```

## Prerequisites

- Python 3.9+
- Twilio account (for SMS/MMS reception)
- Ngrok account (for local webhook exposure)
- Anthropic API key (optional, for AI classification)
- Windows/Linux/macOS

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
cd "QR Code/qr-research"
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required: Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Optional: Claude API for classification
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# Required: Ngrok for webhooks
NGROK_AUTH_TOKEN=your_ngrok_token_here

# Optional: Customize settings
FLASK_SECRET_KEY=random-secret-key-change-this
FLASK_PORT=5000
```

### 3. Set Up Twilio

1. Create account at [twilio.com](https://www.twilio.com/try-twilio)
2. Get a phone number with SMS/MMS capabilities
3. Copy Account SID and Auth Token from console
4. Add to `.env` file

### 4. Set Up Ngrok

1. Create account at [ngrok.com](https://dashboard.ngrok.com/signup)
2. Get auth token from dashboard
3. Install ngrok: `npm install -g ngrok` or download from website
4. Add auth token to `.env`

### 5. Get Claude API Key (Optional)

1. Create account at [console.anthropic.com](https://console.anthropic.com/)
2. Generate API key
3. Add to `.env`

Note: The system works without Claude API, but classification will be disabled.

## Running the System

### 1. Start the Flask Server

```bash
python app.py
```

You should see:
```
🚀 Starting QR Research Server
📞 Twilio Number: +1234567890
🌐 Listening on http://0.0.0.0:5000
```

### 2. Expose Local Server with Ngrok

In a separate terminal:

```bash
ngrok http 5000
```

Copy the HTTPS forwarding URL (e.g., `https://abc123.ngrok.io`)

### 3. Configure Twilio Webhook

1. Go to Twilio Console > Phone Numbers
2. Select your phone number
3. Under "Messaging", set:
   - "A MESSAGE COMES IN" webhook to: `https://your-ngrok-url.ngrok.io/webhook/sms`
   - Method: HTTP POST
4. Save configuration

### 4. Test the System

1. Send a photo of a QR code via MMS to your Twilio number
2. Watch the console for processing logs
3. Receive SMS response with analysis results

## Usage

### Submitting a QR Code

1. Take a photo of a QR code with your phone
2. Send the photo via MMS to your Twilio number
3. Wait 10-30 seconds for processing
4. Receive SMS with results:

```
QR Code Processed!

NEW QR CODE

Content: https://example.com

Location: 40.758896, -73.985130

Type: PROMOTIONAL
Confidence: 92%

Site: Example Company - Product Page

Total sightings: 1x
```

### For Duplicate QR Codes

```
QR Code Processed!

DUPLICATE (found 3x)

Content: https://example.com
...
Total sightings: 3x
```

Each duplicate sighting still logs the new location and timestamp.

### Debug Mode (No Logging)

To test QR codes without saving to the database (useful for debugging or testing suspicious QR codes):

1. Send the QR code photo via MMS
2. Include "no log" (case insensitive) in the message body

Example: Send the image with text "no log" or "No Log" or "testing this - NO LOG"

The system will:
- Still analyze the QR code fully
- Browse the URL and capture screenshot
- Classify with AI (if enabled)
- Send you the results
- **NOT save anything to the database**

Response will start with:
```
[DEBUG MODE - NOT SAVED]

QR Code Analyzed:

Content: https://example.com
...
```

This is perfect for:
- Testing the system without polluting research data
- Analyzing suspicious QR codes you don't want in your dataset
- Debugging URL navigation issues
- Verifying classification accuracy

## Data Analysis

### Database Schema

The system stores data in SQLite with two main tables:

**qr_codes**: Unique QR code records
- `content_hash`: SHA256 hash for duplicate detection
- `qr_content`: The actual QR code content
- `times_found`: Number of sightings
- `classification`: AI-assigned category
- `is_malicious`: Security flag

**qr_sightings**: Individual sightings
- `latitude/longitude`: GPS coordinates
- `timestamp`: When it was found
- `image_path`: Original photo
- `screenshot_path`: Landing page screenshot

### Accessing the Database

```python
from database import DatabaseManager

db = DatabaseManager()

# Get statistics
stats = db.get_statistics()
print(f"Total unique QR codes: {stats['total_unique_qr_codes']}")
print(f"Total sightings: {stats['total_sightings']}")
print(f"Malicious: {stats['malicious_count']}")

# Query all QR codes
from database import QRCode
session = db.Session()
qr_codes = session.query(QRCode).all()
for qr in qr_codes:
    print(f"{qr.qr_content} - found {qr.times_found}x")
session.close()
```

### Web Dashboard

Visit `http://localhost:5000` in your browser to see basic statistics.

## Configuration Options

Edit `config.py` for advanced settings:

- `BROWSER_TIMEOUT`: How long to wait for pages to load (default: 30s)
- `SKIP_CLASSIFICATION_FOR_DUPLICATES`: Save costs by not re-classifying (default: True)
- `CLASSIFICATION_CONFIDENCE_THRESHOLD`: Flag items below this for review (default: 0.7)
- `MAX_SCREENSHOT_SIZE`: Resize screenshots to save space (default: 1280x720)

## Cost Optimization

The system is designed to minimize costs:

1. **Local hosting**: No server costs (runs on your machine)
2. **Twilio pay-as-you-go**: ~$0.0075 per MMS received, ~$0.0079 per SMS sent
3. **Claude API usage**: Only called for new QR codes (duplicates skipped)
4. **Image compression**: Screenshots optimized to reduce storage
5. **SQLite database**: Free, no database hosting costs

**Estimated costs for 100 QR submissions:**
- 100 MMS received: ~$0.75
- 100 SMS responses: ~$0.79
- ~50 unique QR codes × Claude API calls: ~$0.30
- **Total: ~$1.84**

## Security Features

- Isolated browser environment (Playwright)
- No automatic download execution
- URL safety pre-checks (suspicious TLDs, IP addresses, etc.)
- Malicious content flagging
- All browsing sandboxed and logged

## Troubleshooting

### "No QR code found in image"
- Ensure the QR code is clearly visible and in focus
- Try better lighting
- Make sure the entire QR code is in frame

### "Processing error"
- Check console logs for detailed error messages
- Verify Playwright is installed: `playwright install chromium`
- Check that all environment variables are set

### SMS not received
- Verify Twilio webhook URL is correct
- Check ngrok is still running
- Look for errors in Flask console

### Classification not working
- Verify `ANTHROPIC_API_KEY` is set in `.env`
- Check API key is valid
- System works without classification (just won't categorize)

## Future Enhancements

Potential additions for the research project:

- [ ] Web dashboard for data visualization
- [ ] Export data to CSV/JSON for analysis
- [ ] Interactive map of QR code locations
- [ ] Bulk analysis scripts
- [ ] Machine learning for pattern detection
- [ ] Multi-language QR code support
- [ ] Batch processing mode
- [ ] API endpoint for programmatic access

## License

This is a research project. Use responsibly and ethically. Always obtain permission before scanning QR codes in private spaces.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review console logs for detailed errors
3. Verify all prerequisites are installed
4. Check that environment variables are set correctly

---

Built with Flask, Playwright, Claude AI, and Twilio

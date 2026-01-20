# Quick Setup Guide

Follow these steps to get the QR Research Project running.

## Step 1: Install Python Dependencies

```bash
cd "QR Code/qr-research"

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Step 2: Create Configuration File

```bash
# Copy example to actual config
cp .env.example .env
```

Now edit `.env` file - you'll fill this in as you go through the next steps.

## Step 3: Set Up Twilio (Required)

### Get Twilio Account
1. Go to [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for free trial ($15 credit)
3. Verify your phone number

### Get a Phone Number
1. In Twilio Console, go to "Phone Numbers" > "Buy a number"
2. Select your country
3. Check "SMS" and "MMS" capabilities
4. Buy the number (uses trial credit)

### Get Credentials
1. From Twilio Console home
2. Copy "Account SID"
3. Copy "Auth Token"
4. Copy your phone number (format: +1234567890)

### Add to .env file
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

## Step 4: Set Up Ngrok (Required)

### Install Ngrok
Option A: Via npm
```bash
npm install -g ngrok
```

Option B: Download from [ngrok.com/download](https://ngrok.com/download)

### Get Auth Token
1. Create account at [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)
2. Go to "Your Authtoken" page
3. Copy the token

### Add to .env file
```env
NGROK_AUTH_TOKEN=your_ngrok_token_here
```

### Authenticate Ngrok
```bash
ngrok config add-authtoken your_ngrok_token_here
```

## Step 5: Set Up Claude API (Optional)

This enables AI classification. Skip if you want to start without it.

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up / log in
3. Go to "API Keys"
4. Create new key
5. Copy the key

### Add to .env file
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

## Step 6: Start the System

### Terminal 1: Start Flask Server
```bash
# Make sure venv is activated
python app.py
```

You should see:
```
🚀 Starting QR Research Server
📞 Twilio Number: +1234567890
🌐 Listening on http://0.0.0.0:5000
```

### Terminal 2: Start Ngrok
```bash
ngrok http 5000
```

You should see:
```
Forwarding    https://abc123.ngrok.io -> http://localhost:5000
```

Copy that HTTPS URL (e.g., `https://abc123.ngrok.io`)

## Step 7: Configure Twilio Webhook

1. Go to Twilio Console > Phone Numbers > Manage > Active numbers
2. Click your phone number
3. Scroll to "Messaging Configuration"
4. Under "A MESSAGE COMES IN":
   - Set webhook to: `https://your-ngrok-url.ngrok.io/webhook/sms`
   - Set method to: `HTTP POST`
5. Click "Save"

## Step 8: Test It!

1. Take a photo of any QR code
2. Send it via text message to your Twilio number
3. Watch the Flask console for processing logs
4. Wait 10-30 seconds
5. You should receive an SMS response with the results!

### Testing in Debug Mode

For your first test, you may want to use debug mode to avoid saving test data:

1. Take a photo of a QR code
2. Send it via MMS with the text "no log"
3. System will analyze but NOT save to database
4. Response will start with `[DEBUG MODE - NOT SAVED]`

This is useful for testing and won't corrupt your research database!

## Verification Checklist

- [ ] Python dependencies installed
- [ ] Playwright chromium browser installed
- [ ] `.env` file created with all credentials
- [ ] Flask server running
- [ ] Ngrok running and showing HTTPS URL
- [ ] Twilio webhook configured with ngrok URL
- [ ] Test SMS sent and response received

## Common Issues

### "ModuleNotFoundError"
```bash
# Make sure venv is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall requirements
pip install -r requirements.txt
```

### "Playwright browser not found"
```bash
playwright install chromium
```

### "Missing required config"
Check that your `.env` file has all required fields filled in.

### "No response from SMS"
1. Check Flask console for errors
2. Verify ngrok is running
3. Verify Twilio webhook URL is correct (should match ngrok URL)
4. Check Twilio console > Monitor > Logs for error details

### Ngrok session expired
Free ngrok URLs expire after 2 hours. When this happens:
1. Restart ngrok (get new URL)
2. Update Twilio webhook with new URL

## Cost Estimates

**Twilio Trial**: $15 credit
- Each MMS received: ~$0.0075
- Each SMS sent: ~$0.0079
- ~950 QR submissions on trial credit

**Claude API**: Pay as you go
- ~$0.006 per classification
- Only charges for new (non-duplicate) QR codes

**Total**: Very cheap for research purposes!

## Next Steps

Once everything works:
1. Start collecting QR codes in the wild
2. Monitor the web dashboard at `http://localhost:5000`
3. Query the database for analysis (see README.md)
4. Consider adding custom analysis scripts

## Getting Help

If stuck:
1. Check Flask console logs
2. Check Twilio console error logs
3. Review README.md troubleshooting section
4. Verify all environment variables in `.env`

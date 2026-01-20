"""
Flask webhook server for receiving Twilio MMS messages.
Main entry point for the QR research application.
"""
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import requests
import os
from config import Config
from database import DatabaseManager
from processor import ImageProcessor, save_uploaded_image
from safe_browser import SafeBrowser
from classifier import QRClassifier
import validators

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY

# Initialize database
db = DatabaseManager(Config.DATABASE_PATH)

# Initialize Twilio client for sending responses
twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

# Initialize browser and classifier (only if configured)
safe_browser = SafeBrowser()
classifier = QRClassifier() if Config.is_classification_enabled() else None


@app.route('/webhook/sms', methods=['POST'])
def receive_sms():
    """
    Webhook endpoint for Twilio MMS messages.
    Receives QR code images and processes them.
    """
    print("\n=== Received MMS ===")

    # Get sender info
    from_number = request.form.get('From')
    num_media = int(request.form.get('NumMedia', 0))
    message_body = request.form.get('Body', '').strip()

    # Check for debug mode (no logging)
    debug_mode = 'no log' in message_body.lower()

    print(f"From: {from_number}")
    print(f"Media count: {num_media}")
    if debug_mode:
        print("🔍 DEBUG MODE: Data will not be saved to database")

    if num_media == 0:
        # No image attached
        return send_sms_response(from_number, "Please send an image of a QR code!")

    try:
        # Process each attached image
        for i in range(num_media):
            media_url = request.form.get(f'MediaUrl{i}')
            media_content_type = request.form.get(f'MediaContentType{i}')

            print(f"Processing media {i+1}: {media_url}")

            # Download the image
            response = requests.get(media_url)
            if response.status_code == 200:
                # Save image
                filename = f"qr_submission_{from_number.replace('+', '')}_{i}.jpg"
                image_path = save_uploaded_image(response.content, filename)
                print(f"Saved image: {image_path}")

                # Process the image
                result = process_qr_submission(image_path, from_number, debug_mode=debug_mode)

                # Send response SMS
                if result['success']:
                    send_result_sms(from_number, result)
                else:
                    send_sms_response(from_number, f"Error: {result['error']}")

        # Return empty TwiML response
        resp = MessagingResponse()
        return Response(str(resp), mimetype='application/xml')

    except Exception as e:
        print(f"Error processing MMS: {e}")
        send_sms_response(from_number, f"Processing error: {str(e)}")
        resp = MessagingResponse()
        return Response(str(resp), mimetype='application/xml')


def process_qr_submission(image_path, from_number, debug_mode=False):
    """
    Main processing pipeline for QR code submission.

    Args:
        image_path: Path to the QR code image
        from_number: Phone number of submitter
        debug_mode: If True, analyzes QR but doesn't save to database

    Returns result dict with success status and data.
    """
    try:
        # Step 1: Extract EXIF and decode QR
        processor = ImageProcessor(image_path)
        data = processor.process()

        if not data['qr_codes']:
            return {
                'success': False,
                'error': 'No QR code found in image',
                'debug_mode': debug_mode
            }

        # For now, handle first QR code (we can enhance to handle multiple later)
        qr_data = data['qr_codes'][0]
        qr_content = qr_data['data']

        print(f"QR Content: {qr_content}")

        # Step 2 & 3: Handle database operations (or skip in debug mode)
        location = data['exif']['location']

        if debug_mode:
            # Debug mode: Create mock objects but don't save to database
            print("🔍 DEBUG MODE: Skipping database operations")

            # Create a mock QR code object with the data we'd normally get from DB
            class MockQRCode:
                def __init__(self, content):
                    self.id = 'debug'
                    self.qr_content = content
                    self.content_hash = db.hash_qr_content(content)
                    self.times_found = 0
                    self.classification = None
                    self.confidence_score = None
                    self.is_malicious = False
                    self.manual_review = False
                    self.destination_url = None
                    self.final_url = None
                    self.site_title = None

            qr_code = MockQRCode(qr_content)
            is_duplicate = False
            sighting = None
        else:
            # Normal mode: Save to database
            qr_code, is_duplicate = db.find_or_create_qr(qr_content)
            print(f"Duplicate: {is_duplicate} (found {qr_code.times_found}x)")

            # Record this sighting
            sighting = db.add_sighting(
                qr_code_id=qr_code.id,
                latitude=location['latitude'] if location else None,
                longitude=location['longitude'] if location else None,
                location_accuracy=location['accuracy'] if location else None,
                timestamp=data['exif']['timestamp'],
                image_path=image_path,
                device_model=data['exif']['device'],
                submission_phone=from_number,
                submission_method='sms'
            )

        # Step 4: Perform analysis (always happens, even in debug mode)
        browse_result = None
        classification_result = None

        # In debug mode, always analyze. In normal mode, skip duplicates if configured
        should_analyze = debug_mode or (not is_duplicate or not Config.SKIP_CLASSIFICATION_FOR_DUPLICATES)

        if should_analyze and validators.url(qr_content):
            print("Performing full analysis (browsing + classification)...")

            # Check URL safety first
            is_safe, warnings = safe_browser.check_url_safety(qr_content)
            if warnings:
                print(f"Safety warnings: {', '.join(warnings)}")

            # Navigate to URL and capture screenshot
            browse_result = safe_browser.navigate_and_capture(qr_content, qr_code.id)

            if browse_result['success']:
                if debug_mode:
                    # Debug mode: Just store in memory
                    qr_code.destination_url = browse_result.get('destination_url')
                    qr_code.final_url = browse_result.get('final_url')
                    qr_code.site_title = browse_result.get('title')
                else:
                    # Normal mode: Update database
                    db.update_qr_destination(
                        qr_code.id,
                        browse_result.get('destination_url'),
                        browse_result.get('final_url'),
                        browse_result.get('title')
                    )

                    # Update sighting with screenshot path
                    if browse_result.get('screenshot_path'):
                        from sqlalchemy import update
                        from database import QRSighting
                        session = db.Session()
                        session.execute(
                            update(QRSighting)
                            .where(QRSighting.id == sighting.id)
                            .values(screenshot_path=browse_result['screenshot_path'])
                        )
                        session.commit()
                        session.close()

                # Classify using AI (if enabled)
                if classifier:
                    print("Classifying with AI...")
                    classification_result = classifier.classify(
                        url=qr_content,
                        page_title=browse_result.get('title'),
                        page_preview=browse_result.get('page_preview'),
                        screenshot_path=browse_result.get('screenshot_path'),
                        warnings=warnings
                    )

                    if debug_mode:
                        # Debug mode: Just store in memory
                        qr_code.classification = classification_result['category']
                        qr_code.confidence_score = classification_result['confidence']
                        qr_code.is_malicious = classification_result['is_malicious']
                        qr_code.manual_review = classification_result['confidence'] < 0.7
                    else:
                        # Normal mode: Update database
                        db.update_qr_classification(
                            qr_code.id,
                            classification_result['category'],
                            classification_result['confidence'],
                            classification_result['is_malicious']
                        )

                    print(f"Classified as: {classification_result['category']} "
                          f"({classification_result['confidence']:.2%} confidence)")
            else:
                print(f"Browse failed: {browse_result.get('error')}")
        elif not validators.url(qr_content):
            print(f"Non-URL QR code content (phone, text, etc.): {qr_content[:50]}")

        # Refresh qr_code object to get updated data (only in normal mode)
        if not debug_mode:
            from database import QRCode
            session = db.Session()
            qr_code = session.query(QRCode).get(qr_code.id)
            session.close()

        return {
            'success': True,
            'qr_code': qr_code,
            'is_duplicate': is_duplicate,
            'sighting': sighting,
            'location': location,
            'browse_result': browse_result,
            'classification': classification_result,
            'debug_mode': debug_mode
        }

    except Exception as e:
        print(f"Processing error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def send_result_sms(to_number, result):
    """Send detailed results back via SMS"""
    qr_code = result['qr_code']
    is_duplicate = result['is_duplicate']
    location = result['location']
    debug_mode = result.get('debug_mode', False)

    # Build response message
    if debug_mode:
        message = "[DEBUG MODE - NOT SAVED]\n\nQR Code Analyzed:\n\n"
    else:
        message = "QR Code Processed!\n\n"

        if is_duplicate:
            message += f"DUPLICATE (found {qr_code.times_found}x)\n\n"
        else:
            message += "NEW QR CODE\n\n"

    # Show content (truncate if too long)
    content_preview = qr_code.qr_content[:80]
    if len(qr_code.qr_content) > 80:
        content_preview += "..."
    message += f"Content: {content_preview}\n\n"

    # Show destination if it's a URL
    if qr_code.final_url and qr_code.final_url != qr_code.qr_content:
        message += f"Redirects to: {qr_code.final_url[:60]}\n\n"

    # Show location
    if location:
        message += f"Location: {location['latitude']:.6f}, {location['longitude']:.6f}\n\n"

    # Show classification
    if qr_code.classification:
        message += f"Type: {qr_code.classification.upper()}\n"
        if qr_code.confidence_score:
            message += f"Confidence: {qr_code.confidence_score:.0%}\n"

        if qr_code.is_malicious:
            message += "\nWARNING: FLAGGED AS MALICIOUS!\n"
        elif qr_code.manual_review:
            message += "\nFlagged for manual review\n"

    # Show page title if available
    if qr_code.site_title:
        title_preview = qr_code.site_title[:60]
        if len(qr_code.site_title) > 60:
            title_preview += "..."
        message += f"\nSite: {title_preview}\n"

    # Show sightings count (only in normal mode)
    if not debug_mode:
        message += f"\nTotal sightings: {qr_code.times_found}x"

    send_sms_response(to_number, message)


def send_sms_response(to_number, message):
    """Send SMS message via Twilio"""
    try:
        twilio_client.messages.create(
            body=message,
            from_=Config.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        print(f"Sent SMS to {to_number}")
    except Exception as e:
        print(f"Error sending SMS: {e}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    stats = db.get_statistics()
    return {
        'status': 'healthy',
        'database': stats
    }


@app.route('/', methods=['GET'])
def index():
    """Simple home page"""
    stats = db.get_statistics()
    return f"""
    <html>
        <head><title>QR Research Project</title></head>
        <body style="font-family: monospace; padding: 40px;">
            <h1>📱 QR Code Research Project</h1>
            <p>Send QR code images via SMS to {Config.TWILIO_PHONE_NUMBER}</p>

            <h2>Statistics</h2>
            <ul>
                <li>Unique QR Codes: {stats['total_unique_qr_codes']}</li>
                <li>Total Sightings: {stats['total_sightings']}</li>
                <li>Malicious: {stats['malicious_count']}</li>
                <li>Needs Review: {stats['needs_manual_review']}</li>
            </ul>

            <p><a href="/health">Health Check</a></p>
        </body>
    </html>
    """


if __name__ == '__main__':
    # Validate configuration
    if not Config.validate():
        print("\n⚠️  Missing required configuration!")
        print("Please copy .env.example to .env and fill in your credentials.\n")
        exit(1)

    print("\n🚀 Starting QR Research Server")
    print(f"📞 Twilio Number: {Config.TWILIO_PHONE_NUMBER}")
    print(f"🌐 Listening on http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print("\nWebhook URL: http://your-ngrok-url/webhook/sms\n")

    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=True
    )

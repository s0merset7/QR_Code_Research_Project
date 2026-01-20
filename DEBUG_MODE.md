# Debug Mode Feature

## Overview

Debug Mode allows you to analyze QR codes without saving any data to the database. This is useful for testing, debugging, or analyzing suspicious QR codes without polluting your research dataset.

## How to Use

Send a QR code photo via MMS with "no log" (case insensitive) anywhere in the message text.

### Examples

All of these activate debug mode:
- `no log`
- `No Log`
- `NO LOG`
- `Testing this QR - no log`
- `no log - suspicious QR code`

## What Happens in Debug Mode

### Still Performed:
- ✅ Image is saved temporarily
- ✅ EXIF data extracted (GPS, timestamp, device)
- ✅ QR code decoded
- ✅ URL safety checks
- ✅ Safe browsing and screenshot capture
- ✅ AI classification (if enabled)
- ✅ Full SMS response sent to you

### Skipped:
- ❌ No database entries created
- ❌ QR code not saved to `qr_codes` table
- ❌ Sighting not saved to `qr_sightings` table
- ❌ No duplicate detection check
- ❌ Statistics not affected

## Response Format

Debug mode responses are clearly marked:

```
[DEBUG MODE - NOT SAVED]

QR Code Analyzed:

Content: https://example.com

Location: 40.758896, -73.985130

Type: PROMOTIONAL
Confidence: 92%

Site: Example Company - Product Page
```

Note: No "Total sightings" counter in debug mode since nothing is saved.

## Use Cases

### 1. Initial System Testing
Test that everything works before collecting real research data:
```
Send: Photo + "no log"
```

### 2. Suspicious QR Codes
Analyze potentially malicious QR codes safely without adding to dataset:
```
Send: Photo + "no log - checking if malicious"
```

### 3. Personal QR Codes
Test your own QR codes without skewing research data:
```
Send: Photo + "no log - my business card"
```

### 4. Debugging Issues
Troubleshoot URL navigation or classification problems:
```
Send: Photo + "no log - testing navigation issue"
```

### 5. Classification Verification
Test if AI classification is working correctly:
```
Send: Photo + "no log - verifying classifier"
```

## Console Output

When debug mode is active, you'll see in the Flask console:

```
=== Received MMS ===
From: +1234567890
Media count: 1
🔍 DEBUG MODE: Data will not be saved to database
Saved image: data/images/qr_submission_1234567890_0.jpg
QR Content: https://example.com
🔍 DEBUG MODE: Skipping database operations
Performing full analysis (browsing + classification)...
Classifying with AI...
Classified as: promotional (0.92 confidence)
```

## Technical Details

### Implementation

When "no log" is detected in the message body:

1. A `debug_mode=True` flag is passed through the processing pipeline
2. A `MockQRCode` object is created in memory instead of database entry
3. All analysis proceeds normally
4. Results are stored only in the mock object
5. Response is sent with debug mode header
6. No database transactions occur

### Code Flow

```python
# Detection
message_body = request.form.get('Body', '').strip()
debug_mode = 'no log' in message_body.lower()

# Processing
if debug_mode:
    # Create mock objects, skip database
    qr_code = MockQRCode(qr_content)
else:
    # Normal database operations
    qr_code, is_duplicate = db.find_or_create_qr(qr_content)
```

## Cost Implications

Debug mode has the same costs as normal mode:
- Twilio MMS/SMS charges still apply
- Claude API classification still runs (if enabled)
- Screenshot storage still occurs

Only saves on database operations (which are free with SQLite).

## Notes

- Images and screenshots are still saved to disk even in debug mode
- Debug mode always performs full analysis (ignores duplicate skip setting)
- Useful for testing without affecting `get_statistics()` output
- Perfect for validating system functionality before real data collection

## Examples in Practice

### Before Starting Research
```
You: [Photo of test QR] "no log"
System: [DEBUG MODE - NOT SAVED] ... Type: PROMOTIONAL ...
You: Perfect! System works. Now I'll start collecting real data.
```

### During Research
```
You: [Photo of sketchy QR] "no log - looks suspicious"
System: [DEBUG MODE - NOT SAVED] ... WARNING: FLAGGED AS MALICIOUS!
You: Good to know, but didn't add to my legitimate research data.
```

### Quality Control
```
You: [Photo of known QR] "no log - verifying classification"
System: [DEBUG MODE - NOT SAVED] ... Type: PROMOTIONAL ...
You: Classification looks correct!
```

---

This feature ensures your research database stays clean while still allowing full system functionality for testing and debugging purposes.

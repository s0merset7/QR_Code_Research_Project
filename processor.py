"""
Image processing pipeline: EXIF extraction and QR code decoding.
"""
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pyzbar.pyzbar import decode
import exifread
from datetime import datetime


class ImageProcessor:
    """Handles image analysis, EXIF extraction, and QR decoding"""

    def __init__(self, image_path):
        self.image_path = image_path
        self.image = Image.open(image_path)
        self.exif_data = {}
        self.location = None
        self.timestamp = None
        self.device_info = None

    def extract_exif(self):
        """Extract EXIF data including GPS coordinates"""
        try:
            # Use exifread for comprehensive EXIF extraction
            with open(self.image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            # Extract GPS coordinates
            self.location = self._parse_gps(tags)

            # Extract timestamp
            self.timestamp = self._parse_timestamp(tags)

            # Extract device info
            self.device_info = self._parse_device_info(tags)

            return {
                'location': self.location,
                'timestamp': self.timestamp,
                'device': self.device_info
            }

        except Exception as e:
            print(f"Error extracting EXIF: {e}")
            return {
                'location': None,
                'timestamp': datetime.utcnow(),
                'device': None
            }

    def _parse_gps(self, tags):
        """Parse GPS coordinates from EXIF tags"""
        try:
            # Get GPS tags
            lat = tags.get('GPS GPSLatitude')
            lat_ref = tags.get('GPS GPSLatitudeRef')
            lon = tags.get('GPS GPSLongitude')
            lon_ref = tags.get('GPS GPSLongitudeRef')

            if not all([lat, lat_ref, lon, lon_ref]):
                return None

            # Convert to decimal degrees
            lat_decimal = self._convert_to_degrees(lat)
            if lat_ref.values[0] != 'N':
                lat_decimal = -lat_decimal

            lon_decimal = self._convert_to_degrees(lon)
            if lon_ref.values[0] != 'E':
                lon_decimal = -lon_decimal

            return {
                'latitude': lat_decimal,
                'longitude': lon_decimal,
                'accuracy': 'GPS'
            }

        except Exception as e:
            print(f"Error parsing GPS: {e}")
            return None

    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates to decimal degrees"""
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)

    def _parse_timestamp(self, tags):
        """Parse image timestamp from EXIF"""
        try:
            # Try different timestamp tags
            timestamp_tags = [
                'EXIF DateTimeOriginal',
                'EXIF DateTimeDigitized',
                'Image DateTime'
            ]

            for tag_name in timestamp_tags:
                tag = tags.get(tag_name)
                if tag:
                    # Format: "YYYY:MM:DD HH:MM:SS"
                    timestamp_str = str(tag)
                    return datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')

        except Exception as e:
            print(f"Error parsing timestamp: {e}")

        # Default to current time if no EXIF timestamp
        return datetime.utcnow()

    def _parse_device_info(self, tags):
        """Extract device/camera information"""
        try:
            make = tags.get('Image Make', '')
            model = tags.get('Image Model', '')

            if make and model:
                return f"{make} {model}".strip()
            return None

        except Exception as e:
            print(f"Error parsing device info: {e}")
            return None

    def decode_qr(self):
        """
        Decode QR code from image.
        Returns list of decoded data (in case multiple QR codes in image)
        """
        try:
            decoded_objects = decode(self.image)

            results = []
            for obj in decoded_objects:
                results.append({
                    'data': obj.data.decode('utf-8'),
                    'type': obj.type,
                    'rect': obj.rect,
                    'quality': obj.quality if hasattr(obj, 'quality') else None
                })

            return results

        except Exception as e:
            print(f"Error decoding QR code: {e}")
            return []

    def process(self):
        """
        Run full processing pipeline.
        Returns dict with all extracted information.
        """
        exif_info = self.extract_exif()
        qr_codes = self.decode_qr()

        return {
            'exif': exif_info,
            'qr_codes': qr_codes,
            'image_size': self.image.size,
            'image_format': self.image.format
        }


def save_uploaded_image(file_content, filename, output_dir='data/images'):
    """
    Save uploaded image file.
    Returns the saved file path.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1] or '.jpg'
    unique_filename = f"{base_name}_{timestamp}{extension}"

    file_path = os.path.join(output_dir, unique_filename)

    with open(file_path, 'wb') as f:
        f.write(file_content)

    return file_path


if __name__ == '__main__':
    # Test with a sample image
    import sys

    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        print(f"Processing: {test_image}")

        processor = ImageProcessor(test_image)
        results = processor.process()

        print("\n=== EXIF Data ===")
        print(f"Location: {results['exif']['location']}")
        print(f"Timestamp: {results['exif']['timestamp']}")
        print(f"Device: {results['exif']['device']}")

        print("\n=== QR Codes ===")
        for i, qr in enumerate(results['qr_codes'], 1):
            print(f"QR #{i}: {qr['data']}")
    else:
        print("Usage: python processor.py <image_path>")

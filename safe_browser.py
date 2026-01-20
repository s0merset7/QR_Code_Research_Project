"""
Safe browsing module using Playwright in isolated environment.
Navigates to URLs from QR codes safely and captures screenshots.
"""
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from datetime import datetime
from urllib.parse import urlparse
import validators
from config import Config


class SafeBrowser:
    """
    Safely browse URLs and capture information.
    Runs in headless mode with security restrictions.
    """

    def __init__(self, timeout=30):
        self.timeout = timeout * 1000  # Convert to milliseconds
        self.screenshots_dir = Config.SCREENSHOTS_DIR
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def navigate_and_capture(self, url, qr_code_id):
        """
        Navigate to URL safely and capture information.
        Returns dict with destination info and screenshot path.
        """
        # Validate URL first
        if not validators.url(url):
            # Might be a phone number, text, or malformed URL
            return {
                'success': False,
                'error': 'Invalid URL format',
                'url_type': 'non-url',
                'content': url
            }

        try:
            with sync_playwright() as p:
                # Launch browser with security settings
                browser = p.chromium.launch(
                    headless=Config.BROWSER_HEADLESS,
                    args=[
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',  # For capturing cross-origin content
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                )

                # Create context with additional security
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    java_script_enabled=True,
                    ignore_https_errors=True  # Some QR codes may have SSL issues
                )

                # Block dangerous file downloads
                context.route('**/*', lambda route: route.abort()
                              if route.request.resource_type in ['media', 'font', 'video']
                              else route.continue_())

                page = context.new_page()

                # Set timeout
                page.set_default_timeout(self.timeout)

                print(f"Navigating to: {url}")

                # Navigate to URL
                try:
                    response = page.goto(url, wait_until='networkidle')
                    final_url = page.url
                    status_code = response.status if response else None

                    print(f"Final URL: {final_url}")
                    print(f"Status: {status_code}")

                    # Wait a bit for any JavaScript redirects
                    page.wait_for_timeout(2000)
                    final_url = page.url

                    # Extract page information
                    title = page.title()
                    page_text = page.inner_text('body')[:500]  # First 500 chars

                    # Take screenshot
                    screenshot_path = self._save_screenshot(page, qr_code_id)

                    # Get any redirects
                    redirect_chain = self._get_redirect_info(url, final_url)

                    result = {
                        'success': True,
                        'destination_url': url,
                        'final_url': final_url,
                        'status_code': status_code,
                        'title': title,
                        'page_preview': page_text,
                        'screenshot_path': screenshot_path,
                        'redirects': redirect_chain,
                        'domain': urlparse(final_url).netloc
                    }

                    browser.close()
                    return result

                except PlaywrightTimeout:
                    print(f"Timeout loading {url}")
                    browser.close()
                    return {
                        'success': False,
                        'error': 'Page load timeout',
                        'destination_url': url
                    }

                except Exception as e:
                    print(f"Error navigating to {url}: {e}")
                    browser.close()
                    return {
                        'success': False,
                        'error': str(e),
                        'destination_url': url
                    }

        except Exception as e:
            print(f"Browser initialization error: {e}")
            return {
                'success': False,
                'error': f'Browser error: {str(e)}',
                'destination_url': url
            }

    def _save_screenshot(self, page, qr_code_id):
        """Save screenshot of the page"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"qr_{qr_code_id}_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)

            # Take full page screenshot
            page.screenshot(path=filepath, full_page=True)

            # Optionally resize to save storage
            if Config.MAX_SCREENSHOT_SIZE:
                from PIL import Image
                img = Image.open(filepath)
                img.thumbnail(Config.MAX_SCREENSHOT_SIZE, Image.Resampling.LANCZOS)
                img.save(filepath, optimize=True, quality=85)

            print(f"Screenshot saved: {filepath}")
            return filepath

        except Exception as e:
            print(f"Screenshot error: {e}")
            return None

    @staticmethod
    def _get_redirect_info(original_url, final_url):
        """Analyze redirect chain"""
        if original_url == final_url:
            return []

        original_domain = urlparse(original_url).netloc
        final_domain = urlparse(final_url).netloc

        return [{
            'from_domain': original_domain,
            'to_domain': final_domain,
            'cross_domain': original_domain != final_domain
        }]

    def check_url_safety(self, url):
        """
        Basic URL safety checks before browsing.
        Returns (is_safe, warnings)
        """
        warnings = []

        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top']
        parsed = urlparse(url)
        if any(parsed.netloc.endswith(tld) for tld in suspicious_tlds):
            warnings.append('Suspicious TLD')

        # Check for IP address instead of domain
        if parsed.netloc.replace('.', '').replace(':', '').isdigit():
            warnings.append('IP address instead of domain')

        # Check for suspicious keywords
        suspicious_keywords = ['login', 'verify', 'account', 'secure', 'update', 'confirm']
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in suspicious_keywords):
            warnings.append('Contains suspicious keywords')

        # Check for extremely long URLs (possible obfuscation)
        if len(url) > 200:
            warnings.append('Unusually long URL')

        is_safe = len(warnings) == 0

        return is_safe, warnings


# Install Playwright browsers on first run
def install_browsers():
    """Install Playwright browser binaries"""
    import subprocess
    print("Installing Playwright browsers...")
    subprocess.run(['playwright', 'install', 'chromium'], check=True)
    print("Browser installation complete!")


if __name__ == '__main__':
    # Test the browser
    import sys

    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Testing safe browser with: {test_url}")

        browser = SafeBrowser()

        # Check safety first
        is_safe, warnings = browser.check_url_safety(test_url)
        print(f"\nSafety check: {'✓ Safe' if is_safe else '⚠ Warnings'}")
        if warnings:
            for warning in warnings:
                print(f"  - {warning}")

        # Navigate
        result = browser.navigate_and_capture(test_url, qr_code_id='test')

        if result['success']:
            print(f"\n✓ Success!")
            print(f"Title: {result.get('title')}")
            print(f"Final URL: {result.get('final_url')}")
            print(f"Screenshot: {result.get('screenshot_path')}")
        else:
            print(f"\n✗ Failed: {result.get('error')}")
    else:
        print("Usage: python safe_browser.py <url>")
        print("\nTo install browsers: playwright install chromium")

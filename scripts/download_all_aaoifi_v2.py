"""
Download ALL available AAOIFI FAS standards from main page.
Scrape page, extract all PDF URLs, download EN+AR versions.
"""
import base64
import re
import os
import urllib.request
import urllib.parse
import time

def decode_param(encoded):
    """Decode base64 tnc_pvfw param to get file URL."""
    try:
        padded = encoded + '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.b64decode(padded).decode('utf-8')
        result = {}
        for part in decoded.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                result[key] = value
        return result
    except Exception as e:
        return {}

def extract_std_num(fname):
    """Extract standard number from filename."""
    # Try patterns like FAS-1, FAS1, Standard-3, Standard3
    patterns = [
        r'FAS[_\-\s]*(\d+)',
        r'STANDARD[_\-\s]*(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, fname, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def scrape_page_for_pdfs(url):
    """Scrape page for all PDF URLs."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        print(f"DEBUG: HTML length {len(html)}")

        pattern = r'tnc_pvfw=([^&#\s]+)'
        matches = re.findall(pattern, html)

        print(f"DEBUG: Found {len(matches)} base64 matches")

        pdf_map = {}  # std_num -> {'en': url, 'ar': url, 'fname': fname}

        for i, encoded in enumerate(matches):
            try:
                params = decode_param(encoded)
                pdf_url = params.get('file')
                if not pdf_url:
                    continue

                pdf_url = urllib.request.unquote(pdf_url)
                fname = os.path.basename(pdf_url)

                std_num = extract_std_num(fname)
                if not std_num:
                    if i < 5:
                        print(f"DEBUG: No std num for {fname[:60]}")
                    continue

                lang = params.get('lang', 'en-US')
                if std_num not in pdf_map:
                    pdf_map[std_num] = {'en': None, 'ar': None, 'fname': fname}

                if 'ar' in lang.lower():
                    pdf_map[std_num]['ar'] = pdf_url
                else:
                    pdf_map[std_num]['en'] = pdf_url

            except Exception as e:
                if i < 5:
                    print(f"DEBUG: Exception: {e}")
                pass

        return pdf_map
    except Exception as e:
        print(f"Error scraping page: {e}")
        return {}

def encode_url(url):
    """Encode URL with non-ASCII chars."""
    parsed = urllib.parse.urlparse(url)
    path_encoded = urllib.parse.quote(parsed.path, safe='/')
    query_encoded = urllib.parse.quote(parsed.query, safe='=&')
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path_encoded, parsed.params, query_encoded, parsed.fragment)
    )

def download_pdf(pdf_url, output_path, max_retries=2):
    """Download PDF with retries."""
    for attempt in range(max_retries):
        try:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True, "Skipped (exists)"

            safe_url = encode_url(pdf_url)
            req = urllib.request.Request(
                safe_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(output_path, 'wb') as f:
                    f.write(response.read())
            return True, "Downloaded"
        except Exception as e:
            if attempt == max_retries - 1:
                return False, str(e)
            time.sleep(2)
    return False, "Max retries exceeded"

def safe_print(msg):
    try:
        print(str(msg))
    except:
        print(str(msg).encode('ascii', errors='replace').decode('ascii'))

def main():
    output_dir = "D:/AI Projects/Freelance/Sabry/Mushir-Sharia-Bot/data/raw/aaoifi_standards"
    os.makedirs(output_dir, exist_ok=True)

    # Scrape main page for ALL PDF URLs
    safe_print("Scraping AAOIFI accounting standards page...")
    pdf_map = scrape_page_for_pdfs('https://aaoifi.com/accounting-standards-2/?lang=en')
    safe_print(f"Found {len(pdf_map)} standards on page\n")

    if not pdf_map:
        safe_print("ERROR: No standards found! Check debug output above.")
        return

    # Download all available standards
    success_count = 0
    fail_count = 0

    for std_num in sorted(pdf_map.keys(), key=int):
        info = pdf_map[std_num]
        safe_print(f"[FAS {std_num}] {info['fname'][:60]}")

        # EN download
        en_url = info['en']
        if en_url:
            en_output = os.path.join(output_dir, f"Standard_{std_num.zfill(2)}_EN.pdf")
            success, msg = download_pdf(en_url, en_output)
            status = "OK" if success else "FAIL"
            safe_print(f"  EN: {status} - {str(msg)[:80]}")
            if success:
                success_count += 1
            else:
                fail_count += 1
        else:
            safe_print(f"  EN: No URL found")

        # AR download
        ar_url = info['ar'] or en_url  # Fallback to EN if no AR
        ar_output = os.path.join(output_dir, f"Standard_{std_num.zfill(2)}_AR.pdf")
        if ar_url and (not os.path.exists(ar_output) or os.path.getsize(ar_output) == 0):
            success, msg = download_pdf(ar_url, ar_output)
            status = "OK" if success else "FAIL"
            safe_print(f"  AR: {status} - {str(msg)[:80]}")
        else:
            safe_print(f"  AR: Skipped (exists)")

        safe_print("")

    # Summary
    safe_print(f"\n{'='*50}")
    safe_print(f"Download complete!")
    safe_print(f"Success: {success_count}, Failed: {fail_count}")
    safe_print(f"Output: {output_dir}")
    safe_print(f"{'='*50}\n")

if __name__ == "__main__":
    main()

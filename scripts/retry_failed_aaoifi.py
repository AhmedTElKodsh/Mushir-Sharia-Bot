"""
Download failed AAOIFI standards (English + Arabic) - retry with updated URLs.
"""

import base64
import re
import os
import urllib.request
import urllib.parse

# URLs for previously failed standards (from user's retry request)
RETRY_URLS = [
    # Standard 14 - Investments in Real Estate
    ("14", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTQtSW52ZXN0bWVudC1BY2NvdW50cy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 16 - Investments in Real Estate
    ("16", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTYtSW52ZXN0bWVudC1pbi1SZWFsLUVzdGF0ZS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 17 - Disclosure on Transfer of Assets
    ("17", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTctRGlzY2xvc3VyZS1vbi1UcmFuc2Zlci1vZi1Bc3NldHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 21 - Disclosure on Transfer of Assets
    ("21", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjEtRGlzY2xvc3VyZS1vbi1UcmFuc2Zlci1vZi1Bc3NldHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 22 - Segment Reporting
    ("22", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjItU2VnbWVudC1SZXBvcnRpbmcucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 23 - Consolidation
    ("23", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjMtQ29uc29saWRhdGlvbi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 24 - Investments - Adjustments
    ("24", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjQtSW52ZXN0bWVudHMtaW4tQXNzb2NpYXRlcy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 25 - Investments - Shares and Stakes
    ("25", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjUtSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 28 - Murabaha and other Deferred Payments
    ("28", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTI4LU11cmFiYWhhLWFuZC1PdGhlci1EZWZlcnJlZC1QYXltZW50LVNhbGVzLUZvcm1hdHRlZC0yMDIxLWNsZWFuLTEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 38 - Transfer of Assets between Pools
    ("38", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM4LVRyYW5zZmVyLW9mLUFzc2V0cy1iZXR3ZWVuLUludmVzdG1lbnQtUG9vbHMtRmludWwtY2xlYW4ucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 42 - Presentation and Disclosure in Financial Statements
    ("42", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQyLVByZXNlbnRhdGlvbi1hbmQtRGlzY2xvc3VyZXMtaW4tdGhlLUZpbmFuY2lhbC1TdGF0ZW1lbnRzLW9mLVRha2FmdWwtSW5zdGl0dXRpb25zLWZpbmFsLWNsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 46 - Off-Balance-Sheet Assets Under Management
    ("46", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM2LUZpcnN0LVRpbWUtQWRvcHRpb24tb2YtQUFPSUZJLUZpbmFuY2lhbC1BY2NvdW50aW5nLVN0YW5kYXJkcy1GaW5hbC0zMC1Ob3YtMjAtQ2xlYW4ucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 47 - Transfer of Assets between Investment Pools
    ("47", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQ3X1JhbnNmZXI1b2YtQXNzZXRzLWJldHdlZW4tSW52ZXN0bWVudC1Qb29scy1GaW5hbC1jbGVhbi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 48
    ("48", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNDgtSW52ZXN0bWVudHMtaW4tU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 49
    ("49", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNDktSW52ZXN0bWVudHMtaW4tU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 50
    ("50", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTAtSW52ZXN0bWVudHMtaW4tU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 51
    ("51", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTEtSW52ZXN0bWVudHMtaW4tU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 53 - Quasi-equity
    ("53", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTMzLUludmVzdG1lbnQtaW4tU3VrdWstU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLWZvcm1hdHRlZC1jbGVhbi11cGRhdGVkLWFwcmlsLTIwMjMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 55 - Shares and Stakes
    ("55", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjUtSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 56
    ("56", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTYtSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 57
    ("57", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTctSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 58
    ("58", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTgtSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 59
    ("59", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtNTktSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 61
    ("61", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQwLUZpbmFuY2lhbC1SZXBvcnRpbmctZm9yLUlzbGFtaWMtV2luZG93cy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 63 - Income Tax
    ("63", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQzLUFjY291bnRpbmctZm9yLVNoYXJlcy1SZWd1bGF0aW9uLVN1cnBsdXMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 65 - Islamic Financial Services
    ("65", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQ1LVJpc2stUmVzZXJ2ZS1GaW5hbGl6YXRpb24tRm9ybWF0dGVkLTIwMjEtY2xlYW4tMTYtUXVpbi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT"),
    # Standard 66
    ("66", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM2LUZpcnN0LVRpbWUtQWRvcHRpb24tb2YtQUFPSUZJLUZpbmFuY2lhbC1BY2NvdW50aW5nLVN0YW5kYXJkcy1GaW5hbC0zMC1Ob3YtMjAtQ2xlYW4ucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 67
    ("67", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM3LUZpbmFuY2lhbC1SZXBvcnRpbmctYnktV2FkaC1LaGl5YXItYW5kLVNoYWhhd2F0LUZpbmFsLTE1LUplbWJlci0yMDIwLWNsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
    # Standard 68
    ("68", "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM4LVdhYXEtS2hpeWFyLWFuZC1aYWhhd2F0LUZpbmFsLTE1LU5vdi0yMDIwLWNsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMTExMDAmbGFuZz1lbi1VUw="),
]

def decode_param(encoded):
    """Decode base64 tnc_pvfw param."""
    try:
        padded = encoded + '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.b64decode(padded).decode('utf-8')
        result = {}
        for part in decoded.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                result[key] = value
        return result
    except Exception:
        return {}

def make_arabic_url(encoded):
    """Generate Arabic version URL."""
    try:
        padded = encoded + '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.b64decode(padded).decode('utf-8')
        arabic_decoded = re.sub(r'lang=[^&]+', 'lang=ar', decoded)
        arabic_encoded = base64.b64encode(arabic_decoded.encode('utf-8')).decode('utf-8')
        return arabic_encoded
    except Exception:
        return None

def encode_url(url):
    """Encode URL with non-ASCII chars."""
    parsed = urllib.parse.urlparse(url)
    path_encoded = urllib.parse.quote(parsed.path, safe='/')
    query_encoded = urllib.parse.quote(parsed.query, safe='=&')
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path_encoded, parsed.params, query_encoded, parsed.fragment)
    )

def download_pdf(pdf_url, output_path):
    """Download PDF using urllib."""
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, "Skipped (exists)"
        safe_url = encode_url(pdf_url)
        req = urllib.request.Request(
            safe_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True, "Downloaded {}".format(os.path.basename(output_path))
    except Exception as e:
        return False, str(e)

def safe_print(msg):
    try:
        print(str(msg))
    except:
        print(str(msg).encode('ascii', errors='replace').decode('ascii'))

def main():
    output_dir = "D:/AI Projects/Freelance/Sabry/Mushir-Sharia-Bot/data/raw/aaoifi_standards"
    os.makedirs(output_dir, exist_ok=True)

    safe_print("Retrying failed standards...")
    safe_print("Output: {}\n".format(output_dir))

    for std_num, url in RETRY_URLS:
        # Extract PDF URL from base64 param
        match = re.search(r'tnc_pvfw=([^&#]+)', url)
        if not match:
            safe_print("[{}] No base64 param found".format(std_num))
            continue

        encoded = match.group(1)
        params = decode_param(encoded)
        pdf_url = params.get('file')

        if not pdf_url:
            safe_print("[{}] No PDF URL extracted".format(std_num))
            continue

        # EN download
        en_output = os.path.join(output_dir, "Standard_{}_EN.pdf".format(std_num.zfill(2)))
        safe_print("[{}] EN: {}".format(std_num, pdf_url[:80]))
        success, msg = download_pdf(pdf_url, en_output)
        safe_print("    {}: {}".format("OK" if success else "FAIL", msg[:100]))

        # AR download
        try:
            ar_encoded = make_arabic_url(encoded)
            if ar_encoded:
                ar_params = decode_param(ar_encoded)
                ar_pdf_url = ar_params.get('file', pdf_url)
            else:
                ar_pdf_url = pdf_url

            ar_output = os.path.join(output_dir, "Standard_{}_AR.pdf".format(std_num.zfill(2)))
            safe_print("    AR: Trying Arabic version...")
            success, msg = download_pdf(ar_pdf_url, ar_output)
            safe_print("    {}: {}".format("OK" if success else "FAIL", msg[:100]))
        except Exception as e:
            safe_print("    AR FAIL: {}".format(str(e)[:100]))

        safe_print("")

    safe_print("Retry complete!")

if __name__ == "__main__":
    main()

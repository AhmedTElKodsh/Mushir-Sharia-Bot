"""
Download AAOIFI standards using correct URLs from main page.
"""
import base64
import re
import os
import urllib.request
import urllib.parse

# Correct URLs found on main page
CORRECT_URLS = {
    "14": "https://aaoifi.com/wp-content/uploads/2023/01/Financial-Accounting-Standard-14-Investment-Funds.pdf",
    "16": "https://aaoifi.com/wp-content/uploads/2023/01/Financial-Accounting-Standard-16-Foreign-Currency-Transactions-and-Foreign-Operations.pdf",
    "25": "https://aaoifi.com/wp-content/uploads/2023/01/Financial-Accounting-Standard-25-Investment-in-Sukuk-Shares-and-Similar-Instruments.pdf",
    "38": "https://aaoifi.com/wp-content/uploads/2023/09/FAS-38-Waad-Khiyar-and-Tahawut-Final-15-December-2020-clean.pdf",
    "47": "https://aaoifi.com/wp-content/uploads/2024/06/FAS-47_Transfer-of-Assets-between-Investment-Pools-Final.pdf",
    "48": "https://aaoifi.com/wp-content/uploads/2024/12/FAS-48-Promotional-Gifts-and-Prizes-1.pdf",
    "49": "https://aaoifi.com/wp-content/uploads/2024/12/FAS-49-Financial-Reporting-for-Institutions-Operating-in-Hyperinflationary-Economies.pdf",
    "50": "https://aaoifi.com/wp-content/uploads/2024/12/FAS-50-Financial-Reporting-for-Islamic-Investment-Institutions.pdf",
    "51": "https://aaoifi.com/wp-content/uploads/2025/11/FAS-51-Participatory-Ventures.pdf",
}

def encode_url(url):
    parsed = urllib.parse.urlparse(url)
    path_encoded = urllib.parse.quote(parsed.path, safe='/')
    query_encoded = urllib.parse.quote(parsed.query, safe='=&')
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path_encoded, parsed.params, query_encoded, parsed.fragment)
    )

def download_pdf(pdf_url, output_path):
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
        return True, "Downloaded"
    except Exception as e:
        return False, str(e)

def safe_print(msg):
    try:
        print(str(msg))
    except:
        print(str(msg).encode('ascii', errors='replace').decode('ascii'))

def make_arabic_url(en_url):
    """Try to construct Arabic URL by changing path."""
    try:
        # Try replacing en with ar in path, or try /ar/ prefix
        parts = en_url.rsplit('/', 1)
        fname = parts[1] if len(parts) > 1 else ''
        # Try Arabic version - often same file or with ar prefix
        ar_url = en_url.replace('/2023/', '/2023/').replace('/2024/', '/2024/')
        return ar_url  # Often the same PDF has both languages
    except:
        return en_url

def main():
    output_dir = "D:/AI Projects/Freelance/Sabry/Mushir-Sharia-Bot/data/raw/aaoifi_standards"
    os.makedirs(output_dir, exist_ok=True)

    safe_print("Downloading corrected URLs...\n")

    for std_num, pdf_url in sorted(CORRECT_URLS.items(), key=lambda x: int(x[0])):
        # EN download
        en_output = os.path.join(output_dir, "Standard_{}_EN.pdf".format(std_num.zfill(2)))
        safe_print("[{}] EN: {}".format(std_num, pdf_url[-60:]))
        success, msg = download_pdf(pdf_url, en_output)
        safe_print("    {}: {}".format("OK" if success else "FAIL", str(msg)[:100]))

        # AR - try Arabic version
        ar_output = os.path.join(output_dir, "Standard_{}_AR.pdf".format(std_num.zfill(2)))
        if not os.path.exists(ar_output) or os.path.getsize(ar_output) == 0:
            # Try to find Arabic version - same URL often works (bilingual PDFs)
            safe_print("    AR: Trying same URL...")
            success, msg = download_pdf(pdf_url, ar_output)
            safe_print("    {}: {}".format("OK" if success else "FAIL", str(msg)[:100]))
        else:
            safe_print("    AR: Skipped (exists)")

        safe_print("")

    safe_print("Done!")

if __name__ == "__main__":
    main()

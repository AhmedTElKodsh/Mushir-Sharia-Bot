"""
Download AAOIFI accounting standards (English + Arabic) from provided URLs.
Handles both viewer URLs (base64 param) and direct PDF links.
Uses stdlib only.
"""

import base64
import re
import os
import urllib.request
import urllib.parse

# All provided URLs (EN viewer URLs + direct PDF links)
URLS = [
    # Batch 1 (Standards 1-9)
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEvRkFTLTEtR2VuZXJhbC1QcmVzZW50YXRpb24tYW5kLURpc2Nsb3N1cmUtaW4tdGhlLUZpbmFuY2lhbC1TdGF0ZW1lbnRzLW9mLUlzbGFtaWMtQmFua3MtYW5kLUZpbmFuY2lhbC1JbnN0aXR1dGlvbnMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw==",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTEt2KfZhNi52LHYti3ZiNin2YTYpdmB2LXYp9itLdin2YTYudin2YUt2YHZii3Yp9mE2YLZiNin2KbZhS3Yp9mE2YXYp9mE2YrYqS3ZhNmE2YXYtdin2LHZgS3ZiNin2YTZhdik2LPYs9in2Kot2KfZhNmF2KfZhNmK2Kkt2KfZhNil2LPZhNin2YXZitipLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvQ29uY2VwdHVhbC1GcmFtZXdvcmstZm9yLUZpbmFuY2lhbC1SZXBvcnRpbmctYnktSXNsYW1pYy1GaW5hbmNpYWwtSW5zdGl0dXRpb25zLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2KjZitin2YYt2KfZhNmF2K3Yp9iz2KjYqS3Yp9mE2YXYp9mE2YrYqS0yLdmF2YHYp9mH2YrZhS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLdmE2YTZhdi12KfYsdmBLdmI2KfZhNmF2KTYs9iz2KfYqi3Yp9mE2YXYp9mE2YrYqS3Yp9mE2KXYs9mE2KfZhdmK2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw==",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvQUFPSUZJLUNvbmNlcHR1YWwtRnJhbWV3b3JrLWZvci1GaW5hbmNpYWwtUmVwb3J0aW5nLVJldmlzZWQtMjAyMC1GaW5hbC1jbGVhbi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2KfZhNil2LfYp9ixLdin2YTZhdmB2KfZh9mK2YXZii3ZhNmE2KrZgtix2YrYsS3Yp9mE2YXYp9mE2YrYjC3Yp9mE2LXYp9iv2LEt2LnZhi3Yo9mK2YjZgdmKLS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEvRkFTLTEtR2VuZXJhbC1QcmVzZW50YXRpb24tYW5kLURpc2Nsb3N1cmVzLWluLXRoZS1GaW5hbmNpYWwtU3RhdGVtZW50cy1fLXY3LWNsZWFuLTE3LU9jdG9iZXItMjAyMi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMy1NdWRhcmFiYS1GaW5hbmNpbmcucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw==",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTMt2KfZhNiq2YXZiNmK2YQt2KjYp9mE2YXYttin2LHYqNipLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    # Batch 2 (Standards 10-47)
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTAtSXN0aXNuYWEtYW5kLVBhcmFsbGVsLUlzdGlzbmFhLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTEwLdin2YTYp9iz2KrYtdmG2KfYuS3ZiNin2YTYp9iz2KrYtdmG2KfYuS3Yp9mE2YXZiNin2LLZii5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTItR2VuZXJhbC1QcmVzZW50YXRpb24tYW5kLURpc2Nsb3N1cmUtaW4tdGhlLUZpbmFuY2lhbC1TdGF0ZW1lbnRzLW9mLUlzbGFtaWMtSW5zdXJhbmNlLUNvbXBhbmllcy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTEyLdin2YTYpdmB2LXYp9itLdi52YYt2KPZs9iyLdiq2K3Yr9mK2K8t2YjYqtmI2LLZiti5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTMtSW52ZXN0bWVudC1BY2NvdW50cy1EZXRlcm1pbmctYW5kLUFsbG9jYXRpbmctU3VycGx1cy1vci1EZWZpY2l0LWluLVNzbGFtaWMtSW5zdXJhbmNlLUNvbXBhbmllcy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTMt2KfZhNiq2YXZiNmK2YQt2KjYp9mE2YXYttin2LHYqNipLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTQtSW52ZXN0bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw==",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRuLdi12YbYp9iv2YrZgi3Yp9mE2KfYs9iq2KvZhdin2LEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTUtUHJvdmlzaW9ucy1hbmQtUmVzZXJ2ZXMtaW4tSXNsYW1pYy1JbnN1cmFuY2UtQ29tcGFuaWVzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTXU1Ldin2YTYqtmC2LHZitixLdi52YYt2KfZhNmC2LfYp9i52KfYqi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTYtRm9yZWlnbi1DdXJyZW5jeS1UcmFuc2FjdGlvbnMtYW5kLUZvcmVpZ24tT3BlcmF0aW9ucy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTI2Ldin2YTYqtmC2LHZitixLdi52YYt2KfZhNmC2LfYp9i52KfYqi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTctSW52ZXN0bWVudC1pbi1SZWFsLUVzdGF0ZS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTI3Ldi12YrYrdmI2YrZhC3Yp9mE2YXZiNiz2IjYqfZhdmE2YrYp9iy2KfZhS3ZiNin2YTYo9iv2YjYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTgtSXNsYW1pYy1GaW5hbmNpYWwtU2VydmljZXMtT2ZmZXJlZC1ieS1Db252ZW50aW9uYWwtRmluYW5jaWFsLUluc3RpdHV0aW9ucy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRuLdiq2K3Yr9mK2K8t2KfZhNmC2YjYp9im2YUt2KfZhNmF2KfZhNmK2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMTktQ29udHJpYnV0aW9ucy1pbi1Jc2xhbWljLUluc3VyYW5jZS1Db21wYW5pZXMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTXE5Ldin2YTYp9i02KrYsdin2YPYp9iqLdmB2Yot2LTYsdmD2KfYqi3Yp9mE2KrYo9mF2YrZhi3Yp9mE2KXYs9mE2KfZhdmK2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjAtTXVyYWJhaGEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjAtLdin2YTYqtmC2LHZitixLdi52YYt2KfZhNmC2LfYp9i52KfYqi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjEtRGlzY2xvc3VyZS1vbi1UcmFuc2Zlci1vZi1Bc3NldHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjEtLdin2YTYpdmB2LXYp9itLdi52YYt2KfZhNmC2LfYp9i52KfYqi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjItU2VnbWVudC1SZXBvcnRpbmcucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjItLdin2YTYqtmC2LHZitixLdi52YYt2KfZhNmC2LfYp9i52KfYqi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjMtQ29uc29saWRhdGlvbi5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjMtLdin2YTYp9iz2KrYq9mF2KfYsS3ZgdmKLdin2YTZhdmE2YrYp9iy2KfZhS3ZiNin2YTYo9iv2YjYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjQtSW52ZXN0bWVudHMtaW4tQXNzb2NpYXRlcy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjQtLdin2YTYp9iz2KrYq9mF2KfYsS3ZgdmKLdin2YTZhdmE2YrYp9iy2KfZhS3ZiNin2YTYo9iv2YjYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjUtSW52ZXN0bWVudC1pbi1TaGFyZXMtYW5kLVNpbWlsYXItSW5zdHJ1bWVudHMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjUtLdin2YTYp9iz2KrYq9mF2KfYsS3ZgdmKLdin2YTZhdmE2YrYp9iy2KfZhS3ZiNin2YTYo9iv2YjYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjYtSW52ZXN0bWVudC1pbi1SZWFsLUVzdGF0ZS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjYtLdin2YTYp9iz2KrYq9mF2KfYsS3ZgdmKLdin2YTZhdmE2YrYp9iy2KfZhS3ZiNin2YTYo9iv2YjYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEvRmluYW5jaWFsLUFjY291bnRpbmctU3RhbmRhcmQtMjctSW52ZXN0bWVudC1BY2NvdW50cy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjctLdit2LPYp9io2KfYqi3Yp9mE2KfYs9iq2KvZhdin2LEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTI4LU11cmFiYWhhLWFuZC1PdGhlci1EZWZlcnJlZC1QYXltZW50LVNhbGVzLUZvcm1hdHRlZC0yMDIxLWNsZWFuLTEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLMjgtLdin2YTZh9io2YjYty3ZiNin2YTYrtiz2KfYptixLdin2YTYp9im2KrZhdin2YbZitipLdmI2KfZhNin2YTYqtiy2KfZhdin2Kot2KfZhNmF2K3ZhdmE2Kkt2KjYp9mE2K7Ys9in2KbYsS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTMwLUltcGFpcm1lbnQtTG9zc2VzLWFuZC1PbmVyb3VzLUNvbW1pdG1lbnRzLUZvcm1hdHRlZC0yMDIxLWNsZWFuLTEzLU5vdi0yMi0xLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTMwLdin2YTZh9io2YjYty3ZiNin2YTYrtiz2KfYptiz2KjYqS3Yp9mE2K7Zitin2LEt2YjYp9mE2KvZhdin2LEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTMzLUludmVzdG1lbnQtaW4tU3VrdWstU2hhcmVzLWFuZC1TaW1pbGFyLUluc3RydW1lbnRzLWZvcm1hdHRlZC1jbGVhbi11cGRhdGVkLWFwcmlsLTIwMjMucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTMzLdin2YTYqtmC2LHZitixLdin2YTZhdin2YTZii3ZhNit2YXZhNipLdin2YTYtdmD2YjZgy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM0LUZpbmFuY2lhbC1SZXBvcnRpbmctZm9yLVN1a3VrLWhvbGRlcnMtRmluYWwtQ2xlYW4tdXBkYXRlZC1hcHJpbC0yMDIzLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTM0Ldin2YTYqtmC2LHZitixLdin2YTZhdin2YTZii3ZhNit2YXZhNipLdin2YTYtdmD2YjZgy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM1LVJpc2stUmVzZXJ2ZS1GaW5hbGl6YXRpb24tRm9ybWF0dGVkLTIwMjEtY2xlYW4tMTYtQXVnLTIwMjIucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTM1Ldin2YTYqtmC2LHZitixLdin2YTZhdin2YTZii3ZhNit2YXZhNipLdin2YTYtdmD2YjZgy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM2LUZpcnN0LVRpbWUtQWRvcHRpb24tb2YtQUFPSUZJLUZpbmFuY2lhbC1BY2NvdW50aW5nLVN0YW5kYXJkcy1GaW5hbC0zMC1Ob3YtMjAtQ2xlYW4ucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTM2Ldiq2LfYqNmK2YIt2YXYudin2YrZitixLdij2YrZiNmB2Yot2YTZhNmF2K3ZhdmE2Kkt2KjYp9mE2K7Ys9in2KbYsS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM3LUZpbmFuY2lhbC1SZXBvcnRpbmctYnktV2FkaC1LaGl5YXItYW5kLVNhaGF3YXRpLUZpbmFsLTE1LUplbWJlci0yMDIwLWNsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjYvMDMv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTM3Ldin2YTZh9io2YjYty3ZiNin2YTYrtiz2KfYptixLdin2YTYp9im2KrZhdin2YbZitipLdmI2KfZhNin2YTYqtiy2KfZhdin2Kot2KfZhNmF2K3ZhdmE2Kkt2KjYp9mE2K7Ys9in2KbYsS5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTM5LUZpbmFuY2lhbC1SZXBvcnRpbmctZm9yLVpoYWthhi1jbGVhbi1KdW5lLTIwMjIucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTM5Ldin2YTYqtmC2LHZitixLdin2YTZhdin2YTZii3ZhNit2YXZhNipLdin2YTYtdmD2YjZgy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQwLUZpbmFuY2lhbC1SZXBvcnRpbmctZm9yLUlzbGFtaWMtV2luZG93cy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRwLdin2YTYqtmC2LHZitixLdin2YTZhdin2YTZii3ZhNit2YXZhNipLdin2YTYtdmD2YjZgy5wZGYmc2V0dGluZ3M9MDAxMDAwMTExMDAwMDAxMTEwMCZsYW5nPWVuLVVT",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQxLUludGVyaW0tRmluYW5jaWFsLVJlcG9ydGluZy12MTYtZmluYWwtZm9yLWlzc3VhbmNlX2NsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRuLdi12YbYp9iv2YrZgi3Yp9mE2KfYs9iq2KvZhdin2LEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQyLVByZXNlbnRhdGlvbi1hbmQtRGlzY2xvc3VyZXMtaW4tdGhlLUZpbmFuY2lhbC1TdGF0ZW1lbnRzLW9mLVRha2FmdWwtSW5zdGl0dXRpb25zLWZpbmFsLWNsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMTEv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRyLdin2YTZhdmI2KzZiNiv2KfYqi3ZiNmF2LTYsdmI2LnYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjMvMDkvRkFTLTQzLUFjY291bnRpbmctZm9yLVRha2FmdWwtUmVjb2duaXRpb24tYW5kLU1lYXN1cmVtZW50X2ZpbmFsX2NsZWFuLnBkZiZzZXR0aW5ncz0wMDEwMDAxMTEwMDAwMDExMTAwJmxhbmc9ZW4tVVM=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjUvMDcv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTRzLdin2YTZh9io2YjYty3ZiNin2YTYrtiz2KfYptiz2KjYqS3Yp9mE2K7Zitin2LEt2YjYp9mE2KvZhdin2LEucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    "https://aaoifi.com/themencode-pdf-viewer-sc/?lang=en&tnc_pvfw=ZmlsZT1odHRwczovL2Fhb2lmaS5jb20vd3AtY29udGVudC91cGxvYWRzLzIwMjUvMDUv2YXYudmK2KfYsS3Yp9mE2YXYrdin2LPYqNipLdin2YTZhdin2YTZitipLTR0Ldiq2K3Yr9mK2K8t2KfZhNiz2YrYt9ix2Kkt2LnZhNmJLdin2YTZhdmI2KzZiNiv2KfYqi3ZiNmF2LTYsdmI2LnYp9iqLdin2YTZhdi02KfYqNmH2KkucGRmJnNldHRpbmczPTAwMTAwMDExMTAwMDAwMTExMDAmbGFuZz1lbi1VUw=",
    # Direct PDF links (Standards 44-47)
    "https://aaoifi.com/wp-content/uploads/2024/06/FAS-44_-Determining-Control-of-Assets-and-Business-Final.pdf",
    "https://aaoifi.com/wp-content/uploads/2024/06/FAS-45_Quasi-equity-Including-Investment-Accounts-Final.pdf",
    "https://aaoifi.com/wp-content/uploads/2024/06/FAS-46_Off-Balance-Sheet-Assets-Under-Management-Final.pdf",
    "https://aaoifi.com/wp-content/uploads/2024/06/FAS-47_Transfer-of-Assets-between-Investment-Pools-Final.pdf",
]

def decode_param(encoded):
    """Decode base64 tnc_pvfw param and extract components."""
    try:
        # Add padding if needed
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
    """Change lang param to ar for Arabic version. Handle padding."""
    try:
        # Add padding if needed
        padded = encoded + '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.b64decode(padded).decode('utf-8')
        arabic_decoded = re.sub(r'lang=[^&]+', 'lang=ar', decoded)
        arabic_encoded = base64.b64encode(arabic_decoded.encode('utf-8')).decode('utf-8')
        return arabic_encoded
    except Exception:
        return None

def get_pdf_url(url):
    """Extract the actual PDF URL from a viewer URL or return direct PDF URL."""
    # Direct PDF link
    if url.startswith('https://aaoifi.com/wp-content/'):
        return url, None  # No encoded param needed

    # Viewer URL - extract from base64 param
    match = re.search(r'tnc_pvfw=([^&#]+)', url)
    if match:
        encoded = match.group(1)
        params = decode_param(encoded)
        pdf_url = params.get('file')
        if pdf_url:
            return pdf_url, encoded

    return None, None

def encode_url(url):
    """Properly encode URL with non-ASCII characters."""
    parsed = urllib.parse.urlparse(url)
    # Encode path with non-ASCII chars
    path_encoded = urllib.parse.quote(parsed.path, safe='/')
    # Encode query with non-ASCII chars
    query_encoded = urllib.parse.quote(parsed.query, safe='=&')
    # Reconstruct URL
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path_encoded, parsed.params, query_encoded, parsed.fragment)
    )

def download_pdf(pdf_url, output_path, skip_if_exists=False):
    """Download PDF using urllib (stdlib). Skip if file exists and non-empty."""
    if skip_if_exists and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return True, "Skipped (exists) {}".format(os.path.basename(output_path))
    try:
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

def try_arabic_fallback(en_url):
    """Try to construct Arabic PDF URL by replacing language indicators in URL."""
    # Common patterns: replace /en- with /ar- or _en_ with _ar_
    ar_url = en_url
    for old, new in [('/en-', '/ar-'), ('_en_', '_ar_'), ('_en.', '_ar.'), ('/en/', '/ar/')]:
        if old in ar_url:
            ar_url = ar_url.replace(old, new)
            break
    return ar_url if ar_url != en_url else None

def safe_print(msg):
    """Print message, replacing non-ASCII chars if console can't handle them."""
    try:
        print(str(msg))
    except UnicodeEncodeError:
        safe = str(msg).encode('ascii', errors='replace').decode('ascii')
        print(safe)

def main():
    output_dir = "D:/AI Projects/Freelance/Sabry/Mushir-Sharia-Bot/data/raw/aaoifi_standards"
    os.makedirs(output_dir, exist_ok=True)

    safe_print("Output directory: {}".format(output_dir))
    safe_print("Processing {} standards...\n".format(len(URLS)))

    for i, url in enumerate(URLS, 1):
        pdf_url, encoded = get_pdf_url(url)

        if not pdf_url:
            safe_print("[{}] Could not extract PDF URL, skipping.".format(i))
            continue

        name_base = "Standard_{:02d}".format(i)

        # Download English version
        en_output = os.path.join(output_dir, "{}_EN.pdf".format(name_base))
        if os.path.exists(en_output) and os.path.getsize(en_output) > 0:
            safe_print("[{}] EN: Skipped (exists) {}_EN.pdf".format(i, name_base))
        else:
            safe_print("[{}] EN: Downloading to {}_EN.pdf".format(i, name_base))
            success, msg = download_pdf(pdf_url, en_output, skip_if_exists=False)
            safe_print("    {}: {}".format("OK" if success else "FAIL", msg[:100]))

        # Try Arabic version
        ar_output = os.path.join(output_dir, "{}_AR.pdf".format(name_base))
        if os.path.exists(ar_output) and os.path.getsize(ar_output) > 0:
            safe_print("    AR: Skipped (exists) {}_AR.pdf".format(name_base))
        else:
            ar_pdf_url = None
            try:
                if encoded:
                    ar_encoded = make_arabic_url(encoded)
                    if ar_encoded:
                        ar_params = decode_param(ar_encoded)
                        ar_pdf_url = ar_params.get('file')
                if not ar_pdf_url:
                    # Fallback: try to guess Arabic URL from English PDF URL
                    ar_pdf_url = try_arabic_fallback(pdf_url) or pdf_url
                safe_print("    AR: Downloading to {}_AR.pdf".format(name_base))
                success, msg = download_pdf(ar_pdf_url, ar_output, skip_if_exists=False)
                safe_print("    {}: {}".format("OK" if success else "FAIL", msg[:100]))
            except Exception as e:
                safe_print("    AR FAIL: {}".format(str(e)[:100]))

        safe_print("")

    safe_print("Done!")

if __name__ == "__main__":
    main()

"""Reproduce the dated pilot register from preserved captures; makes no network calls."""
from pathlib import Path
from datetime import datetime, UTC
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
OUT = ROOT / '_bmad-output/initiative-egypt-market-knowledge/acquisition-results-2026-10-02'
OUT.mkdir(exist_ok=True)
RUNS = [ROOT / 'data/runtime/artifacts/l6_scrape/public_capture' / name for name in
        ('pilot-20261002-reviewed-01', 'pilot-20261002-reviewed-02')]
captures, summaries, references = {}, [], {}

def inspect_refs(value, run):
    if isinstance(value, dict):
        if {'artifact_path', 'sha256', 'bytes'} <= value.keys():
            file = (run / value['artifact_path']).resolve()
            assert file.is_relative_to(run.resolve()), 'artifact escapes run'
            data = file.read_bytes()
            assert len(data) == value['bytes'], f'byte mismatch: {file}'
            assert hashlib.sha256(data).hexdigest() == value['sha256'], f'hash mismatch: {file}'
            references[str(file)] = dict(sha256=value['sha256'], bytes=len(data))
        for child in value.values(): inspect_refs(child, run)
    elif isinstance(value, list):
        for child in value: inspect_refs(child, run)

for run in RUNS:
    summary = json.loads((run / 'summary.json').read_text())
    events = [json.loads(line) for line in (run / 'manifest.jsonl').read_text().splitlines()]
    assert summary['request_count'] == sum(e['record_type'] == 'attempt' for e in events)
    assert summary['capture_count'] == sum(e['record_type'] == 'capture' for e in events)
    summaries.append(dict(run=str(run.relative_to(ROOT)), **summary))
    for event in events:
        inspect_refs(event, run)
        if event['record_type'] == 'capture': captures[event['label']] = (run, event)

observations = []
def observe(provider, label, field, summary, needle, page=None, scope='public advertised arrangement'):
    run, capture = captures[label]
    data = json.loads((run / capture['extraction']['artifact_path']).read_text(encoding='utf-8'))
    if page is None:
        text, pointer = data['text'], '/text'
    else:
        assert data['pages'][page-1]['page'] == page
        text, pointer = data['pages'][page-1]['text'], f'/pages/{page-1}/text'
    start = text.index(needle)
    assert text[start:start+len(needle)] == needle
    observations.append(dict(observation_id=f'OBS-{len(observations)+1:03}', provider=provider,
        field=field, observation=summary, scope=scope, source_url=capture['final_url'],
        capture_id=capture['capture_id'], raw_sha256=capture['raw']['sha256'],
        raw_artifact=str((run/capture['raw']['artifact_path']).relative_to(ROOT)),
        extraction_artifact=str((run/capture['extraction']['artifact_path']).relative_to(ROOT)),
        extraction_sha256=capture['extraction']['sha256'], source_pointer=pointer, page=page,
        start=start, end=start+len(needle), offset_unit='unicode_code_points',
        review_status='automated analyst observation; human second review pending',
        applicability='unestablished for a selected customer/channel/date', scholar_status='pending'))

observe('Contact','contact-contact','corporate_email','Info@contact.eg','Info@contact.eg')
observe('Contact','contact-contact','corporate_hotline','16177','16177')
observe('Contact','contact-home','product_categories','Advertised vehicles, home, education, lifestyle, green finance and travel categories.','Vehicles\nHome\nInsurance\nEducation\nLifestyle\nGreen Finance\nTravel and Tourism')
observe('Contact','contact-terms','document_coverage','Customer terms appendix; main agreement and per-transaction statements are separate.','These terms and conditions are an appendix to the financing agreement',1,'English published appendix; effective date unestablished')
observe('Contact','contact-terms','company_name_candidate','Appendix names Contact Credit Tech as the company; exact incorporated party and current applicability need confirmation.','Contact Credit Tech (referred to as the company in this appendix)',1)
observe('Contact','contact-terms','repayment_schedule','Monthly due dates are described as 15th or 30th; price, total instalments, period and return rate belong to each supplementary statement.','the supplementary statement issued for each',1,'goods/services appendix; per-transaction statement missing')
observe('Contact','contact-terms','late_payment','English appendix states a monthly late fine capped at 9% of unpaid instalments; rate/version/applicability need human verification.','It shall be a maximum of 9% on the value of the unpaid installments',1)
observe('Contact','contact-terms','ownership','English appendix asserts company ownership until all financing instalments are received; underlying acquisition/risk/title chain remains unestablished.','The company remains the owner of the goods/services being financed until it obtains all the financing installments',1)
observe('Contact','contact-terms','early_settlement','English appendix mentions written notice at least 30 days and refers to missing main-contract paragraphs 3/b and 3/c.','in accordance with paragraphs 3/b and 3/c of the contract',1)
observe('Contact','contact-terms','merchant_role_description','Appendix distinguishes the merchant providing goods/services details from the company; does not establish the exact seller/creditor legal relationship.','goods/services being financed by the merchant',1)
observe('Contact','contact-terms','security_interest','Appendix describes a movable-property security arrangement and incorporated supplementary statement.','mortgage the movable property',1)
observe('Contact','contact-terms','fatorty_mechanism','Fatorty finances goods/services already purchased; keep separate from purchase-time instalments.','goods, products or services that he has purchased or obtained',3,'Fatorty general subsection')
observe('Contact','contact-terms','fatorty_fee','General Fatorty subsection states expenses no less than 5% of financing.','no \nless than 5% of the financing amount',3,'Fatorty general subsection')
observe('Contact','contact-terms','fatorty_telecom_tenor','Telecom/wallet variant describes 6–36 months; this is not a universal Contact tenor.','from 6 months to 36 months',3,'Fatorty subsequent finance with telecom companies')
observe('Contact','contact-terms','fatorty_telecom_disbursement','Telecom/wallet variant describes transfer of financing to customer wallet after deducting fees.','after \ndeducting the administrative fees',3,'Fatorty subsequent finance with telecom companies')
observe('Contact','contact-terms','club_tenor','Club-membership subsection describes 12–60 months.','from 12 to 60 months',4,'club-membership financing')
observe('Contact','contact-terms','club_fee','Club-membership subsection states fees no less than 3% of financing.','no less than 3% of the financing',4,'club-membership financing')
observe('Halan','halan-shop','shop_channel','Advertised Halan Shop sales channel for electronics, appliances and phones with instalments; same legal seller/financier not established.','choose flexible payment plans to own the items you want over 6, 12, or 36 months')
observe('Halan','halan-shop','advertised_limit','Halan Shop advertises application for up to EGP 500,000; eligibility and actual approved amount are not established.','Apply for a limit of up to 500,000 L.E.')
observe('Halan','halan-contact','corporate_hotline','16303','16303')
observe('Halan','halan-consumer-finance','merchant_network_channel','Consumer-finance page advertises instalments at a vendor network; exact contracting financier/merchant unknown.','over 8,000 registered vendors')
observe('Halan','halan-consumer-finance','advertised_tenor','Consumer-finance page advertises 6–36 months.','6 to 36 month installment plans')
observe('Halan','halan-consumer-finance','advertised_fees','Page advertises no administrative fees; this does not prove absence of all contractual charges.','No Administrative Fees')
observe('Halan','halan-consumer-finance','program_leads','Health, education, home finishing and furnishing programs are separate leads, not the same established financing arrangement.','Consumer Finance Programs')
observe('Aman','aman-installment','channels','Advertises Aman online store, merchant network and branches; classify as multiple advertised channels with legal roles unresolved.','whether through Aman online store, Aman merchant network, or Aman branches')
observe('Aman','aman-installment','product_variants','Page advertises regular and Islamic instalment limits; its Islamic claim is not a scholar-approved finding.','Islamic Installment Limit')
observe('Aman','aman-installment','merchant_process','Page describes merchant QR purchase amount and option review; record description only, no transaction undertaken.','Enter the purchase amount you wish to finance and review the available installment options')
observe('Aman','aman-installment','advertised_tenor','FAQ advertises typical 3–36 month plans depending on product/type/price.','typically ranging from 3 to 36 months')
observe('Aman','aman-installment','corporate_hotline','19910','19910')
observe('Aman','aman-store','store_channel','Online-store page advertises goods sold with cash/card/instalment options; seller/creditor legal identities are not established.','Whether Cash, Credit Card, or Installments')
observe('Aman','aman-store','advertised_pricing','FAQ says interest rates vary with product and advertises promotions; no operative rate table or full repayment schedule captured.','The interest rates vary depending on the product type')
observe('Aman','aman-contact','corporate_contact_route','Corporate contact form and Maadi office location captured; a corporate email address was not established.','Palestine Rd, El-Basatin Sharkeya, El Maaid,  Cairo Governorate 11693')

# Passage coverage is checked separately from mere anchor existence. Widen
# multi-fact observations to the complete sentence/section containing the facts.
coverage = {
 'OBS-004': ('These terms and conditions are an appendix', 'according to the supplementary statement issued for each', ['appendix', 'supplementary statement']),
 'OBS-006': ('The total value of financing goods/services', 'payment systems announced by the company from time to time.', ['15th or 30th', 'price of the goods/services', 'total installments', 'installment period', 'return']),
 'OBS-007': ('The company has the right to impose a monthly late fine', 'The company notifies the customer electronically of this', ['monthly', '9%', 'unpaid installments']),
 'OBS-009': ('The second party has the right to accelerate', 'in accordance with paragraphs 3/b and 3/c of the contract', ['in writing', 'thirty days', '3/b', '3/c']),
 'OBS-011': ('The customer agrees that the company will mortgage', 'The Movable', ['mortgage', 'supplementary statement']),
 'OBS-012': ('Fatorty Terms & Conditions:', 'goods, products or services that he has purchased or obtained', ['Fatorty', 'purchased or obtained']),
 'OBS-013': ('In the event that the customer obtains financing according to Fatorty product,', 'less than 5% of the financing amount', ['Fatorty', '5%']),
 'OBS-014': ('Terms & Conditions of Fatorty Product for Subsequent Consumer Financing with Telecom Companies:', 'from 6 months to 36 months', ['Telecom Companies', '6 months', '36 months']),
 'OBS-015': ('The company transfers the financing amount', 'deducting the administrative fees', ['company transfers', "customer's wallet", 'deducting']),
 'OBS-016': ('Club Product Terms and Conditions:', 'from 12 to 60 months', ['club membership', '12 to 60 months']),
 'OBS-017': ('Club Product Terms and Conditions:', 'no less than 3% of the financing', ['club membership', '3%']),
 'OBS-018': ('We know finding the best prices matters', 'Explore unbeatable prices and flexible payment options today!', ['electronics', 'home appliances', 'mobile phones', '6, 12, or 36 months']),
 'OBS-021': ("Shop now and pay later with Halan's", 'Halan makes shopping convenient and affordable for everyone.', ['BNPL', 'installment plans', 'registered vendors']),
 'OBS-024': ('Consumer Finance Programs', "Don't wait, get started today", ['Health', 'Education', 'Home Finishing', 'Furnishing']),
 'OBS-026': ('Aman Installment Types', 'Apply & Track Your Installments', ['Normal', 'Islamic', 'Islamic Installment Limit']),
 'OBS-028': ('What installment plans are available with Aman?', 'our hotline at 19910.', ['type and price', '3 to 36 months']),
 'OBS-031': ('What Are the Interest Rates Associated', 'our hotline at 19910.', ['vary depending on the product type', 'promotions']),
 'OBS-032': ('Contact Us', 'Copied', ['Your email', 'Our Offices', 'Palestine Rd']),
}
for item in observations:
    if item['observation_id'] in coverage:
        source=json.loads((ROOT/item['extraction_artifact']).read_text(encoding='utf-8'))
        text=source['text'] if item['page'] is None else source['pages'][item['page']-1]['text']
        first,last,required=coverage[item['observation_id']]
        start=text.index(first); end=text.index(last,start)+len(last)
        selected=text[start:end]
        assert all(term in selected for term in required), item['observation_id']
        item.update(start=start,end=end,passage_coverage_terms_checked=required)

manual = json.loads((BASE/'manual-public-observations.json').read_text(encoding='utf-8'))
quality = []
run, arabic = captures['contact-terms-ar']
data = json.loads((run/arabic['extraction']['artifact_path']).read_text())
assert all(sum(c.isalpha() for c in p['text']) < 20 for p in data['pages'])
quality.append(dict(provider='Contact', capture_id=arabic['capture_id'],
    source_url=arabic['final_url'], raw_sha256=arabic['raw']['sha256'],
    raw_artifact=str((run/arabic['raw']['artifact_path']).relative_to(ROOT)),
    collector_extraction_status=arabic['extraction_status'], acceptance_status='rejected_text_extraction',
    detail='Both pages render legibly as Arabic, but extracted text is punctuation/OTP with fewer than 20 alphabetic characters per page. OCR flag is incorrectly empty. Original pages require transcription/OCR and second-human legal verification.',
    version_equivalence='Arabic two-page and English five-page appendices are not established as matching effective versions; do not merge them.',
    next_action='Verified Arabic extraction and effective-version comparison; separate parser-quality repair.'))

for image in (ROOT/'tmp/pdfs/acquisition-20261002').glob('contact-*.png'):
    destination=OUT/'visual-review'/image.name
    destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(image,destination)

document_copies=[]
for label,filename in [('contact-terms','Contact-English-terms-appendix.pdf'),
                       ('contact-terms-ar','Contact-Arabic-terms-appendix.pdf')]:
    run,event=captures[label]
    destination=OUT/'documents'/filename
    destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(run/event['raw']['artifact_path'],destination)
    assert hashlib.sha256(destination.read_bytes()).hexdigest()==event['raw']['sha256']
    document_copies.append(dict(path=str(destination.relative_to(ROOT)),sha256=event['raw']['sha256'],
                               source_capture_id=event['capture_id'], byte_identical_to_raw=True))

common_gaps=['exact legal seller and creditor for selected arrangement', 'cash price / financed principal / total payable',
 'complete standard main agreement and incorporated schedules', 'effective version and customer/channel applicability',
 'ownership acquisition, delivery and risk chronology', 'human second review of material observations', 'scholar-selected AAOIFI rule evaluation']
dossiers=[]
for provider, channel, contracts, extra in [
 ('Contact','merchant finance described; post-purchase Fatorty and club programs separately observed','English five-page appendix readable; Arabic two-page appendix captured with rejected extraction; main agreement absent',['early-settlement main-contract clauses', 'late-fee beneficiary and operative version']),
 ('Halan','own shop and external merchant network advertised; same legal seller/creditor unresolved','No applicable standard consumer-finance agreement captured',['late/default and early-settlement terms', 'complete fee/repayment annex']),
 ('Aman','own online store and merchant network advertised; regular/Islamic products require separate arrangements','No applicable standard consumer-finance agreement captured',['separate Islamic-product mechanism/contract', 'late/default and early-settlement terms']),
 ('Souhoola','partner-merchant financing described in manually reviewed terms; exact incorporated party conflict unresolved','General website/service terms manually reviewed; full instalment agreement absent',['dated CI/Contact Investment legal-name resolution', 'full fees and operative instalment agreement']),
 ('ValU','agreement party/operator leads; selected vendor/channel role unresolved','Public terms manually inspected; no full copied contract artifact',['eligible permission/document-delivery route', 'app/operator/creditor role and cover/schedules'])]:
    dossiers.append(dict(provider=provider, arrangement_description=channel,
        role_classification='unresolved contractual roles; described channels retained separately',
        contract_coverage=contracts, observation_ids=[o['observation_id'] for o in observations if o['provider']==provider],
        material_gaps=common_gaps+extra, scholar_status='pending; no verdict'))

register=dict(created_at=datetime.now(UTC).isoformat(), scope='five-provider nonpersonal public financing evidence pilot',
 runs=summaries, dossiers=dossiers, observations=observations, manual_observations=manual,
 quality_flags=quality, document_copies=document_copies, accepted_contractual_role_claims=0, scholar_verdicts=0,
 rights_boundary='internal research decisions only; source permission and publication rights not established')
(OUT/'evidence-register.json').write_text(json.dumps(register,ensure_ascii=False,indent=2),encoding='utf-8')
verification=dict(verified_at=datetime.now(UTC).isoformat(), independent_artifact_hash_checks=len(references),
 artifact_bytes_total=sum(x['bytes'] for x in references.values()), span_checks=len(observations),
 raw_and_derived_artifacts=references, byte_identical_document_copies=document_copies,
 all_hash_and_byte_checks_passed=True, all_span_checks_passed=True,
 expanded_multi_fact_passages=len(coverage), passage_coverage_method='Selected contextual passages and required subfact terms; automated analyst review, not human semantic acceptance.',
 readable_contracts='one English appendix; Arabic text rejected independently',
 limitation='Hashes/spans establish stored provenance, not current applicability or scholar acceptance.')
(OUT/'provenance-verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
inventory=['# Captured source inventory — 2026-10-02','',
 '| Label | Outcome | Extraction | Source URL | Raw artifact SHA-256 |','|---|---|---|---|---|']
for label,(run,e) in captures.items():
    inventory.append(f"| {label} | {e['state']} | {e.get('extraction_status','—')} | {e['final_url']} | {e.get('raw',{}).get('sha256','—')} |")
(OUT/'capture-inventory.md').write_text('\n'.join(inventory)+'\n',encoding='utf-8')
print(json.dumps(dict(requests=sum(s['request_count'] for s in summaries), captures=sum(e['state']=='captured' for _,e in captures.values()),
 observations=len(observations), verified_artifacts=len(references), bytes=verification['artifact_bytes_total'], output=str(OUT))))

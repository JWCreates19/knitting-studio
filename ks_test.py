#!/usr/bin/env python3
"""
Knitting Studio — Regression Test Suite
Run: python3 ks_test.py path/to/index.html
"""

import sys
import re
import subprocess
import tempfile
import os

# ── Colour output ──────────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

passed = []
failed = []
warnings = []

def ok(name):
    passed.append(name)
    print(f"  {GREEN}✓{RESET} {name}")

def fail(name, detail=''):
    failed.append(name)
    msg = f"  {RED}✗{RESET} {name}"
    if detail: msg += f"\n      {RED}{detail}{RESET}"
    print(msg)

def warn(name, detail=''):
    warnings.append(name)
    msg = f"  {YELLOW}⚠{RESET} {name}"
    if detail: msg += f"\n      {YELLOW}{detail}{RESET}"
    print(msg)

def section(title):
    print(f"\n{BOLD}{title}{RESET}")

# ── Load file ──────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print(f"Usage: python3 ks_test.py path/to/index.html")
    sys.exit(1)

filepath = sys.argv[1]
if not os.path.exists(filepath):
    print(f"{RED}File not found: {filepath}{RESET}")
    sys.exit(1)

with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"\n{BOLD}Knitting Studio — Regression Test Suite{RESET}")
print(f"File: {filepath}  ({len(html):,} chars, {html.count(chr(10)):,} lines)")

# Extract JS block
script_start = html.find('<script>') + len('<script>')
script_end   = html.rfind('</script>')
js_raw = html[script_start:script_end]

# ══════════════════════════════════════════════════════════════════
section("1. Character Safety")
# ══════════════════════════════════════════════════════════════════

# Smart quotes — the bug that caused the production outage
sq_count = js_raw.count('\u2018') + js_raw.count('\u2019')
if sq_count == 0:
    ok("No smart/curly quotes in JS block")
else:
    examples = []
    for m in re.finditer('[\u2018\u2019]', js_raw):
        examples.append(repr(js_raw[max(0,m.start()-15):m.start()+15]))
        if len(examples) >= 3: break
    fail(f"Smart quotes found in JS ({sq_count} occurrences)",
         f"First occurrence: {examples[0] if examples else ''}")

# Ellipsis used as spread operator
spread_ellipsis = len(re.findall(r'[\[\{]\u2026', js_raw))
if spread_ellipsis == 0:
    ok("No ellipsis (…) used as spread operator")
else:
    fail(f"Ellipsis used as spread operator ({spread_ellipsis} occurrences) — use ... instead")

# En-dash used as CSS custom property prefix (–var vs --var)
# These break CSS variables silently
css_start = html.find('<style>') + len('<style>')
css_end   = html.find('</style>')
css_raw   = html[css_start:css_end]
en_dash_vars = len(re.findall(r'var\(\u2013', css_raw))
if en_dash_vars == 0:
    ok("No en-dashes in CSS var() references")
else:
    warn(f"En-dashes in CSS var() ({en_dash_vars} occurrences) — may break CSS variables in some environments")

# Check for any other non-ASCII that would cause a SyntaxError as a JS operator
# Safe set: emoji and symbols used inside strings/comments
SAFE_NONASCII = set('\u2500\u2026\u2014\u00b7\u2192\u2013\u00d7\u2713\u25cf'
                    '\u2197\u26a0\u2715\u25b6\u25c0\u25b2\u25bc\u2600'
                    '\U0001faa1\U0001f4c4\U0001f319\u2714\u21ba\u2190')
dangerous = []
for i, ch in enumerate(js_raw):
    if ord(ch) > 127 and ch not in SAFE_NONASCII:
        ctx = js_raw[max(0,i-15):i+15]
        dangerous.append(f"U+{ord(ch):04X} ({repr(ch)}): {repr(ctx)}")
if not dangerous:
    ok("No unexpected non-ASCII characters in JS")
else:
    fail(f"Unexpected non-ASCII characters in JS ({len(dangerous)} occurrences)",
         dangerous[0] if dangerous else '')

# ══════════════════════════════════════════════════════════════════
section("2. JavaScript Syntax (node --check)")
# ══════════════════════════════════════════════════════════════════

with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as tmp:
    tmp.write(js_raw)
    tmp_path = tmp.name

try:
    result = subprocess.run(['node', '--check', tmp_path],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ok("node --check passed — no syntax errors")
    else:
        err = result.stderr.strip().split('\n')
        fail("node --check FAILED — JavaScript syntax error",
             '\n      '.join(err[:4]))
finally:
    os.unlink(tmp_path)

# ══════════════════════════════════════════════════════════════════
section("3. HTML Structure")
# ══════════════════════════════════════════════════════════════════

html_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))

# Required page elements
required_pages = ['page-projects','page-stash','page-patterns','page-feedback']
for pid in required_pages:
    if pid in html_ids: ok(f"Page element present: #{pid}")
    else: fail(f"Missing page element: #{pid}")

# Required modals
required_modals = ['proj-modal','yarn-modal','needle-modal','acquire-modal',
                   'pat-modal','feedback-modal']
for mid in required_modals:
    if mid in html_ids: ok(f"Modal present: #{mid}")
    else: fail(f"Missing modal: #{mid}")

# Required structural elements
required_els = ['app-header','app-nav','loading-screen','pdf-viewer',
                'projects-grid','yarn-grid','needle-grid','acquire-list',
                'patterns-list','feedback-list','toast','sync-indicator',
                'loading-msg']
for eid in required_els:
    if eid in html_ids: ok(f"Element present: #{eid}")
    else: fail(f"Missing element: #{eid}")

# Stash notes panels
stash_note_els = ['stash-note-panel-yarn','stash-note-panel-needles',
                  'stash-note-ta-yarn','stash-note-ta-needles',
                  'stash-notes-overlay']
all_sn = all(e in html_ids for e in stash_note_els)
if all_sn: ok("Stash notes panel HTML elements present")
else:
    missing_sn = [e for e in stash_note_els if e not in html_ids]
    fail(f"Missing stash notes elements: {missing_sn}")

# Collapse buttons and section bodies
for section_name in ['yarn','needle','acquire']:
    btn = f'{section_name}-collapse-btn'
    body = f'{section_name}-section-body'
    if btn in html_ids and body in html_ids:
        ok(f"Collapse button + body present: {section_name}")
    else:
        fail(f"Collapse missing for {section_name} (btn:{btn in html_ids} body:{body in html_ids})")

# Needle multi-select
if 'needle-multi-select' in html:
    ok("Needle multi-select present in project modal")
else:
    fail("Needle multi-select missing from project modal")

# PDF viewer elements
pdf_els = ['pdf-canvas','row-highlight','pdf-title','pdf-page-info',
           'zoom-info','c-val','hl-btn','notes-panel','notes-list',
           'notes-toggle','pdf-canvas-area']
for eid in pdf_els:
    if eid in html_ids: ok(f"PDF viewer element: #{eid}")
    else: fail(f"Missing PDF viewer element: #{eid}")

# Supabase credentials are placeholders (expected in template)
if 'YOUR_SUPABASE_URL' in html or 'YOUR_SUPABASE_ANON_KEY' in html:
    warn("Supabase credentials are still placeholders — replace before deploying")
else:
    ok("Supabase credentials have been filled in")

# ══════════════════════════════════════════════════════════════════
section("4. JavaScript — getElementById References")
# ══════════════════════════════════════════════════════════════════

get_ids = set(re.findall(r"getElementById\('([^']+)'\)", js_raw))
missing_ids = get_ids - html_ids
if not missing_ids:
    ok(f"All {len(get_ids)} getElementById refs have matching HTML elements")
else:
    for mid in sorted(missing_ids):
        fail(f"getElementById('{mid}') — no matching HTML element")

# ══════════════════════════════════════════════════════════════════
section("5. JavaScript — onclick Functions Defined")
# ══════════════════════════════════════════════════════════════════

onclick_fns = set(re.findall(r"onclick=[\"']([a-zA-Z_][a-zA-Z0-9_]*)\(", html))
defined_fns = set(re.findall(r'function ([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', js_raw))
missing_fns = onclick_fns - defined_fns
if not missing_fns:
    ok(f"All {len(onclick_fns)} onclick functions are defined")
else:
    for fn in sorted(missing_fns):
        fail(f"onclick function not defined: {fn}()")

# ══════════════════════════════════════════════════════════════════
section("6. JavaScript — switchTab Page Elements")
# ══════════════════════════════════════════════════════════════════

switch_tabs = set(re.findall(r"switchTab\('([^']+)'\)", js_raw + html))
for tab in sorted(switch_tabs):
    page_id = 'page-' + tab
    if page_id in html_ids: ok(f"switchTab('{tab}') → #{page_id} exists")
    else: fail(f"switchTab('{tab}') → missing #{page_id}")

# ══════════════════════════════════════════════════════════════════
section("7. JavaScript — Required Functions Present")
# ══════════════════════════════════════════════════════════════════

required_fns = [
    # Core
    'init','loadAll','switchTab','uid','esc','closeModal','showToast','setSyncStatus',
    'setupEventListeners',
    # Projects
    'renderProjects','openProjectModal','saveProject','delProject',
    'openPhotoViewer','showLightbox','closeLightbox',
    'handleProjectPhoto','renderEditPhotos','removeEditPhoto',
    # Yarn
    'renderYarn','openYarnModal','saveYarn','delYarn',
    # Needles
    'renderNeedles','openNeedleModal','saveNeedle','delNeedle','getNeedleUsage',
    # Needle helpers (new)
    'autoFillMmFromUs','autoFillUsFromMm','formatMmValue','formatMmField','formatLengthValue',
    # Stash
    'renderAcquire','openAcquireModal','saveAcquire','acquireItem','delAcquire',
    'toggleStashSection',
    # Patterns
    'renderPatterns','openPatternModal','savePattern','delPattern','handlePdfSelect',
    # PDF viewer
    'openPdf','closePdf','renderPdfPage','changePage','saveLastPage',
    'toggleHighlight','saveHlPos','resetZoom',
    # Counter
    'cUp','cDown','cReset','saveCounter',
    # Notes
    'renderNotes','addNote','updateNote','delNote','toggleNotes',
    # Feedback
    'renderFeedback','openFeedbackModal','saveFeedback','delFeedback',
    # Stash notes
    'openStashNote','closeStashNote','saveStashNote','updateStashNoteDots',
    # Backup
    'exportBackup','importBackup',
    # DB converters
    'dbToProject','dbToYarn','dbToPattern',
]

missing_required = [f for f in required_fns if f not in defined_fns]
present_count = len(required_fns) - len(missing_required)
if not missing_required:
    ok(f"All {len(required_fns)} required functions present")
else:
    ok(f"{present_count}/{len(required_fns)} required functions present")
    for fn in missing_required:
        fail(f"Required function missing: {fn}()")

# ══════════════════════════════════════════════════════════════════
section("8. Feature-Specific Checks")
# ══════════════════════════════════════════════════════════════════

# Auto status bump in saveProject
idx = js_raw.find('async function saveProject()')
save_proj = js_raw[idx:idx+700] if idx != -1 else ''
if 'not-started' in save_proj and 'in-progress' in save_proj:
    ok("Auto status bump present in saveProject")
else:
    fail("Auto status bump missing from saveProject")

# selectedOptions used for needle IDs (not old chip selector)
if 'selectedOptions' in js_raw:
    ok("saveProject reads needle IDs from multi-select (selectedOptions)")
else:
    fail("saveProject still using old chip-selector for needles")

# US_TO_MM lookup table
if 'US_TO_MM' in js_raw:
    ok("US_TO_MM needle size lookup table present")
else:
    fail("US_TO_MM lookup table missing")

# MM_TO_US reverse lookup
if 'MM_TO_US' in js_raw:
    ok("MM_TO_US reverse lookup table present")
else:
    fail("MM_TO_US reverse lookup missing")

# formatMmValue called in saveNeedle
idx2 = js_raw.find('async function saveNeedle()')
save_needle = js_raw[idx2:idx2+500] if idx2 != -1 else ''
if 'formatMmValue' in save_needle:
    ok("formatMmValue called in saveNeedle")
else:
    fail("formatMmValue not called in saveNeedle")

if 'formatLengthValue' in save_needle:
    ok("formatLengthValue called in saveNeedle")
else:
    fail("formatLengthValue not called in saveNeedle")

# Needle list row format (not card format)
if 'needle-row-size' in html:
    ok("Needle list-row format used in renderNeedles")
else:
    fail("Needle list-row format missing — may still be using card format")

# Needle sort by mm in renderNeedles
idx3 = js_raw.find('function renderNeedles()')
render_needles = js_raw[idx3:idx3+500] if idx3 != -1 else ''
if 'parseFloat' in render_needles and 'mm' in render_needles:
    ok("Needle sort by mm present in renderNeedles")
else:
    fail("Needle mm sort missing from renderNeedles")

# Needle dropdown sorted in openProjectModal
idx4 = js_raw.find('function openProjectModal(')
open_proj = js_raw[idx4:idx4+2500] if idx4 != -1 else ''
if 'sortedN' in open_proj:
    ok("Needle dropdown sorted by mm in openProjectModal")
else:
    fail("Needle dropdown sort missing from openProjectModal")

# loadAll fetches all 7 tables
tables = re.findall(r"sb\.from\('([^']+)'\)\.select", js_raw)
expected_tables = {'projects','yarn','needles','acquire','patterns','feedback','stash_notes'}
found_tables = set(tables)
missing_tables = expected_tables - found_tables
if not missing_tables:
    ok(f"loadAll fetches all {len(expected_tables)} expected tables")
else:
    fail(f"loadAll missing tables: {missing_tables}")

# Timeout in init
if 'Promise.race' in js_raw and 'timeout' in js_raw:
    ok("Connection timeout present in init()")
else:
    warn("No connection timeout in init() — app may hang silently on network failure")

# Event listeners inside setupEventListeners (not top-level)
top_level_listeners = re.findall(
    r'^(?:document|window|[a-zA-Z]+El?)\.addEventListener',
    js_raw, re.MULTILINE)
if not top_level_listeners:
    ok("No top-level addEventListener calls detected")
else:
    warn(f"Possible top-level addEventListener ({len(top_level_listeners)}) — verify inside setupEventListeners()")

# ══════════════════════════════════════════════════════════════════
section("9. CDN Dependencies")
# ══════════════════════════════════════════════════════════════════

cdns = {
    'PDF.js': 'cdnjs.cloudflare.com/ajax/libs/pdf.js',
    'Supabase JS': 'cdn.jsdelivr.net/npm/@supabase/supabase-js',
    'Google Fonts': 'fonts.googleapis.com',
}
for name, url in cdns.items():
    if url in html: ok(f"CDN loaded: {name}")
    else: warn(f"CDN not found: {name} ({url})")

# PDF.js worker version matches library version
lib_ver = re.search(r'pdf\.js/([\d.]+)/pdf\.min\.js', html)
worker_ver = re.search(r'pdf\.js/([\d.]+)/pdf\.worker', html)
if lib_ver and worker_ver:
    if lib_ver.group(1) == worker_ver.group(1):
        ok(f"PDF.js library and worker versions match ({lib_ver.group(1)})")
    else:
        fail(f"PDF.js version mismatch: lib={lib_ver.group(1)} worker={worker_ver.group(1)}")

# ══════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════

total = len(passed) + len(failed)
print(f"\n{'═'*50}")
print(f"{BOLD}Results: {GREEN}{len(passed)} passed{RESET}{BOLD}, "
      f"{RED}{len(failed)} failed{RESET}{BOLD}, "
      f"{YELLOW}{len(warnings)} warnings{RESET}{BOLD} / {total} total{RESET}")

if failed:
    print(f"\n{RED}{BOLD}FAILED CHECKS:{RESET}")
    for f in failed:
        print(f"  {RED}✗{RESET} {f}")

if warnings:
    print(f"\n{YELLOW}{BOLD}WARNINGS:{RESET}")
    for w in warnings:
        print(f"  {YELLOW}⚠{RESET} {w}")

if not failed:
    print(f"\n{GREEN}{BOLD}✓ All checks passed — safe to upload{RESET}")
else:
    print(f"\n{RED}{BOLD}✗ Fix failures before uploading{RESET}")
    sys.exit(1)

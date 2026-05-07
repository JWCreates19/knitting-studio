#!/usr/bin/env python3
"""
Knitting Studio -- Regression Test Suite
Run: python3 ks_test.py path/to/index.html
"""

import sys
import re
import subprocess
import tempfile
import os

# -- Colour output --
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
    print(f"  {GREEN}+{RESET} {name}")

def fail(name, detail=''):
    failed.append(name)
    msg = f"  {RED}x{RESET} {name}"
    if detail: msg += f"\n      {RED}{detail}{RESET}"
    print(msg)

def warn(name, detail=''):
    warnings.append(name)
    msg = f"  {YELLOW}!{RESET} {name}"
    if detail: msg += f"\n      {YELLOW}{detail}{RESET}"
    print(msg)

def section(title):
    print(f"\n{BOLD}{title}{RESET}")

# -- Load file --
if len(sys.argv) < 2:
    print(f"Usage: python3 ks_test.py path/to/index.html")
    sys.exit(1)

filepath = sys.argv[1]
if not os.path.exists(filepath):
    print(f"{RED}File not found: {filepath}{RESET}")
    sys.exit(1)

with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

print(f"\n{BOLD}Knitting Studio -- Regression Test Suite{RESET}")
print(f"File: {filepath}  ({len(html):,} chars, {html.count(chr(10)):,} lines)")

# Extract JS block
script_start = html.find('<script>') + len('<script>')
script_end   = html.rfind('</script>')
js_raw = html[script_start:script_end]

# Extract CSS block
css_start = html.find('<style>') + len('<style>')
css_end   = html.find('</style>')
css_raw   = html[css_start:css_end]

html_ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))
defined_fns = set(re.findall(r'function ([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', js_raw))

# ==============================================================
section("1. Character Safety")
# ==============================================================

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

spread_ellipsis = len(re.findall(r'[\[\{]\u2026', js_raw))
if spread_ellipsis == 0:
    ok("No ellipsis used as spread operator")
else:
    fail(f"Ellipsis used as spread operator ({spread_ellipsis} occurrences) -- use ... instead")

en_dash_vars = len(re.findall(r'var\(\u2013', css_raw))
if en_dash_vars == 0:
    ok("No en-dashes in CSS var() references")
else:
    fail(f"En-dashes in CSS var() ({en_dash_vars} occurrences) -- breaks CSS variables silently")

SAFE_NONASCII = set('\u2500\u2026\u2014\u00b7\u2192\u2013\u00d7\u2713\u25cf'
                    '\u2197\u26a0\u2715\u25b6\u25c0\u25b2\u25bc\u2600'
                    '\U0001faa1\U0001f4c4\U0001f319\u2714\u21ba\u2190'
                    '\u00b0\u00e9\u00e8\u00e0\u00e2')
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

# ==============================================================
section("2. JavaScript Syntax (node --check)")
# ==============================================================

with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as tmp:
    tmp.write(js_raw)
    tmp_path = tmp.name

try:
    result = subprocess.run(['node', '--check', tmp_path],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ok("node --check passed -- no syntax errors")
    else:
        err = result.stderr.strip().split('\n')
        fail("node --check FAILED -- JavaScript syntax error",
             '\n      '.join(err[:4]))
finally:
    os.unlink(tmp_path)

# ==============================================================
section("3. HTML Structure -- Core Pages & Modals")
# ==============================================================

required_pages = ['page-projects','page-stash','page-patterns','page-feedback','page-moodboard']
for pid in required_pages:
    if pid in html_ids: ok(f"Page element present: #{pid}")
    else: fail(f"Missing page element: #{pid}")

required_modals = ['proj-modal','yarn-modal','needle-modal','acquire-modal',
                   'pat-modal','feedback-modal','palette-modal','moodboard-modal']
for mid in required_modals:
    if mid in html_ids: ok(f"Modal present: #{mid}")
    else: fail(f"Missing modal: #{mid}")

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

if 'YOUR_SUPABASE_URL' in html or 'YOUR_SUPABASE_ANON_KEY' in html:
    warn("Supabase credentials are still placeholders -- replace before deploying")
else:
    ok("Supabase credentials have been filled in")

# ==============================================================
section("4. HTML Structure -- Palette Builder")
# ==============================================================

palette_els = ['palettes-list','palette-modal','palette-modal-title',
               'palette-yarn-picker','palette-yarn-search','palette-swatch-bar-wrap',
               'palette-selected-list','palette-yardage-block',
               'pal-name','pal-pattern','pal-project']
for eid in palette_els:
    if eid in html_ids: ok(f"Palette element present: #{eid}")
    else: fail(f"Missing palette element: #{eid}")

# Link prompt elements
link_els = ['link-prompt-overlay','link-prompt-sub','link-choice-keep','link-choice-replace']
for eid in link_els:
    if eid in html_ids: ok(f"Link prompt element present: #{eid}")
    else: fail(f"Missing link prompt element: #{eid}")

# ==============================================================
section("5. HTML Structure -- Mood Board")
# ==============================================================

mb_page_els = ['page-moodboard','moodboard-grid','moodboard-viewer',
               'mb-viewer-title','mb-content-area','mb-images-grid',
               'mb-notes-ta','mb-img-input','mb-sketch-canvas',
               'mb-canvas-wrap','moodboard-modal','mb-modal-name']
for eid in mb_page_els:
    if eid in html_ids: ok(f"Mood board element present: #{eid}")
    else: fail(f"Missing mood board element: #{eid}")

# Sketch brush buttons
for i in range(4):
    eid = f'mb-brush-{i}'
    if eid in html_ids: ok(f"Sketch brush button present: #{eid}")
    else: fail(f"Missing sketch brush button: #{eid}")

# ==============================================================
section("6. JavaScript -- getElementById References")
# ==============================================================

get_ids = set(re.findall(r"getElementById\('([^']+)'\)", js_raw))
missing_ids = get_ids - html_ids
if not missing_ids:
    ok(f"All {len(get_ids)} getElementById refs have matching HTML elements")
else:
    for mid in sorted(missing_ids):
        fail(f"getElementById('{mid}') -- no matching HTML element")

# ==============================================================
section("7. JavaScript -- onclick Functions Defined")
# ==============================================================

onclick_fns = set(re.findall(r"onclick=[\"']([a-zA-Z_][a-zA-Z0-9_]*)\(", html))
missing_fns = onclick_fns - defined_fns
if not missing_fns:
    ok(f"All {len(onclick_fns)} onclick functions are defined")
else:
    for fn in sorted(missing_fns):
        fail(f"onclick function not defined: {fn}()")

# ==============================================================
section("8. JavaScript -- switchTab Page Elements")
# ==============================================================

switch_tabs = set(re.findall(r"switchTab\('([^']+)'\)", js_raw + html))
for tab in sorted(switch_tabs):
    page_id = 'page-' + tab
    if page_id in html_ids: ok(f"switchTab('{tab}') -> #{page_id} exists")
    else: fail(f"switchTab('{tab}') -> missing #{page_id}")

# ==============================================================
section("9. JavaScript -- Required Functions Present")
# ==============================================================

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
    # Needle helpers
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
    # Palette builder (new)
    'renderPalettes','openPaletteBuilder','renderPaletteYarnPicker',
    'togglePaletteYarn','updatePalettePanel','savePalette','doSavePalette',
    'delPalette','selectLinkChoice','confirmLinkChoice','closeLinkPrompt',
    # Mood board (new)
    'renderMoodboards','openMoodboardModal','saveMoodboard','delMoodboard',
    'openMoodboardViewer','closeMoodboardViewer','renderMbImages',
    'handleMoodboardImage','removeMbImage','saveMoodboardNotes',
    'initMbCanvas','setMbBrush','setMbColor','setMbColorHex',
    'clearMbCanvas','saveMbSketch','setupMbCanvasListeners',
]

missing_required = [f for f in required_fns if f not in defined_fns]
present_count = len(required_fns) - len(missing_required)
if not missing_required:
    ok(f"All {len(required_fns)} required functions present")
else:
    ok(f"{present_count}/{len(required_fns)} required functions present")
    for fn in missing_required:
        fail(f"Required function missing: {fn}()")

# ==============================================================
section("10. Feature-Specific Checks -- Existing Features")
# ==============================================================

# Auto status bump in saveProject
idx = js_raw.find('async function saveProject()')
save_proj = js_raw[idx:idx+700] if idx != -1 else ''
if 'not-started' in save_proj and 'in-progress' in save_proj:
    ok("Auto status bump present in saveProject")
else:
    fail("Auto status bump missing from saveProject")

if 'selectedOptions' in js_raw:
    ok("saveProject reads needle IDs from multi-select (selectedOptions)")
else:
    fail("saveProject still using old chip-selector for needles")

if 'US_TO_MM' in js_raw:
    ok("US_TO_MM needle size lookup table present")
else:
    fail("US_TO_MM lookup table missing")

if 'MM_TO_US' in js_raw:
    ok("MM_TO_US reverse lookup table present")
else:
    fail("MM_TO_US reverse lookup missing")

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

if 'needle-row-size' in html:
    ok("Needle list-row format used in renderNeedles")
else:
    fail("Needle list-row format missing -- may still be using card format")

idx3 = js_raw.find('function renderNeedles()')
render_needles = js_raw[idx3:idx3+500] if idx3 != -1 else ''
if 'parseFloat' in render_needles and 'mm' in render_needles:
    ok("Needle sort by mm present in renderNeedles")
else:
    fail("Needle mm sort missing from renderNeedles")

idx4 = js_raw.find('function openProjectModal(')
open_proj = js_raw[idx4:idx4+2500] if idx4 != -1 else ''
if 'sortedN' in open_proj:
    ok("Needle dropdown sorted by mm in openProjectModal")
else:
    fail("Needle dropdown sort missing from openProjectModal")

# loadAll fetches all 9 tables (updated for palettes + moodboards)
tables = re.findall(r"sb\.from\('([^']+)'\)\.select", js_raw)
expected_tables = {'projects','yarn','needles','acquire','patterns','feedback',
                   'stash_notes','palettes','moodboards'}
found_tables = set(tables)
missing_tables = expected_tables - found_tables
if not missing_tables:
    ok(f"loadAll fetches all {len(expected_tables)} expected tables")
else:
    fail(f"loadAll missing tables: {missing_tables}")

if 'Promise.race' in js_raw and 'timeout' in js_raw:
    ok("Connection timeout present in init()")
else:
    warn("No connection timeout in init() -- app may hang silently on network failure")

top_level_listeners = re.findall(
    r'^(?:document|window|[a-zA-Z]+El?)\.addEventListener',
    js_raw, re.MULTILINE)
if not top_level_listeners:
    ok("No top-level addEventListener calls detected")
else:
    warn(f"Possible top-level addEventListener ({len(top_level_listeners)}) -- verify inside setupEventListeners()")

# ==============================================================
section("11. Feature-Specific Checks -- Palette Builder")
# ==============================================================

# palettes in state
if 'palettes:[]' in js_raw or "palettes:palettes.data" in js_raw or 'state.palettes' in js_raw:
    ok("Palettes present in app state")
else:
    fail("Palettes missing from app state")

# Live swatch update wired to togglePaletteYarn
idx_toggle = js_raw.find('function togglePaletteYarn(')
toggle_yarn = js_raw[idx_toggle:idx_toggle+300] if idx_toggle != -1 else ''
if 'updatePalettePanel' in toggle_yarn:
    ok("togglePaletteYarn calls updatePalettePanel (live swatch update)")
else:
    fail("togglePaletteYarn does not call updatePalettePanel -- swatch bar won't update live")

# updatePalettePanel builds swatch bar
idx_panel = js_raw.find('function updatePalettePanel(')
panel_fn = js_raw[idx_panel:idx_panel+1200] if idx_panel != -1 else ''
if 'palette-swatch-bar' in panel_fn and 'palette-swatch-seg' in panel_fn:
    ok("updatePalettePanel renders swatch bar segments")
else:
    fail("updatePalettePanel missing swatch bar rendering")

# Yardage check uses targetYards from linked project
if 'target_yards' in panel_fn or 'targetYards' in panel_fn:
    ok("updatePalettePanel includes yardage check against project target")
else:
    fail("updatePalettePanel missing yardage check")

# Link prompt shown when project has existing yarn
idx_save_pal = js_raw.find('async function savePalette(')
save_pal = js_raw[idx_save_pal:idx_save_pal+600] if idx_save_pal != -1 else ''
if 'link-prompt-overlay' in save_pal or 'linkPromptPalId' in save_pal:
    ok("savePalette shows link prompt when project already has yarn")
else:
    fail("savePalette missing link prompt logic for existing yarn conflict")

# doSavePalette handles replace vs keep
idx_do = js_raw.find('async function doSavePalette(')
do_save = js_raw[idx_do:idx_do+400] if idx_do != -1 else ''
if 'replace' in do_save or 'yarnOverride' in do_save:
    ok("doSavePalette handles yarn replace option")
else:
    fail("doSavePalette missing yarn replace logic")

# renderPalettes called when stash tab opens
idx_sw = js_raw.find("if(t==='stash')")
stash_render = js_raw[idx_sw:idx_sw+100] if idx_sw != -1 else ''
if 'renderPalettes' in stash_render:
    ok("renderPalettes called when Stash tab opens")
else:
    fail("renderPalettes not called on stash tab switch")

# Palette upsert goes to 'palettes' table
if "sb.from('palettes').upsert" in js_raw:
    ok("Palette saves to 'palettes' Supabase table")
else:
    fail("Palette not saving to 'palettes' table")

# ==============================================================
section("12. Feature-Specific Checks -- Mood Board")
# ==============================================================

# moodboards in state
if 'state.moodboards' in js_raw:
    ok("Moodboards present in app state")
else:
    fail("Moodboards missing from app state")

# moodboard tab renders on switch
idx_mb_sw = js_raw.find("if(t==='moodboard')")
if idx_mb_sw != -1:
    ok("switchTab handles 'moodboard' case")
else:
    fail("switchTab missing 'moodboard' case")

# Viewer opens full-screen (body overflow hidden)
idx_open_mb = js_raw.find('function openMoodboardViewer(')
open_mb = js_raw[idx_open_mb:idx_open_mb+300] if idx_open_mb != -1 else ''
if 'overflow' in open_mb and 'hidden' in open_mb:
    ok("openMoodboardViewer sets body overflow hidden (full-screen)")
else:
    fail("openMoodboardViewer missing full-screen body overflow")

# Viewer close restores overflow
idx_close_mb = js_raw.find('function closeMoodboardViewer(')
close_mb = js_raw[idx_close_mb:idx_close_mb+150] if idx_close_mb != -1 else ''
if 'overflow' in close_mb:
    ok("closeMoodboardViewer restores body overflow")
else:
    fail("closeMoodboardViewer missing body overflow restore")

# Image upload goes to moodboard-images bucket
idx_img = js_raw.find('async function handleMoodboardImage(')
handle_img = js_raw[idx_img:idx_img+300] if idx_img != -1 else ''
if 'moodboard-images' in handle_img:
    ok("Mood board images upload to 'moodboard-images' bucket")
else:
    fail("Mood board image upload not targeting 'moodboard-images' bucket")

# Images stored in moodboards.images jsonb
if "update({images:" in js_raw or "update({images :" in js_raw:
    ok("Mood board images persisted to Supabase (images column)")
else:
    fail("Mood board images not persisted to Supabase")

# Notes saved to Supabase
if "update({notes:" in js_raw or "update({notes :" in js_raw:
    ok("Mood board notes saved to Supabase (notes column)")
else:
    fail("Mood board notes not saved to Supabase")

# Sketch saved as base64 to sketch_data column
idx_sketch = js_raw.find('async function saveMbSketch(')
save_sketch = js_raw[idx_sketch:idx_sketch+400] if idx_sketch != -1 else ''
if 'toDataURL' in save_sketch and ('sketch_data' in save_sketch):
    ok("Sketch saved as PNG dataURL to sketch_data column")
else:
    fail("Sketch not saving to sketch_data column")

# Canvas listeners set up inside setupMbCanvasListeners (not top-level)
if 'function setupMbCanvasListeners(' in js_raw:
    ok("Canvas listeners in dedicated setupMbCanvasListeners function")
else:
    fail("setupMbCanvasListeners function missing")

# setupMbCanvasListeners called from setupEventListeners
idx_sel = js_raw.find('function setupEventListeners(')
setup_el = js_raw[idx_sel:idx_sel+3000] if idx_sel != -1 else ''
if 'setupMbCanvasListeners' in setup_el:
    ok("setupMbCanvasListeners called from setupEventListeners")
else:
    fail("setupMbCanvasListeners not called from setupEventListeners -- canvas won't work")

# Eraser mode implemented (uses background color not transparent)
idx_draw = js_raw.find('function setupMbCanvasListeners(')
canvas_setup = js_raw[idx_draw:idx_draw+800] if idx_draw != -1 else ''
if 'mbIsEraser' in canvas_setup or 'eraser' in canvas_setup.lower():
    ok("Eraser mode implemented in sketch canvas")
else:
    fail("Eraser mode missing from sketch canvas")

# Image deletion also removes from storage
idx_del_img = js_raw.find('async function removeMbImage(')
del_img = js_raw[idx_del_img:idx_del_img+320] if idx_del_img != -1 else ''
if 'moodboard-images' in del_img and 'remove' in del_img:
    ok("removeMbImage deletes from Supabase Storage")
else:
    fail("removeMbImage not cleaning up Supabase Storage")

# Board deletion also cleans up images from storage
idx_del_mb = js_raw.find('async function delMoodboard(')
del_mb = js_raw[idx_del_mb:idx_del_mb+300] if idx_del_mb != -1 else ''
if 'moodboard-images' in del_mb and 'remove' in del_mb:
    ok("delMoodboard cleans up images from Supabase Storage")
else:
    fail("delMoodboard not cleaning up images from Storage on delete")

# ==============================================================
section("13. CDN Dependencies")
# ==============================================================

cdns = {
    'PDF.js': 'cdnjs.cloudflare.com/ajax/libs/pdf.js',
    'Supabase JS': 'cdn.jsdelivr.net/npm/@supabase/supabase-js',
    'Google Fonts': 'fonts.googleapis.com',
}
for name, url in cdns.items():
    if url in html: ok(f"CDN loaded: {name}")
    else: warn(f"CDN not found: {name} ({url})")

lib_ver = re.search(r'pdf\.js/([\d.]+)/pdf\.min\.js', html)
worker_ver = re.search(r'pdf\.js/([\d.]+)/pdf\.worker', html)
if lib_ver and worker_ver:
    if lib_ver.group(1) == worker_ver.group(1):
        ok(f"PDF.js library and worker versions match ({lib_ver.group(1)})")
    else:
        fail(f"PDF.js version mismatch: lib={lib_ver.group(1)} worker={worker_ver.group(1)}")


# ==============================================================
section("14. Structural Correctness — Modal & Section Nesting")
# ==============================================================

import re as _re

def find_page_close(h, open_idx):
    """Find closing </div> index for a page div using recursive matching."""
    depth = 0
    i = open_idx
    while i < len(h):
        if h[i:i+4] == '<div':
            depth += 1; i += 4
        elif h[i:i+6] == '</div>':
            depth -= 1
            if depth == 0: return i
            i += 6
        else:
            i += 1
    return len(h)

all_page_divs = [(m.start(), m.group(0)) for m in _re.finditer(r'<div id="page-[^"]+?"', html)]

# Key modals must NOT be nested inside any page div
top_level_modals = [
    'palette-modal', 'moodboard-modal', 'link-prompt-overlay',
    'moodboard-viewer', 'proj-modal', 'yarn-modal', 'needle-modal',
    'acquire-modal', 'pat-modal', 'feedback-modal',
]

for mid in top_level_modals:
    el_idx = html.find(f'id="{mid}"')
    if el_idx == -1:
        warn(f"#{mid} not found in HTML"); continue
    nested = False
    for page_start, _ in all_page_divs:
        page_close = find_page_close(html, page_start)
        if page_start < el_idx < page_close:
            fail(f"#{mid} NESTED inside page div — will be hidden when page is hidden")
            nested = True; break
    if not nested:
        ok(f"#{mid} is correctly at top level")

# Palette section must be INSIDE page-stash (not floating between pages)
pal_idx = html.find('id="palettes-list"')
stash_open = html.find('<div id="page-stash"')
stash_close = find_page_close(html, stash_open) if stash_open != -1 else -1
if pal_idx != -1 and stash_open != -1:
    if stash_open < pal_idx < stash_close:
        ok("Colour Palettes section is inside #page-stash")
    else:
        fail("Colour Palettes section is NOT inside #page-stash — will render on all tabs")
else:
    fail("Could not verify palette section placement")

# isDemo() must not be called (live app uses demoGuard())
isDemo_calls = js_raw.count('isDemo()')
if isDemo_calls == 0:
    ok("No isDemo() calls — demo guard uses demoGuard() correctly")
else:
    fail(f"isDemo() called {isDemo_calls} times but is not defined — use demoGuard() instead")

# ==============================================================
# SUMMARY
# ==============================================================

total = len(passed) + len(failed)
print(f"\n{'='*50}")
print(f"{BOLD}Results: {GREEN}{len(passed)} passed{RESET}{BOLD}, "
      f"{RED}{len(failed)} failed{RESET}{BOLD}, "
      f"{YELLOW}{len(warnings)} warnings{RESET}{BOLD} / {total} total{RESET}")

if failed:
    print(f"\n{RED}{BOLD}FAILED CHECKS:{RESET}")
    for f in failed:
        print(f"  {RED}x{RESET} {f}")

if warnings:
    print(f"\n{YELLOW}{BOLD}WARNINGS:{RESET}")
    for w in warnings:
        print(f"  {YELLOW}!{RESET} {w}")

if not failed:
    print(f"\n{GREEN}{BOLD}All checks passed -- safe to upload{RESET}")
else:
    print(f"\n{RED}{BOLD}Fix failures before uploading{RESET}")
    sys.exit(1)

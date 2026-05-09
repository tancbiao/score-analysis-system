#!/usr/bin/env python3
"""
Merge v1.53 features (question bank upload, exam paper parser) into v1.51 base.
Uses the old broken file for code and fixes garbled Chinese strings.
"""

import re

# Paths
NEW_FILE = r'index.html'  # Current v1.51 base
OLD_FILE = r'C:\Users\tanc\AppData\Local\Temp\old_index.html'
OUTPUT = r'index.html'  # Overwrite

# Read both files
with open(NEW_FILE, 'rb') as f:
    new_raw = f.read()

with open(OLD_FILE, 'rb') as f:
    old_raw = f.read()

def fix_garbled(text):
    """Fix known garbled Chinese character patterns."""
    replacements = {
        # Common garbled -> correct mappings
        "\u6392\u5e8f\u72b6\ufffd": "\u6392\u5e8f\u72b6\u6001",
        "\ufffd \u5c31\u7eea": "\u2705 \u5c31\u7eea",
        "\ufffd ": "\u274c ",
        "\u5237\u65b0\u9875\ufffd": "\u5237\u65b0\u9875\u9762",
        "\u5df2\u89e3\ufffd ": "\u5df2\u89e3\u6790 ",
        " \ufffd \u4efd": " \u4efd",
        "\u8bfb\u53d6\u5931\ufffd": "\u8bfb\u53d6\u5931\u8d25",
        "": "",
        # Exam paper parser
        "\u4e0d\u652f\u6301\u7684\u6587\u4ef6\u683c\u5f0f": "\u4e0d\u652f\u6301\u7684\u6587\u4ef6\u683c\u5f0f",
        "\ufffd\u4e0a\u4f20": "\uff0c\u8bf7\u4e0a\u4f20",
        "\ufffd .xlsx \u6587\u4ef6": "\u6216 .xlsx \u6587\u4ef6",
        "JSZip\u7ec4\u4ef6\u672a\u52a0\ufffd": "JSZip\u7ec4\u4ef6\u672a\u52a0\u8f7d",
        "docx\u5185\u5bb9\u89e3\u6790\u5931\u8d25\ufffd": "docx\u5185\u5bb9\u89e3\u6790\u5931\u8d25\uff0c\u8bf7",
        # Upload
        "\u67e5\u770b\u9519\u9898\u5bf9\u5e94\u6750\ufffd": "\u67e5\u770b\u9519\u9898\u5bf9\u5e94\u6750\u6599",
        # Various garbled char removals
        "\ufffd": "",
    }
    for garbled, correct in replacements.items():
        text = text.replace(garbled, correct)
    return text

def fix_garbled_bytes(data):
    """Fix garbled Chinese in bytes using known patterns."""
    result = data
    # Try to decode, fix, re-encode
    text = data.decode('utf-8', errors='replace')
    # Remove replacement characters \ufffd
    text = text.replace('\ufffd', '')
    fixed = fix_garbled(text)
    return fixed.encode('utf-8')

# ============================================================
# Strategy: Build the merged file from new base + old file pieces
# ============================================================

new_text = new_raw.decode('utf-8', errors='replace')
old_text = old_raw.decode('utf-8', errors='replace')

# Fix all garbled chars in old text first
old_fixed = fix_garbled(old_text)
# Also remove any remaining replacement chars
old_fixed = old_fixed.replace('\ufffd', '')

# 1. Insert QB Upload HTML after the main upload section
# Find the first upload-section div
main_upload_end = new_text.find('<!-- ===== Info Bar =====')
if main_upload_end == -1:
    main_upload_end = new_text.find('<div id="toastContainer"', 0)

# Find the qb upload HTML in the fixed old text  
qb_html_start = old_fixed.find('id="qbUploadArea"')
# Find the parent div
div_before = old_fixed.rfind('<div class="upload-section"', 0, qb_html_start)
div_after = old_fixed.find('</div>', old_fixed.find('qbFileInput'))
div_after = old_fixed.find('</div>', div_after + 6) + 6

qb_html = old_fixed[div_before:div_after]
print(f"QB HTML length: {len(qb_html)}")
print(f"QB HTML: {qb_html[:120]}...")

# Insert QB HTML after main upload
insert_pos = main_upload_end
if insert_pos > 0:
    # Insert the QB upload section before the info bar
    new_text = new_text[:insert_pos] + '\n' + qb_html + '\n' + new_text[insert_pos:]
    print(f"Inserted QB HTML at position {insert_pos}")
else:
    print("ERROR: Could not find insertion point for QB HTML")

# 2. Extract and insert ExamPaperParser
epp_start_old = old_fixed.find('const ExamPaperParser')
app_start_old = old_fixed.find('\nconst App', epp_start_old)
epp_code = old_fixed[epp_start_old:app_start_old]
print(f"\nExamPaperParser length: {len(epp_code)}")

# Find where to insert in new file (before App declaration)
app_start_new = new_text.find('\nconst App')
# Find the section before App - the ExcelParser and ClassNormalizer end
# Insert ExamPaperParser before App
new_text = new_text[:app_start_new] + '\n\n' + epp_code + '\n' + new_text[app_start_new:]
print(f"Inserted ExamPaperParser at position {app_start_new}")

# 3. Add questionBank property to App object
# Find the App property section
app_props = new_text.find('const App = {')
if app_props > 0:
    # Find the first property line after the opening {
    first_prop = new_text.find('\n  data:', app_props)
    # Add questionBank after data:
    qb_prop = '\n  questionBank: null,  // { questions: {...}, images: {...} }\n'
    # Find the init method
    init_start_new = new_text.find('\n  init()', app_props)
    # Find the _reportSort line to add after it  
    sort_line = new_text.find('_reportSort', app_props)
    if sort_line > 0 and sort_line < init_start_new:
        line_end = new_text.find('\n', sort_line)
        new_text = new_text[:line_end] + qb_prop + new_text[line_end:]
        print("Added questionBank property")
    else:
        # Add before init
        new_text = new_text[:init_start_new] + qb_prop + new_text[init_start_new:]
        print("Added questionBank property before init()")

# 4. Add loadQuestionBank event handlers to init()
# Find the init method's last event handler before it ends
init_text = new_text[new_text.find('\n  init()'):]
# Find the help button handler
help_handler = init_text.find("this.showHelp()")
if help_handler > 0:
    line_start = init_text.rfind('\n', 0, help_handler)
    line_end = init_text.find('\n', help_handler)
    # Find the end of init (the }, line)
    init_end = init_text.find('\n  },', help_handler)
    
    qb_handler_code = '''
    // Question bank upload
    try {
      Util.$('qbFileInput').addEventListener('change', e => {
        if (e.target.files.length) this.loadQuestionBank(e.target.files[0]);
      });
      Util.$('qbUploadArea').addEventListener('click', () => Util.$('qbFileInput').click());
    } catch(e) {}
'''
    # Insert before init's closing }
    init_close = init_text.find('\n  },', help_handler)
    before_init_end = new_text.find('\n  init()') + init_close
    
    # Better: find the position in the full text
    show_help_pos = new_text.find("this.showHelp()")
    if show_help_pos > 0:
        end_of_help_line = new_text.find('\n', show_help_pos)
        new_text = new_text[:end_of_help_line] + qb_handler_code + new_text[end_of_help_line:]
        print("Added QB upload event handlers")

# 5. Add loadQuestionBank method to App
lqb_method_old = old_fixed.find('loadQuestionBank(file)')
if lqb_method_old == -1:
    lqb_method_old = old_fixed.find('loadQuestionBank(file)')

# Find the method boundary
# Search in fixed old text for the complete method
lqb_start = old_fixed.find('\n  loadQuestionBank')
if lqb_start > 0:
    # Find the closing of this method (look for  }, pattern that's not inside nested braces)
    method_end_search = old_fixed[lqb_start+1:]
    depth = 0
    method_end = 0
    in_string = False
    for i, ch in enumerate(method_end_search):
        if ch == '"' or ch == "'" or ch == '`':
            if i > 0 and method_end_search[i-1] != '\\':
                in_string = not in_string
        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    # Found the closing brace
                    method_end = i + 1
                    break
    
    if method_end > 0:
        lqb_method = method_end_search[:method_end]
        # Find where to insert in the new file
        # Insert before the checkLibraries or before processFiles
        check_lib = new_text.find('\n  checkLibraries()')
        new_text = new_text[:check_lib] + '\n' + lqb_method + new_text[check_lib:]
        print(f"Added loadQuestionBank method ({len(lqb_method)} chars)")

# Write the merged file
new_raw_fixed = new_text.encode('utf-8')
with open(OUTPUT, 'wb') as f:
    f.write(new_raw_fixed)

print(f"\nMerged file written: {OUTPUT}")
print(f"Size: {len(new_raw_fixed)} bytes")

# Verify critical Chinese strings
test_strings = ['总数据', 'loadQuestionBank', 'ExamPaperParser', 'questionBank']
for s in test_strings:
    pos = new_raw_fixed.find(s.encode('utf-8'))
    print(f"  '{s}': {'FOUND' if pos >= 0 else 'MISSING'} at byte {pos}")

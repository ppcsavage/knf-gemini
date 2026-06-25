import re
import json

def is_header_or_footer(line):
    stripped = line.strip()
    header_footers = {
        "KOMISJA NADZORU FINANSOWEGO",
        "KOMISJA EGZAMINACYJNA DLA POŚREDNIKÓW KREDYTU HIPOTECZNEGO",
        "Pytania z egzaminów",
        "na pośrednika kredytu hipotecznego",
        "z lat 2024 - 2025",
        "z lat 2018 - 2023",
        "Ponowne wykorzystywanie informacji zawartych na stronie internetowej Komisji Nadzoru Finansowego (www.knf.gov.pl) jest bezpłatne.",
        "Podmiot ponownie wykorzystujący informacje udostępnione w serwisie internetowym KNF jest zobządzany do podania źródła ich pochodzenia poprzez",
        "Podmiot ponownie wykorzystujący informacje udostępnione w serwisie internetowym KNF jest zobowiązany do podania źródła ich pochodzenia poprzez",
        "wskazanie strony internetowej, z której informacje zostały pozyskane",
        "wskazanie strony internetowej, z której informacje zostały pozyskane.",
        "Treść i koncepcja pytań zawartych w teście są przedmiotem praw autorskich",
        "i nie mogą być publikowane lub w inny sposób rozpowszechniane bez zgody Komisji Nadzoru Finansowego"
    }
    for hf in header_footers:
        if stripped.startswith(hf) or hf in stripped:
            return True
    return False

def parse_file(filepath, slices, max_expected, year_group):
    raw_lines = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            cleaned = line.replace("\x0c", "")
            if is_header_or_footer(cleaned):
                raw_lines.append("")
            else:
                raw_lines.append(cleaned.rstrip())
            
    # Find anchors
    anchors = [] # list of (q_num, line_idx)
    for idx, line in enumerate(raw_lines):
        match = re.match(r'^ {0,2}(\d{1,3})\b', line)
        if match:
            val = int(match.group(1))
            if 1 <= val <= max_expected:
                anchors.append((val, idx))
                    
    # Sort anchors by line index
    anchors.sort(key=lambda x: x[1])
    
    # Map q_num to line index
    anchor_map = {}
    for q, ln in anchors:
        if q in anchor_map:
            # Duplicate anchor, choose the one with the answer on the same line if possible
            line_padded = raw_lines[ln].ljust(200)
            ans_txt = line_padded[slices['ans'][0]:slices['ans'][1]].strip()
            if ans_txt in ['A', 'B', 'C']:
                anchor_map[q] = ln
        else:
            anchor_map[q] = ln
            
    # Verify all are present
    missing = [q for q in range(1, max_expected + 1) if q not in anchor_map]
    if missing:
        raise ValueError(f"File {filepath} has missing anchors: {missing}")
    
    # Find boundaries B_q for each q from 1 to max_expected-1
    boundaries = {} # q_num -> boundary_line_idx (inclusive for q)
    
    for q in range(1, max_expected):
        ln_curr = anchor_map[q]
        ln_next = anchor_map[q+1]
        
        # 1. Compute hard upper bound max_b based on uppercase starts
        max_b = ln_next - 1
        
        def get_col_text(ln, col):
            if ln < 0 or ln >= len(raw_lines): return ""
            line_padded = raw_lines[ln].ljust(200)
            return line_padded[slices[col][0]:slices[col][1]].strip()
            
        for ln in range(ln_curr + 1, ln_next):
            for col in ['q', 'a', 'b', 'c']:
                txt = get_col_text(ln, col)
                prev_txt = get_col_text(ln - 1, col)
                if txt and not prev_txt:
                    if txt[0].isupper():
                        max_b = min(max_b, ln - 1)
                        break
            else:
                continue
            break
            
        max_b = max(ln_curr, max_b)
        
        # 2. Optimal boundary b is min(max_b, midpoint) using the mathematically correct inclusive midpoint formula
        midpoint = ln_curr + (ln_next - ln_curr - 1) // 2
        b = min(max_b, midpoint)
        
        boundaries[q] = b
        
    # Extract questions
    questions = []
    
    for idx, (q, ln) in enumerate(anchors):
        if ln != anchor_map[q]:
            continue
            
        prev_q = None
        for prev_candidate in range(q-1, 0, -1):
            if prev_candidate in anchor_map:
                prev_q = prev_candidate
                break
                
        start_ln = 0 if prev_q is None else boundaries[prev_q] + 1
        
        next_q = None
        for next_candidate in range(q+1, max_expected + 1):
            if next_candidate in anchor_map:
                next_q = next_candidate
                break
                
        end_ln = len(raw_lines) - 1 if next_q is None else boundaries[q]
        
        q_lines = []
        a_lines = []
        b_lines = []
        c_lines = []
        ans_val = ""
        
        for ln in range(start_ln, end_ln + 1):
            line_padded = raw_lines[ln].ljust(200)
            
            q_txt = line_padded[slices['q'][0]:slices['q'][1]].strip()
            if ln == anchor_map[q]:
                q_txt = re.sub(r'^\d+\s*', '', q_txt)
                
            a_txt = line_padded[slices['a'][0]:slices['a'][1]].strip()
            b_txt = line_padded[slices['b'][0]:slices['b'][1]].strip()
            c_txt = line_padded[slices['c'][0]:slices['c'][1]].strip()
            ans_txt = line_padded[slices['ans'][0]:slices['ans'][1]].strip()
            
            if q_txt: q_lines.append(q_txt)
            if a_txt: a_lines.append(a_txt)
            if b_txt: b_lines.append(b_txt)
            if c_txt: c_lines.append(c_txt)
            if ans_txt in ['A', 'B', 'C']: ans_val = ans_txt
            
        def clean_field(txt):
            t = re.sub(r'\s+', ' ', txt)
            t = re.sub(r'^(PYTANIE|Odp\.|A|B|C)\s+', '', t, flags=re.IGNORECASE)
            t = re.sub(r'^\.\s*', '', t)
            return t.strip()
            
        questions.append({
            'id': q,
            'question': clean_field(" ".join(q_lines)),
            'a': clean_field(" ".join(a_lines)),
            'b': clean_field(" ".join(b_lines)),
            'c': clean_field(" ".join(c_lines)),
            'answer': ans_val,
            'year_group': year_group
        })
        
    return questions

# 2024-2025
slices_24_25 = {
    'lp': (0, 6),
    'q': (6, 48),
    'a': (48, 85),
    'b': (85, 121),
    'c': (121, 158),
    'ans': (158, 200)
}
q_24_25 = parse_file("pdfs/questions_2024_2025_layout.txt", slices_24_25, 150, "2024-2025")
print(f"Parsed 2024-2025: {len(q_24_25)} questions.")

# 2018-2023
slices_18_23 = {
    'lp': (0, 3),
    'q': (3, 46),
    'a': (46, 82),
    'b': (82, 112),
    'c': (112, 145),
    'ans': (145, 200)
}
q_18_23 = parse_file("pdfs/questions_2018_2023_layout.txt", slices_18_23, 206, "2018-2023")
print(f"Parsed 2018-2023: {len(q_18_23)} questions.")

# Save to json
all_questions = q_18_23 + q_24_25
with open("questions.json", "w", encoding="utf-8") as f:
    json.dump(all_questions, f, ensure_ascii=False, indent=2)
print(f"Saved {len(all_questions)} questions to questions.json")

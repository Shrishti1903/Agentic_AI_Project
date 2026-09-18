from pdfminer.high_level import extract_text
text = extract_text('AI_Agent_Project_Rules.pdf')
with open('rules_text.txt','w', encoding='utf-8') as f:
    f.write(text)
print('WROTE rules_text.txt; length=', len(text))

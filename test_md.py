import requests, re
resp = requests.post('http://localhost:5000/api/v1/chat/stream',
    json={'message':'用python写个hello world函数'}, stream=True)
chunks = []
for line in resp.iter_lines():
    if line:
        text = line.decode('utf-8')
        chunks.append(text)
        if len(chunks) <= 5 or text.startswith('data: [DONE]'):
            print(repr(text[:80]))
print(f'Total chunks: {len(chunks)}')
full = ''
for c in chunks:
    m = re.match(r'data: (.*)', c)
    if m and m.group(1) != '[DONE]':
        full += m.group(1)
has_md = '```' in full or '**' in full or '##' in full or '>>>' in full
print(f'Full text: {len(full)} chars, has_md_syntax: {has_md}')
print(f'Content: {full[:300]}')

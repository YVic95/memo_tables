function markdownToHtml(text) {
    if (!text) return '';

    let normalized = text
        .replace(/(?<!\n)(?=## )/g, '\n')
        .replace(/(?<!\n)(?=### )/g, '\n')
        .replace(/(?<!\n)(?=# )/g, '\n')
        .trim();

    const rawLines = normalized.split('\n');

    const lines = rawLines.filter(raw => {
        const cleaned = raw.replace(/[\s\u00A0\u200B\uFEFF]+/g, '');
        return !/^#{1,6}$/.test(cleaned);
    });

    function inline(s) {
        return s
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');
    }

    const tokens = [];
    let sawFirstHeading = false;
    for (const raw of lines) {
        const line = raw.trim();
        if (!line) continue;
        let m;
        if ((m = line.match(/^#{1,3}\s+(.+)/))) {
            if (!sawFirstHeading) {
                tokens.push({ type: 'h2', text: m[1] });
                sawFirstHeading = true;
            } else {
                tokens.push({ type: 'h3', text: m[1] });
            }
        }
        else if ((m = line.match(/^\d+\.\s+(.+)/))) tokens.push({ type: 'ol', text: m[1] });
        else if ((m = line.match(/^[-*]\s+(.+)/))) tokens.push({ type: 'ul', text: m[1] });
        else tokens.push({ type: 'p', text: line });
    }

    const out = [];
    let i = 0;
    while (i < tokens.length) {
        const t = tokens[i];

        if (t.type === 'h2') { out.push('<h2>' + inline(t.text) + '</h2>'); i++; continue; }
        if (t.type === 'h3') { out.push('<h3>' + inline(t.text) + '</h3>'); i++; continue; }
        if (t.type === 'p')  { out.push('<p>' + inline(t.text) + '</p>'); i++; continue; }

        if (t.type === 'ol') {
            out.push('<ol>');
            while (i < tokens.length && tokens[i].type === 'ol') {
                const item = tokens[i];
                i++;
                let nested = '';
                if (i < tokens.length && tokens[i].type === 'ul') {
                    nested = '<ul>';
                    while (i < tokens.length && tokens[i].type === 'ul') {
                        nested += '<li>' + inline(tokens[i].text) + '</li>';
                        i++;
                    }
                    nested += '</ul>';
                }
                out.push('<li>' + inline(item.text) + nested + '</li>');
            }
            out.push('</ol>');
            continue;
        }

        if (t.type === 'ul') {
            out.push('<ul>');
            while (i < tokens.length && tokens[i].type === 'ul') {
                out.push('<li>' + inline(tokens[i].text) + '</li>');
                i++;
            }
            out.push('</ul>');
            continue;
        }

        i++;
    }

    return out.join('\n');
}
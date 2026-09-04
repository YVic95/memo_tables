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

    function parsePipeTable(startIdx) {
        const headerLine = lines[startIdx].trim();
        const separatorLine = lines[startIdx + 1]?.trim();
        if (!separatorLine || !/^\|[\s\-:|]+\|$/.test(separatorLine)) {
            return null;
        }

        const splitCells = (line) =>
            line.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());

        const headers = splitCells(headerLine);
        const rows = [];
        let i = startIdx + 2;
        while (i < lines.length && lines[i].trim().startsWith('|')) {
            rows.push(splitCells(lines[i].trim()));
            i++;
        }

        return { headers, rows, endIdx: i };
    }

    const tokens = [];
    let sawFirstHeading = false;
    let i = 0;
    while (i < lines.length) {
        const line = lines[i].trim();
        if (!line) { i++; continue; }

        if (line.startsWith('|')) {
            const table = parsePipeTable(i);
            if (table) {
                tokens.push({ type: 'table', headers: table.headers, rows: table.rows });
                i = table.endIdx;
                continue;
            }
        }

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
        i++;
    }

    const out = [];
    let j = 0;
    while (j < tokens.length) {
        const t = tokens[j];

        if (t.type === 'h2') { out.push('<h2>' + inline(t.text) + '</h2>'); j++; continue; }
        if (t.type === 'h3') { out.push('<h3>' + inline(t.text) + '</h3>'); j++; continue; }
        if (t.type === 'p')  { out.push('<p>' + inline(t.text) + '</p>'); j++; continue; }

        if (t.type === 'table') {
            out.push('<table>');
            out.push('<thead><tr>' + t.headers.map(h => '<th>' + inline(h) + '</th>').join('') + '</tr></thead>');
            out.push('<tbody>');
            for (const row of t.rows) {
                out.push('<tr>' + row.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>');
            }
            out.push('</tbody></table>');
            j++;
            continue;
        }

        if (t.type === 'ol') {
            out.push('<ol>');
            while (j < tokens.length && tokens[j].type === 'ol') {
                const item = tokens[j];
                j++;
                let nested = '';
                if (j < tokens.length && tokens[j].type === 'ul') {
                    nested = '<ul>';
                    while (j < tokens.length && tokens[j].type === 'ul') {
                        nested += '<li>' + inline(tokens[j].text) + '</li>';
                        j++;
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
            while (j < tokens.length && tokens[j].type === 'ul') {
                out.push('<li>' + inline(tokens[j].text) + '</li>');
                j++;
            }
            out.push('</ul>');
            continue;
        }

        j++;
    }

    return out.join('\n');
}
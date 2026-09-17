(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.skeletonTableSerializer = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  function splitPipeTableBlocks(markdown) {
    if (typeof markdown !== 'string' || !markdown.trim()) {
      return [];
    }

    const lines = markdown.split('\n');
    const blocks = [];
    let other = [];
    let i = 0;

    const flushOther = () => {
      const content = other.join('\n');
      if (content.trim()) {
        blocks.push({ isTable: false, content });
      }
      other = [];
    };

    while (i < lines.length) {
      const line = lines[i].trim();
      const separator = i + 1 < lines.length ? lines[i + 1].trim() : '';
      if (line.startsWith('|') && /^\|[\s\-:|]+\|$/.test(separator)) {
        flushOther();

        const tableLines = [lines[i], lines[i + 1]];
        i += 2;
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          tableLines.push(lines[i]);
          i++;
        }
        blocks.push({ isTable: true, content: tableLines.join('\n') });
      } else {
        other.push(lines[i]);
        i++;
      }
    }

    flushOther();
    return blocks;
  }

  function tableBlockColumnCount(markdown) {
    const blocks = splitPipeTableBlocks(markdown);
    const firstTable = blocks.find(b => b.isTable);
    if (!firstTable) {
      return 0;
    }
    const headerLine = firstTable.content.split('\n')[0]
      .replace(/^\|/, '')
      .replace(/\|$/, '');
    return headerLine.split('|').length;
  }

  function withRuleHeading(title, content) {
    const trimmed = String(title || '').trim().replace(/^#+\s*/, '');
    return trimmed ? '## ' + trimmed + '\n\n' + content : content;
  }

  function resolveSkeletonTableReplacement(category, markdown) {
    if (typeof markdown !== 'string' || !markdown.trim()) {
      return null;
    }

    const firstLine = markdown.split('\n').find(line => line.trim());
    if (!firstLine || !firstLine.trim().startsWith('## ')) {
      return null;
    }

    const tableTitle = firstLine.trim().slice(3).trim();
    if (!tableTitle) {
      return null;
    }

    return { category, tableTitle, markdown };
  }

  function reduceSkeletonReplacements(replacements) {
    const latest = new Map();
    (replacements || []).forEach(replacement => {
      const resolved = resolveSkeletonTableReplacement(replacement.category, replacement.markdown);
      if (resolved) {
        latest.set(resolved.category + '\u0000' + resolved.tableTitle, resolved);
      }
    });
    return Array.from(latest.values());
  }

  function tableElementToMarkdown(tableEl) {
    const getCells = (tr) =>
      Array.from(tr.children).map(cell => cell.textContent.trim());

    const headerRow = tableEl.querySelectorAll('thead tr')[0];
    if (!headerRow) {
      return '';
    }

    const headerCells = getCells(headerRow);
    const separatorRow =
      '| ' + headerCells.map(() => '---').join(' | ') + ' |';
    const bodyRows = Array.from(tableEl.querySelectorAll('tbody tr')).map(tr =>
      '| ' + getCells(tr).join(' | ') + ' |',
    );

    return ['| ' + headerCells.join(' | ') + ' |', separatorRow]
      .concat(bodyRows)
      .join('\n');
  }

  return {
    splitPipeTableBlocks,
    tableBlockColumnCount,
    tableElementToMarkdown,
    withRuleHeading,
    resolveSkeletonTableReplacement,
    reduceSkeletonReplacements,
  };
});

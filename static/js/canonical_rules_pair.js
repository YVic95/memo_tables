// Keeps the Rule Catalogue's language pair selected across page reloads.
// The chosen pair is remembered in localStorage and mirrored into the URL, so
// the server can render the section with the pair already selected and its
// rules already listed

const CANONICAL_RULES_PAIR_STORAGE_KEY = 'canonicalRulesPairId';
const CANONICAL_RULES_PAIR_SELECT_ID = 'canonical-rules-pair-select';
const CANONICAL_RULES_PAIR_PANEL_ID = 'canonical-rules-panel';
const CANONICAL_RULES_PAIR_PARAM = 'pair_id';
const HTMX_HISTORY_PATH_KEY = 'htmx-current-path-for-history';

function getPairSelect(doc) {
    return doc.getElementById(CANONICAL_RULES_PAIR_SELECT_ID);
}

function getRenderedPairId(doc) {
    const panel = doc.getElementById(CANONICAL_RULES_PAIR_PANEL_ID);
    return (panel && panel.dataset.pairId) || '';
}

function hasPairOption(select, pairId) {
    return Array.from(select.options || []).some(option => option.value === pairId);
}

function getStoredPairId() {
    return localStorage.getItem(CANONICAL_RULES_PAIR_STORAGE_KEY) || '';
}

// htmx caches each page under the path it pushed. Rewriting the URL behind its
// back would make the cache miss and its restore swap a bare fragment into the
// page, so keep the key htmx will look up in step.
function syncHtmxHistoryPath(url) {
    try {
        const path = url.pathname.replace(/\/+$/, '') || '/';
        const key = path + url.search;
        if (window.sessionStorage.getItem(HTMX_HISTORY_PATH_KEY) !== null) {
            window.sessionStorage.setItem(HTMX_HISTORY_PATH_KEY, key);
        }
    } catch (ignored) {
        // Session storage can be unavailable; htmx then falls back to the live URL.
    }
}

function updateUrlPairId(pairId) {
    const url = new URL(window.location.href);
    if (pairId) {
        url.searchParams.set(CANONICAL_RULES_PAIR_PARAM, pairId);
    } else {
        url.searchParams.delete(CANONICAL_RULES_PAIR_PARAM);
    }
    window.history.replaceState(window.history.state, '', url.toString());
    syncHtmxHistoryPath(url);
}

function handleCanonicalRulesPairChange(event) {
    const select = event.target;
    if (!select || select.id !== CANONICAL_RULES_PAIR_SELECT_ID) {
        return;
    }
    const pairId = select.value;
    if (pairId) {
        localStorage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, pairId);
    } else {
        localStorage.removeItem(CANONICAL_RULES_PAIR_STORAGE_KEY);
    }
    updateUrlPairId(pairId);
}

function restoreCanonicalRulesPair(doc = document) {
    const select = getPairSelect(doc);
    if (!select) {
        return;
    }

    const storedPairId = getStoredPairId();
    if (!storedPairId || !hasPairOption(select, storedPairId)) {
        return;
    }
    if (getRenderedPairId(doc) === storedPairId) {
        return;
    }

    const panel = doc.getElementById(CANONICAL_RULES_PAIR_PANEL_ID);
    const panelUrl = select.getAttribute('hx-get');
    if (!panel || !panelUrl || typeof htmx === 'undefined') {
        return;
    }

    select.value = storedPairId;
    // htmx announces every node it processes, so the section is seen several
    // times per swap. Claim the pair up front: the request below will show it.
    const renderedPairId = panel.dataset.pairId;
    panel.dataset.pairId = storedPairId;
    updateUrlPairId(storedPairId);
    const request = htmx.ajax('GET', panelUrl, {
        target: panel,
        swap: 'outerHTML',
        values: { [CANONICAL_RULES_PAIR_PARAM]: storedPairId },
    });
    if (request && typeof request.catch === 'function') {
        request.catch(() => {
            // Nothing was rendered, so let the next pass try again.
            if (panel.dataset.pairId === storedPairId) {
                panel.dataset.pairId = renderedPairId;
            }
        });
    }
}

function initCanonicalRulesPairPersistence(doc = document) {
    doc.addEventListener('change', handleCanonicalRulesPairChange);
    // htmx fires this on the page load and as it processes swapped-in content.
    doc.addEventListener('htmx:load', () => restoreCanonicalRulesPair(doc));
}

if (typeof document !== 'undefined') {
    initCanonicalRulesPairPersistence(document);
}

if (typeof module === 'object' && module.exports) {
    module.exports = {
        CANONICAL_RULES_PAIR_STORAGE_KEY,
        initCanonicalRulesPairPersistence,
    };
}

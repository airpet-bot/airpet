export const LEFT_PANEL_DEFAULT_WIDTH = 350;
export const LEFT_PANEL_MIN_WIDTH = 260;
export const LEFT_PANEL_MAX_WIDTH = 720;
export const LEFT_PANEL_MIN_MAIN_WIDTH = 360;
export const LEFT_PANEL_RAIL_WIDTH = 8;
const LEFT_PANEL_COLLAPSE_THRESHOLD = 90;
const LEFT_PANEL_WIDTH_STORAGE_KEY = 'airpet_left_panel_width';
const LEFT_PANEL_COLLAPSED_STORAGE_KEY = 'airpet_left_panel_collapsed';

export function normalizeStoredPanelWidth(
    value,
    fallback = LEFT_PANEL_DEFAULT_WIDTH,
) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function getLeftPanelWidthBounds(
    viewportWidth,
    {
        minWidth = LEFT_PANEL_MIN_WIDTH,
        maxWidth = LEFT_PANEL_MAX_WIDTH,
        minMainWidth = LEFT_PANEL_MIN_MAIN_WIDTH,
        railWidth = LEFT_PANEL_RAIL_WIDTH,
    } = {},
) {
    const normalizedViewport = Math.max(Number(viewportWidth) || 0, 0);
    const availableWidth = Math.max(
        normalizedViewport - minMainWidth - railWidth,
        0,
    );
    const effectiveMin = Math.min(minWidth, availableWidth);
    const effectiveMax = Math.max(
        effectiveMin,
        Math.min(maxWidth, availableWidth),
    );
    return {
        min: Math.round(effectiveMin),
        max: Math.round(effectiveMax),
    };
}

export function clampLeftPanelWidth(width, viewportWidth, options = {}) {
    const bounds = getLeftPanelWidthBounds(viewportWidth, options);
    const requested = normalizeStoredPanelWidth(width);
    return Math.round(Math.min(Math.max(requested, bounds.min), bounds.max));
}

export function initializeLeftPanelLayout({
    panel,
    rail,
    resizeHandle,
    toggleButton,
    restoreButton,
    windowObject = window,
    documentObject = document,
}) {
    if (!panel) return null;

    let lastExpandedWidth = normalizeStoredPanelWidth(
        readStorage(windowObject, LEFT_PANEL_WIDTH_STORAGE_KEY),
        LEFT_PANEL_DEFAULT_WIDTH,
    );
    let refreshHandle = null;

    const getViewportWidth = () => (
        documentObject.documentElement?.clientWidth
        || windowObject.innerWidth
        || 0
    );

    const scheduleLayoutRefresh = () => {
        if (refreshHandle !== null) return;
        refreshHandle = windowObject.requestAnimationFrame(() => {
            refreshHandle = null;
            windowObject.dispatchEvent(new windowObject.Event('resize'));
        });
    };

    const applyWidth = (
        widthPx,
        {
            persist = true,
            refresh = true,
        } = {},
    ) => {
        const clamped = clampLeftPanelWidth(widthPx, getViewportWidth());
        lastExpandedWidth = clamped;
        panel.style.setProperty('--left-panel-width', `${clamped}px`);

        const bounds = getLeftPanelWidthBounds(getViewportWidth());
        if (resizeHandle) {
            resizeHandle.setAttribute('aria-valuemin', String(bounds.min));
            resizeHandle.setAttribute('aria-valuemax', String(bounds.max));
            resizeHandle.setAttribute('aria-valuenow', String(clamped));
        }
        if (persist) {
            writeStorage(
                windowObject,
                LEFT_PANEL_WIDTH_STORAGE_KEY,
                clamped,
            );
        }
        if (refresh) scheduleLayoutRefresh();
    };

    const updateToggleButton = () => {
        const isCollapsed = panel.classList.contains('collapsed');
        if (toggleButton) {
            toggleButton.textContent = '‹';
            toggleButton.title = 'Collapse left panel';
            toggleButton.setAttribute(
                'aria-expanded',
                String(!isCollapsed),
            );
        }
        if (restoreButton) {
            restoreButton.hidden = !isCollapsed;
            restoreButton.setAttribute(
                'aria-expanded',
                String(!isCollapsed),
            );
        }
        rail?.classList.toggle('collapsed', isCollapsed);
    };

    const setCollapsed = (
        isCollapsed,
        {
            persist = true,
            refresh = true,
        } = {},
    ) => {
        if (isCollapsed) {
            const currentWidth = Math.round(
                panel.getBoundingClientRect().width,
            );
            if (currentWidth > LEFT_PANEL_COLLAPSE_THRESHOLD) {
                lastExpandedWidth = currentWidth;
                if (persist) {
                    writeStorage(
                        windowObject,
                        LEFT_PANEL_WIDTH_STORAGE_KEY,
                        currentWidth,
                    );
                }
            }
            panel.classList.add('collapsed');
            panel.setAttribute('aria-hidden', 'true');
            panel.setAttribute('inert', '');
        } else {
            panel.classList.remove('collapsed');
            panel.removeAttribute('aria-hidden');
            panel.removeAttribute('inert');
            applyWidth(lastExpandedWidth, {
                persist,
                refresh: false,
            });
        }

        if (persist) {
            writeStorage(
                windowObject,
                LEFT_PANEL_COLLAPSED_STORAGE_KEY,
                isCollapsed,
            );
        }
        updateToggleButton();
        if (refresh) scheduleLayoutRefresh();
    };

    applyWidth(lastExpandedWidth, {
        persist: false,
        refresh: false,
    });
    setCollapsed(
        readStorage(
            windowObject,
            LEFT_PANEL_COLLAPSED_STORAGE_KEY,
        ) === 'true',
        {
            persist: false,
            refresh: false,
        },
    );

    toggleButton?.addEventListener('click', () => {
        setCollapsed(true);
        restoreButton?.focus();
    });

    restoreButton?.addEventListener('click', () => {
        setCollapsed(false);
        toggleButton?.focus();
    });

    resizeHandle?.addEventListener('mousedown', (event) => {
        if (panel.classList.contains('collapsed')) return;

        event.preventDefault();
        panel.classList.add('resizing');
        rail?.classList.add('resizing');
        let collapsedByDrag = false;
        const previousUserSelect = documentObject.body.style.userSelect;
        const previousCursor = documentObject.body.style.cursor;
        documentObject.body.style.userSelect = 'none';
        documentObject.body.style.cursor = 'ew-resize';

        const handleMouseMove = (moveEvent) => {
            if (collapsedByDrag) return;
            const bodyRect = documentObject.body.getBoundingClientRect();
            const desiredWidth = moveEvent.clientX - bodyRect.left;
            if (desiredWidth <= LEFT_PANEL_COLLAPSE_THRESHOLD) {
                collapsedByDrag = true;
                setCollapsed(true);
                return;
            }
            applyWidth(desiredWidth);
        };

        const handleMouseUp = () => {
            documentObject.removeEventListener(
                'mousemove',
                handleMouseMove,
            );
            documentObject.removeEventListener('mouseup', handleMouseUp);
            panel.classList.remove('resizing');
            rail?.classList.remove('resizing');
            documentObject.body.style.userSelect = previousUserSelect;
            documentObject.body.style.cursor = previousCursor;
            scheduleLayoutRefresh();
        };

        documentObject.addEventListener('mousemove', handleMouseMove);
        documentObject.addEventListener('mouseup', handleMouseUp);
    });

    resizeHandle?.addEventListener('dblclick', () => {
        setCollapsed(!panel.classList.contains('collapsed'));
    });

    resizeHandle?.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            return;
        }
        event.preventDefault();

        if (panel.classList.contains('collapsed')) {
            if (event.key === 'ArrowRight' || event.key === 'End') {
                setCollapsed(false);
            }
            return;
        }

        const bounds = getLeftPanelWidthBounds(getViewportWidth());
        let nextWidth = lastExpandedWidth;
        if (event.key === 'ArrowLeft') nextWidth -= 20;
        if (event.key === 'ArrowRight') nextWidth += 20;
        if (event.key === 'Home') nextWidth = bounds.min;
        if (event.key === 'End') nextWidth = bounds.max;
        applyWidth(nextWidth);
    });

    windowObject.addEventListener('resize', () => {
        if (panel.classList.contains('collapsed')) return;
        const clamped = clampLeftPanelWidth(
            lastExpandedWidth,
            getViewportWidth(),
        );
        if (clamped !== lastExpandedWidth) {
            applyWidth(clamped, { refresh: false });
        }
    });

    scheduleLayoutRefresh();
    return {
        applyWidth,
        setCollapsed,
    };
}

function readStorage(windowObject, key) {
    try {
        return windowObject.localStorage.getItem(key);
    } catch (_error) {
        return null;
    }
}

function writeStorage(windowObject, key, value) {
    try {
        windowObject.localStorage.setItem(key, String(value));
    } catch (_error) {
        // Layout persistence is optional in restricted browser contexts.
    }
}

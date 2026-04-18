/**
 * Headless / Playwright flows use `?test_mode=1` to skip WebGL (see test_browser_integration).
 * Only explicit truthy values disable the viewport; `test_mode=0` does not.
 */
export function isViewportWebGlDisabledForTests() {
  const raw = new URLSearchParams(window.location.search).get('test_mode');
  if (raw === null) {
    return false;
  }
  const s = raw.trim().toLowerCase();
  return s === '' || s === '1' || s === 'true' || s === 'yes';
}

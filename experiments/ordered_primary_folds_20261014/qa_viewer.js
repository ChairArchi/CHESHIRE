// Execute the actual fragment script against a minimal DOM. This verifies
// interaction/state logic and image bindings, not browser layout or rendering.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const viewer = path.resolve(process.argv[2]);
const html = fs.readFileSync(viewer, 'utf8');
assert(Buffer.byteLength(html) < 1000000);
assert(!html.includes('__IMAGE_DATA__') && !html.includes('__DEFAULT_IMAGE__'));
const script = html.match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
const buttons = [...html.matchAll(/<button\s+([^>]+)>/g)].map(match => {
  const attrs = {};
  for (const item of match[1].matchAll(/([\w-]+)="([^"]*)"/g)) attrs[item[1]] = item[2];
  return {attrs, dataset: {state: attrs['data-state'], view: attrs['data-view']}, handlers: {},
    setAttribute(name, value) {this.attrs[name] = value;},
    addEventListener(name, handler) {this.handlers[name] = handler;}};
});
assert(buttons.length === 5);
const picture = {};
const caption = {};
const root = {
  querySelector(selector) {
    if (selector === '[data-image]') return picture;
    if (selector === '[data-caption]') return caption;
    throw Error('Unexpected selector: '+selector);
  },
  querySelectorAll(selector) {
    if (selector === '[data-state]') return buttons.filter(x => x.dataset.state);
    if (selector === '[data-view]') return buttons.filter(x => x.dataset.view);
    throw Error('Unexpected selector: '+selector);
  }
};
const saved = [];
const events = {};
const window = {
  openai: {widgetState: null, setWidgetState(value) {saved.push(value); return Promise.resolve();}},
  addEventListener(name, callback) {events[name] = callback;}
};
vm.runInNewContext(script, {document: {getElementById(id) {
  assert(id === 'cheshire-ordered-primary-folds'); return root;
}}, window, Object});
assert(caption.textContent === '주축 강조 · 기둥 몸체');
assert(saved.length === 0);
const actualImages = new Set();
let interactions = 0;
for (const state of ['before', 'after']) {
  buttons.find(x => x.dataset.state === state).handlers.click();
  for (const view of ['front', 'body', 'close']) {
    buttons.find(x => x.dataset.view === view).handlers.click();
    assert(picture.src.startsWith('data:image/jpeg;base64,'));
    actualImages.add(picture.src);
    assert(buttons.filter(x => x.dataset.state && x.attrs['aria-pressed'] === 'true').length === 1);
    assert(buttons.filter(x => x.dataset.view && x.attrs['aria-pressed'] === 'true').length === 1);
    assert(saved.at(-1).modelContent.state === state && saved.at(-1).modelContent.view === view);
    assert(picture.alt.includes('렌더'));
    interactions++;
  }
}
assert(actualImages.size === 6);
const savedBeforeRestore = saved.length;
events['openai:set_globals']({detail: {globals: {widgetState: {modelContent: {
  comparison: 'ordered-primary-folds', state: 'before', view: 'close'
}}}}});
assert(caption.textContent === '이전 결과 · 근접');
assert(saved.length === savedBeforeRestore);
events['openai:set_globals']({detail: {globals: {widgetState: {modelContent: {
  comparison: 'unrelated', state: 'after', view: 'front'
}}}}});
assert(caption.textContent === '이전 결과 · 근접');
const result = {viewer, tests: 'Actual script executed against minimal DOM',
  states: 2, views: 3, combinations_verified: interactions, distinct_inline_images: actualImages.size,
  default_after_body: true, pressed_states: true, captions: true, image_updates: true,
  widget_state_saved_on_click: true, widget_state_restore: true, no_save_on_restore: true,
  browser_layout_inspected: false, passed: true};
fs.writeFileSync(path.join(path.dirname(viewer), 'INTERACTION_QA.json'), JSON.stringify(result, null, 2)+'\n');
console.log(JSON.stringify(result, null, 2));

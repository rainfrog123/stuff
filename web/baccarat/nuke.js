// Clone and redefine listeners to do nothing
const dummyFn = () => {};
['blur', 'focus', 'visibilitychange'].forEach(event => {
  const clone = document.createElement('iframe');
  document.body.appendChild(clone);
  const old = getEventListeners(window)[event] || [];
  old.forEach(({listener}) => window.removeEventListener(event, listener));
  window.addEventListener(event, dummyFn, true);
});

// Send guests to login and bring them back to the page they were on afterwards.

/** Router state for a redirect to /login, remembering the current page. */
export function loginState(location) {
  return { from: `${location.pathname}${location.search}` };
}

/** Where to go after login/registration: the remembered page if it is a safe in-app path. */
export function afterLoginPath(location) {
  const from = location.state?.from;
  if (typeof from !== 'string' || !from.startsWith('/') || from.startsWith('//')) return '/';
  if (/^\/(login|register)(\/|\?|$)/.test(from)) return '/';
  return from;
}

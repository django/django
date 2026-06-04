let prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

function setTheme(mode) {
  if (mode !== 'light' && mode !== 'dark' && mode !== 'auto') {
    console.error(`Got invalid theme mode: ${mode}. Resetting to auto.`);
    mode = 'auto';
  }
  document.documentElement.dataset.theme = mode;
  // trim host to get base domain name for set in cookie domain name for subdomain access
  arrHost = window.location.hostname.split('.');
  prefix = arrHost.shift();
  host = arrHost.join('.');
  setCookie('theme', mode, host);
}

function cycleTheme() {
  const currentTheme = getCookie('theme') || 'auto';

  if (prefersDark) {
    // Auto (dark) -> Light -> Dark
    if (currentTheme === 'auto') {
      setTheme('light');
    } else if (currentTheme === 'light') {
      setTheme('dark');
    } else {
      setTheme('auto');
    }
  } else {
    // Auto (light) -> Dark -> Light
    if (currentTheme === 'auto') {
      setTheme('dark');
    } else if (currentTheme === 'dark') {
      setTheme('light');
    } else {
      setTheme('auto');
    }
  }
}

function initTheme() {
  // set theme defined in localStorage if there is one, or fallback to auto mode
  const currentTheme = getCookie('theme');
  currentTheme ? setTheme(currentTheme) : setTheme('auto');
}

function setupTheme() {
  // Attach event handlers for toggling themes
  let buttons = document.getElementsByClassName('theme-toggle');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', cycleTheme);
  }
}

function setCookie(cname, cvalue, domain) {
  const d = new Date();
  d.setTime(d.getTime() + 365 * 24 * 60 * 60 * 1000); // 1 year
  let expires = 'expires=' + d.toUTCString();
  // change the SameSite attribute if it's on development or production
  sameSiteAttribute =
    domain == 'localhost'
      ? 'SameSite=Lax;'
      : `Domain=${domain}; SameSite=None; Secure;`;
  document.cookie = `${cname}=${cvalue}; ${sameSiteAttribute} ${expires}; path=/;`;
}

function getCookie(cname) {
  let name = cname + '=';
  let decodedCookie = decodeURIComponent(document.cookie);
  let ca = decodedCookie.split(';');
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return '';
}

initTheme();

document.addEventListener('DOMContentLoaded', function () {
  setupTheme();
});

// reset theme and release image if auto mode activated and os preferences have changed
window
  .matchMedia('(prefers-color-scheme: dark)')
  .addEventListener('change', function (e) {
    prefersDark = e.matches;
    initTheme();
  });

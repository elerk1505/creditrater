// ---- OpenAI key/model storage & request helpers ----
(function initApiSettings() {
  const keyInput   = document.getElementById('openaiKey');
  const modelInput = document.getElementById('openaiModel');
  const remember   = document.getElementById('rememberKey');
  const savedKey   = localStorage.getItem('OPENAI_KEY');
  const savedModel = localStorage.getItem('OPENAI_MODEL');

  if (savedKey)  { keyInput.value = savedKey;  remember.checked = true; }
  if (savedModel){ modelInput.value = savedModel; }

  document.getElementById('saveOpenAI').onclick = () => {
    const key = keyInput.value.trim();
    const model = (modelInput.value.trim() || 'gpt-4.1-mini');

    if (remember.checked) {
      localStorage.setItem('OPENAI_KEY', key);
      localStorage.setItem('OPENAI_MODEL', model);
      sessionStorage.removeItem('OPENAI_KEY');
      sessionStorage.removeItem('OPENAI_MODEL');
    } else {
      sessionStorage.setItem('OPENAI_KEY', key);
      sessionStorage.setItem('OPENAI_MODEL', model);
      localStorage.removeItem('OPENAI_KEY');
      localStorage.removeItem('OPENAI_MODEL');
    }
    const m = document.getElementById('apiSavedMsg');
    m.style.display = 'inline';
    setTimeout(()=> m.style.display='none', 1200);
  };

  document.getElementById('clearOpenAI').onclick = () => {
    localStorage.removeItem('OPENAI_KEY');
    localStorage.removeItem('OPENAI_MODEL');
    sessionStorage.removeItem('OPENAI_KEY');
    sessionStorage.removeItem('OPENAI_MODEL');
    keyInput.value = '';
    modelInput.value = 'gpt-4.1-mini';
    remember.checked = false;
  };
})();

export function getApiAuth() {
  const key   = sessionStorage.getItem('OPENAI_KEY') ?? localStorage.getItem('OPENAI_KEY') ?? '';
  const model = sessionStorage.getItem('OPENAI_MODEL') ?? localStorage.getItem('OPENAI_MODEL') ?? 'gpt-4.1-mini';
  return { key, model };
}

export async function postJSON(path, body) {
  const { key, model } = getApiAuth();
  if (!key) throw new Error('OpenAI key not set (paste it at the top and click Save).');
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-OpenAI-Key': key,
      'X-OpenAI-Model': model
    },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---- your existing imports / App boot ----
import './App.js';

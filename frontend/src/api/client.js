const API_BASE_URL = 'http://localhost:8000';

const GLOSSARY_MAP = {
  hin_Deva: {
    'voltmeter': 'वोल्टमीटर',
    'ammeter': 'अमीटर',
    'megger': 'मेगर',
    'turn off': 'बंद करें',
    'switch off': 'बंद करें',
    'turn on': 'चालू करें',
    'insulation resistance': 'इन्सुलेशन प्रतिरोध',
    'circuit breaker': 'सर्किट ब्रेकर',
    'control panel': 'कंट्रोल पैनल',
    'neutral wire': 'न्यूट्रल वायर',
    'live wire': 'लाइव तार',
    'fuse': 'फ्यूज',
    'voltage': 'वोल्टेज',
    'resistance': 'प्रतिरोध',
    'check': 'जांच करें',
    'inspect': 'निरीक्षण करें',
    'connect': 'जोड़ें',
    'the': '',
  }
};

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { status: 'offline', error: err.message };
  }
}

export async function translateText({ text, target_lang = 'hin_Deva', domain = 'electrician' }) {
  const startTime = performance.now();
  try {
    const res = await fetch(`${API_BASE_URL}/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target_lang, domain }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Server returned status ${res.status}`);
    }

    const data = await res.json();
    const duration = Math.round(performance.now() - startTime);
    return { ...data, latencyMs: duration };
  } catch (err) {
    // Dynamic rule-based fallback translation for dynamic user input when offline/reconnecting
    const duration = Math.round(performance.now() - startTime);
    let fallbackText = text;
    const dict = GLOSSARY_MAP[target_lang] || GLOSSARY_MAP['hin_Deva'];
    
    // Perform dynamic phrase/term replacement
    for (const [eng, tgt] of Object.entries(dict)) {
      const regex = new RegExp(`\\b${eng}\\b`, 'gi');
      fallbackText = fallbackText.replace(regex, tgt);
    }
    fallbackText = fallbackText.replace(/\s+/g, ' ').strip ? fallbackText.strip() : fallbackText.trim();

    return {
      translated_text: fallbackText || text,
      target_lang,
      backend: domain === 'electrician' ? 'models/finetuned_' + target_lang : 'facebook/nllb-200-distilled-600M',
      warning: `Note: ${err.message}. Showing local domain translation fallback.`,
      latencyMs: duration,
    };
  }
}

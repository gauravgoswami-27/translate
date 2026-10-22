// The 22 scheduled languages (IN22 scripts) with native names.
// `tuned`: the four languages the electrician adapters were trained on.
export const LANGUAGES = [
  { code: 'hin_Deva', name: 'Hindi', native: 'हिन्दी', tuned: true },
  { code: 'gom_Deva', name: 'Konkani', native: 'कोंकणी', tuned: true },
  { code: 'mai_Deva', name: 'Maithili', native: 'मैथिली', tuned: true },
  { code: 'doi_Deva', name: 'Dogri', native: 'डोगरी', tuned: true },
  { code: 'asm_Beng', name: 'Assamese', native: 'অসমীয়া' },
  { code: 'ben_Beng', name: 'Bengali', native: 'বাংলা' },
  { code: 'brx_Deva', name: 'Bodo', native: 'बड़ो' },
  { code: 'guj_Gujr', name: 'Gujarati', native: 'ગુજરાતી' },
  { code: 'kan_Knda', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'kas_Arab', name: 'Kashmiri', native: 'کٲشُر', rtl: true },
  { code: 'mal_Mlym', name: 'Malayalam', native: 'മലയാളം' },
  { code: 'mni_Mtei', name: 'Manipuri', native: 'ꯃꯩꯇꯩꯂꯣꯟ' },
  { code: 'mar_Deva', name: 'Marathi', native: 'मराठी' },
  { code: 'npi_Deva', name: 'Nepali', native: 'नेपाली' },
  { code: 'ory_Orya', name: 'Odia', native: 'ଓଡ଼ିଆ' },
  { code: 'pan_Guru', name: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
  { code: 'san_Deva', name: 'Sanskrit', native: 'संस्कृतम्' },
  { code: 'sat_Olck', name: 'Santali', native: 'ᱥᱟᱱᱛᱟᱲᱤ' },
  { code: 'snd_Deva', name: 'Sindhi', native: 'सिन्धी' },
  { code: 'tam_Taml', name: 'Tamil', native: 'தமிழ்' },
  { code: 'tel_Telu', name: 'Telugu', native: 'తెలుగు' },
  { code: 'urd_Arab', name: 'Urdu', native: 'اردو', rtl: true },
];

export const TUNED = LANGUAGES.filter((l) => l.tuned);
export const langByCode = Object.fromEntries(LANGUAGES.map((l) => [l.code, l]));
export const langName = (code) => langByCode[code]?.name ?? code;

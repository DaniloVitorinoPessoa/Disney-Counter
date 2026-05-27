// Desenhos SVG estilizados dos personagens (autorais, simplificados).
// Usados como cenario de fundo e particulas de cada tema.
window.SVGS = {
  // ---- FROZEN ----
  olaf: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="50" cy="80" rx="20" ry="15" fill="#fff" stroke="#cfe4f5" stroke-width="1.5"/>
    <ellipse cx="50" cy="56" rx="15" ry="14" fill="#fff" stroke="#cfe4f5" stroke-width="1.5"/>
    <circle cx="50" cy="33" r="14" fill="#fff" stroke="#cfe4f5" stroke-width="1.5"/>
    <circle cx="50" cy="55" r="2.2" fill="#3a3a3a"/><circle cx="50" cy="64" r="2.2" fill="#3a3a3a"/><circle cx="50" cy="74" r="2.2" fill="#3a3a3a"/>
    <circle cx="45" cy="31" r="2.4" fill="#2b2b2b"/><circle cx="55" cy="31" r="2.4" fill="#2b2b2b"/>
    <polygon points="50,33 71,36 50,39" fill="#ff8c2b"/>
    <path d="M43 41 Q50 47 57 41" fill="none" stroke="#2b2b2b" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M50 19 v-6 M46 20 l-3 -5 M54 20 l3 -5" stroke="#3a2a1a" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M35 54 l-13 -4 M65 54 l13 -4" stroke="#6b4a2b" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  sven: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M35 30 q-12 -16 -3 -23 q7 5 9 16 M65 30 q12 -16 3 -23 q-7 5 -9 16" fill="none" stroke="#8a5a2b" stroke-width="3" stroke-linecap="round"/>
    <ellipse cx="50" cy="56" rx="22" ry="25" fill="#a9712f"/>
    <ellipse cx="50" cy="42" rx="20" ry="14" fill="#c0894a"/>
    <ellipse cx="50" cy="73" rx="13" ry="11" fill="#caa06a"/>
    <circle cx="50" cy="74" r="6" fill="#6b4626"/>
    <circle cx="42" cy="51" r="3" fill="#2b1c10"/><circle cx="58" cy="51" r="3" fill="#2b1c10"/>
    <ellipse cx="28" cy="53" rx="6" ry="9" fill="#8a5a2b"/><ellipse cx="72" cy="53" rx="6" ry="9" fill="#8a5a2b"/>
  </svg>`,
  troll: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M25 82 q-7 -36 25 -42 q32 6 25 42 z" fill="#7d7f86" stroke="#5f6168" stroke-width="2"/>
    <circle cx="42" cy="62" r="3" fill="#3a3b40"/><circle cx="58" cy="62" r="3" fill="#3a3b40"/>
    <path d="M44 70 q6 4 12 0" stroke="#3a3b40" stroke-width="1.6" fill="none" stroke-linecap="round"/>
    <path d="M38 44 l-4 -8 M50 40 v-9 M62 44 l4 -8" stroke="#3fa34d" stroke-width="3" stroke-linecap="round"/>
    <circle cx="40" cy="80" r="2" fill="#7fe3ff"/><circle cx="60" cy="80" r="2" fill="#b07fff"/>
  </svg>`,
  // ---- ENROLADOS ----
  flower: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <g fill="#ffd23f">
      <ellipse cx="50" cy="24" rx="6" ry="17"/><ellipse cx="50" cy="76" rx="6" ry="17"/>
      <ellipse cx="24" cy="50" rx="17" ry="6"/><ellipse cx="76" cy="50" rx="17" ry="6"/>
      <ellipse cx="32" cy="32" rx="15" ry="6" transform="rotate(45 32 32)"/>
      <ellipse cx="68" cy="32" rx="15" ry="6" transform="rotate(-45 68 32)"/>
      <ellipse cx="32" cy="68" rx="15" ry="6" transform="rotate(-45 32 68)"/>
      <ellipse cx="68" cy="68" rx="15" ry="6" transform="rotate(45 68 68)"/>
    </g>
    <circle cx="50" cy="50" r="11" fill="#ffb02e" stroke="#fff3c0" stroke-width="2"/>
  </svg>`,
  pascal: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M30 62 q-18 0 -16 -16 q2 -8 8 -6 q-2 6 4 8 q8 2 8 -7" fill="none" stroke="#5bbf5b" stroke-width="6" stroke-linecap="round"/>
    <ellipse cx="56" cy="58" rx="26" ry="16" fill="#5bbf5b"/>
    <path d="M58 46 q9 -9 20 -5" stroke="#4aa64a" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="76" cy="52" r="9" fill="#7fd17f"/>
    <circle cx="78" cy="50" r="5" fill="#fff"/><circle cx="79" cy="50" r="2.4" fill="#2b2b2b"/>
    <path d="M42 70 l-4 9 M54 72 l-2 9 M66 70 l3 9" stroke="#4aa64a" stroke-width="3" stroke-linecap="round"/>
  </svg>`,
  pan: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="60" y="46" width="36" height="8" rx="4" fill="#3a3a3a"/>
    <circle cx="42" cy="50" r="27" fill="#4a4a4a" stroke="#2b2b2b" stroke-width="3"/>
    <ellipse cx="35" cy="42" rx="9" ry="5" fill="#7a7a7a" opacity=".5"/>
  </svg>`,
  // ---- CARROS ----
  mcqueen: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <rect x="8" y="50" width="84" height="20" rx="10" fill="#e2231a"/>
    <path d="M26 51 q8 -17 24 -17 q18 0 26 17 z" fill="#e2231a"/>
    <path d="M33 50 q6 -11 17 -11 q13 0 19 11 z" fill="#bfe6ff"/>
    <circle cx="44" cy="44" r="4" fill="#fff"/><circle cx="58" cy="44" r="4" fill="#fff"/>
    <circle cx="45" cy="45" r="2" fill="#1b6fb5"/><circle cx="59" cy="45" r="2" fill="#1b6fb5"/>
    <polygon points="62,58 75,53 69,60 81,57 64,68 70,60" fill="#ffd23f"/>
    <circle cx="28" cy="70" r="11" fill="#1b1b1b"/><circle cx="28" cy="70" r="5" fill="#b0b0b0"/>
    <circle cx="72" cy="70" r="11" fill="#1b1b1b"/><circle cx="72" cy="70" r="5" fill="#b0b0b0"/>
    <rect x="5" y="54" width="6" height="10" rx="2" fill="#ffd23f"/>
  </svg>`,
  bolt: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <polygon points="56,8 24,56 46,56 40,92 80,38 54,38" fill="#ffd23f" stroke="#e0a91f" stroke-width="2"/>
  </svg>`,
  // ---- REI LEAO ----
  lion: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="52" r="33" fill="#8a4a18"/>
    <g fill="#a55a1f">
      <polygon points="50,10 44,28 56,28"/><polygon points="90,52 72,46 72,58"/><polygon points="10,52 28,46 28,58"/><polygon points="50,94 44,76 56,76"/>
      <polygon points="22,24 34,36 24,40"/><polygon points="78,24 66,36 76,40"/><polygon points="22,80 34,68 24,64"/><polygon points="78,80 66,68 76,64"/>
    </g>
    <circle cx="50" cy="52" r="23" fill="#e3a866"/>
    <circle cx="43" cy="48" r="3" fill="#3a2412"/><circle cx="57" cy="48" r="3" fill="#3a2412"/>
    <ellipse cx="50" cy="60" rx="12" ry="9" fill="#f0c79a"/>
    <polygon points="46,57 54,57 50,62" fill="#3a2412"/>
    <path d="M50 62 v4 M50 66 q-4 3 -8 1 M50 66 q4 3 8 1" stroke="#3a2412" stroke-width="1.4" fill="none" stroke-linecap="round"/>
  </svg>`,
  pumbaa: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="54" cy="56" rx="30" ry="20" fill="#b06a4a"/>
    <circle cx="26" cy="52" r="16" fill="#b06a4a"/>
    <ellipse cx="14" cy="56" rx="8" ry="5" fill="#caa089"/>
    <circle cx="11" cy="55" r="1.5" fill="#3a2418"/><circle cx="16" cy="57" r="1.5" fill="#3a2418"/>
    <circle cx="28" cy="46" r="2.2" fill="#2b1a10"/>
    <polygon points="9,58 5,63 12,63" fill="#fff"/>
    <polygon points="32,38 26,30 34,32" fill="#8a4f38"/>
    <path d="M42 74 v10 M56 76 v10 M70 74 v10" stroke="#8a4f38" stroke-width="5" stroke-linecap="round"/>
    <path d="M26 33 q4 -7 9 -3" stroke="#3a2418" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  </svg>`,
  timon: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M62 80 q20 -2 15 -24" stroke="#c79a5b" stroke-width="6" fill="none" stroke-linecap="round"/>
    <ellipse cx="50" cy="62" rx="14" ry="22" fill="#c79a5b"/>
    <ellipse cx="50" cy="64" rx="8" ry="16" fill="#e7cfa0"/>
    <circle cx="50" cy="30" r="13" fill="#c79a5b"/>
    <ellipse cx="50" cy="34" rx="7" ry="6" fill="#e7cfa0"/>
    <circle cx="40" cy="20" r="4" fill="#a87c44"/><circle cx="60" cy="20" r="4" fill="#a87c44"/>
    <circle cx="45" cy="28" r="2.4" fill="#2b1a10"/><circle cx="55" cy="28" r="2.4" fill="#2b1a10"/>
    <circle cx="50" cy="33" r="2" fill="#2b1a10"/>
    <path d="M40 60 q-8 -6 -6 -16 M60 60 q8 -6 6 -16" stroke="#c79a5b" stroke-width="5" fill="none" stroke-linecap="round"/>
  </svg>`,
  sun: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="40" r="22" fill="#ffcf4d" stroke="#ffe08a" stroke-width="3"/>
    <path d="M8 80 L38 50 q4 -4 8 0 l8 10 14 -16 20 36 z" fill="#6b4a2b"/>
    <path d="M6 80 h88" stroke="#4a3320" stroke-width="3"/>
  </svg>`,
  // ---- TOY STORY ----
  ball: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <circle cx="50" cy="50" r="44" fill="#f3f3f3"/>
    <path d="M7.2 40 L92.8 40 A44 44 0 0 1 92.8 60 L7.2 60 A44 44 0 0 1 7.2 40 Z" fill="#e23b3b"/>
    <polygon points="50,28 57,46 76,46 61,57 67,76 50,64 33,76 39,57 24,46 43,46" fill="#ffd23f"/>
    <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(0,0,0,.15)" stroke-width="2"/>
  </svg>`,
  rocket: `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <path d="M50 8 q16 14 16 40 l-6 16 H40 l-6 -16 q0 -26 16 -40 z" fill="#e8eef5" stroke="#c2ccd8" stroke-width="2"/>
    <circle cx="50" cy="38" r="7" fill="#7fd1ff" stroke="#3a7fb5" stroke-width="2"/>
    <path d="M34 56 l-12 14 14 -4 z" fill="#e2231a"/><path d="M66 56 l12 14 -14 -4 z" fill="#e2231a"/>
    <path d="M44 80 q6 14 12 0 q-6 6 -12 0z" fill="#ffae42"/>
  </svg>`
};

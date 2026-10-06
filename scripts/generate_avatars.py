import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'doctors')
PAT_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'patients')
DEC_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'decoys')

for d in [DOC_DIR, PAT_DIR, DEC_DIR]:
    os.makedirs(d, exist_ok=True)

doc_colors = [
    ('#0284c7', '#38bdf8', '#fed7aa', '#475569', 'SL'),
    ('#059669', '#34d399', '#fcd34d', '#334155', 'MV'),
    ('#7c3aed', '#a78bfa', '#fbcfe8', '#64748b', 'ER'),
    ('#d97706', '#fbbf24', '#fef08a', '#1e293b', 'DK'),
    ('#dc2626', '#f87171', '#fed7aa', '#334155', 'AP')
]

for i, (bg1, bg2, skin, hair, initials) in enumerate(doc_colors, 1):
    doc_id = f"d00{i}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <defs>
    <linearGradient id="bg_{doc_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <circle cx="60" cy="60" r="58" fill="url(#bg_{doc_id})" stroke="{bg2}" stroke-width="3"/>
  <circle cx="60" cy="42" r="20" fill="{skin}"/>
  <path d="M42 36 Q60 18 78 36 Q70 24 60 24 Q50 24 42 36 Z" fill="{hair}"/>
  <path d="M26 110 C26 78 40 70 50 68 L70 68 C80 70 94 78 94 110 Z" fill="#f8fafc"/>
  <polygon points="52,68 68,68 60,86" fill="{bg1}"/>
  <circle cx="94" cy="26" r="14" fill="{bg2}"/>
  <path d="M94 18 L94 34 M86 26 L102 26" stroke="#060913" stroke-width="3.5" stroke-linecap="round"/>
  <text x="60" y="104" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{initials}</text>
</svg>"""
    with open(os.path.join(DOC_DIR, f"doc_{doc_id}.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

pat_colors = [
    ('#ef4444', '#fed7aa', '#334155'),
    ('#38bdf8', '#fcd34d', '#475569'),
    ('#10b981', '#fbcfe8', '#1e293b'),
    ('#f59e0b', '#fed7aa', '#64748b'),
    ('#8b5cf6', '#fef08a', '#334155'),
    ('#ec4899', '#fed7aa', '#1e293b'),
    ('#14b8a6', '#fcd34d', '#475569'),
    ('#6366f1', '#fed7aa', '#334155'),
    ('#f97316', '#fbcfe8', '#64748b'),
    ('#06b6d4', '#fed7aa', '#1e293b'),
    ('#84cc16', '#fcd34d', '#334155'),
    ('#a855f7', '#fed7aa', '#475569')
]

for i, (accent, skin, hair) in enumerate(pat_colors, 1):
    pid = f"hp{i:03d}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <defs>
    <linearGradient id="pbg_{pid}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e1b4b"/>
    </linearGradient>
  </defs>
  <circle cx="60" cy="60" r="58" fill="url(#pbg_{pid})" stroke="{accent}" stroke-width="3"/>
  <circle cx="60" cy="42" r="20" fill="{skin}"/>
  <path d="M42 36 Q60 18 78 36 Q70 26 60 26 Q50 26 42 36 Z" fill="{hair}"/>
  <path d="M26 110 C26 80 40 70 50 68 L70 68 C80 70 94 80 94 110 Z" fill="#38bdf8"/>
  <polygon points="54,68 66,68 60,82" fill="#0284c7"/>
  <circle cx="94" cy="26" r="14" fill="{accent}"/>
  <path d="M86 26 L89 26 L91 21 L94 31 L97 23 L99 26 L102 26" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""
    with open(os.path.join(PAT_DIR, f"pat_{pid}.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

for i in range(101, 111):
    did = f"dec_{i}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <circle cx="60" cy="60" r="58" fill="#2e1065" stroke="#c084fc" stroke-width="3"/>
  <circle cx="60" cy="42" r="20" fill="#e9d5ff"/>
  <path d="M42 36 Q60 18 78 36 Q70 26 60 26 Q50 26 42 36 Z" fill="#581c87"/>
  <path d="M26 110 C26 80 40 70 50 68 L70 68 C80 70 94 80 94 110 Z" fill="#9333ea"/>
  <circle cx="94" cy="26" r="14" fill="#a855f7"/>
  <text x="94" y="31" font-size="14" text-anchor="middle" fill="#ffffff">🎭</text>
</svg>"""
    with open(os.path.join(DEC_DIR, f"{did}.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

print("Generated profile SVGs successfully.")

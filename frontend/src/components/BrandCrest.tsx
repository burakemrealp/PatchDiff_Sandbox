interface BrandCrestProps {
  className?: string;
}

export function BrandCrest({ className = 'w-11 h-11' }: BrandCrestProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id="crestShell" x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#14294a" />
          <stop offset="100%" stopColor="#081224" />
        </linearGradient>
        <linearGradient id="crestGold" x1="10" y1="6" x2="54" y2="58" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#f5db94" />
          <stop offset="50%" stopColor="#c89b3c" />
          <stop offset="100%" stopColor="#8f681d" />
        </linearGradient>
        <linearGradient id="facetBefore" x1="18" y1="20" x2="31" y2="48" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#f4da90" />
          <stop offset="100%" stopColor="#a97b24" />
        </linearGradient>
        <linearGradient id="facetAfter" x1="33" y1="12" x2="48" y2="46" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#94f8ef" />
          <stop offset="55%" stopColor="#0ac8b9" />
          <stop offset="100%" stopColor="#076e7d" />
        </linearGradient>
      </defs>

      {/* Chamfered Hextech Octagonal Shield */}
      <polygon
        points="20,4 44,4 60,20 60,44 44,60 20,60 4,44 4,20"
        fill="url(#crestShell)"
        stroke="url(#crestGold)"
        strokeWidth="2.5"
      />
      <polygon
        points="22,8.5 42,8.5 55.5,22 55.5,42 42,55.5 22,55.5 8.5,42 8.5,22"
        stroke="#27466e"
        strokeWidth="1"
        fill="none"
      />

      {/* Runic Orbital Calibration Ring */}
      <circle
        cx="32"
        cy="33"
        r="17"
        stroke="#0ac8b9"
        strokeOpacity="0.28"
        strokeWidth="1.2"
        strokeDasharray="4 4"
      />

      {/* Split PatchDiff Crystal: Left (Baseline Gold) vs Right (Elevated Patch Spike Teal) */}
      <polygon
        points="30.5,19 19,33 30.5,49 30.5,35"
        fill="url(#facetBefore)"
      />
      <polygon
        points="30.5,19 19,33 25,33 30.5,24.5"
        fill="#fff1c4"
        fillOpacity="0.45"
      />

      <polygon
        points="33.5,13 46.5,31.5 33.5,48.5 33.5,31.5"
        fill="url(#facetAfter)"
      />
      <polygon
        points="33.5,13 46.5,31.5 40.5,31.5 33.5,20"
        fill="#d7fffb"
        fillOpacity="0.55"
      />

      {/* Upward Power-Delta Seam & Nexus Spark */}
      <path
        d="M32 50 V12"
        stroke="#091428"
        strokeWidth="2.2"
      />
      <polygon
        points="33.5,8 36.2,11.8 33.5,15.6 30.8,11.8"
        fill="#f5db94"
      />
    </svg>
  );
}

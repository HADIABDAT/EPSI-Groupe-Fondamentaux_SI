/* Design system perso — icônes.
   Trait de 1,75, extrémités arrondies, grille de 24 px, pas de remplissage.
   Ce fichier ajoute un sprite SVG caché à la page ; on affiche ensuite une icône avec :
     <svg class="ds-icon" aria-hidden="true"><use href="#ds-icon-check"></use></svg>
   (Le sprite est injecté par script parce qu'un <use> vers un fichier externe ne marche
   pas quand la page est ouverte en file://.) Les mêmes icônes existent en fichiers séparés
   dans icons/. */
(function () {
  const ICONS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-up": '<path d="M6 15l6-6 6 6"/>',
    "chevron-left": '<path d="M15 6l-6 6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "external": '<path d="M14 5h5v5M19 5l-8 8M17 14v4a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h4"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "more": '<path d="M6 12h.01M12 12h.01M18 12h.01" stroke-width="2.5"/>',
    "sliders": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "home": '<path d="M4 11l8-6.5 8 6.5M6 9.5V19h12V9.5"/><path d="M10 19v-5h4v5"/>',
    "folder": '<path d="M4 7a1 1 0 0 1 1-1h4.5l2 2H19a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/>',
    "file": '<path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10A.5.5 0 0 1 7 20z"/><path d="M14 3.5V8h4"/>',
    "edit": '<path d="M15.5 5.5l3 3L9 18H6v-3z"/><path d="M13.5 7.5l3 3"/>',
    "trash": '<path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12"/><path d="M10.5 11v5M13.5 11v5"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="1.5"/><path d="M15.5 5.5V5a1 1 0 0 0-1-1H5.5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h.5"/>',
    "download": '<path d="M12 4v11M7 10.5l5 5 5-5M5 20h14"/>',
    "upload": '<path d="M12 16V5M7 9.5l5-5 5 5M5 20h14"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1"/><path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
    "warning": '<path d="M12 4.5l8.5 15h-17z"/><path d="M12 10v4M12 17h.01"/>',
    "error": '<circle cx="12" cy="12" r="8.5"/><path d="M9.5 9.5l5 5M14.5 9.5l-5 5"/>',
    "success": '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
    "help": '<circle cx="12" cy="12" r="8.5"/><path d="M9.8 9.6a2.3 2.3 0 0 1 4.4.9c0 1.6-2.2 2-2.2 3.3M12 16.8h.01"/>',
    "bell": '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 1.5H5z"/><path d="M10 20.5h4"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14.5" rx="1.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "star": '<path d="M12 4.5l2.3 4.7 5.2.8-3.75 3.6.9 5.15L12 16.3l-4.65 2.45.9-5.15L4.5 10l5.2-.8z"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M10 6a9.6 9.6 0 0 1 2-.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.3 3M6.5 7.5C3.9 9.3 2.5 12 2.5 12s3.5 6.5 9.5 6.5a9 9 0 0 0 4.4-1.1M4 4l16 16"/><path d="M9.9 10a3 3 0 0 0 4.1 4.1"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="1.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "user": '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/>',
    "users": '<circle cx="9" cy="8.5" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M15.5 5.2a3.5 3.5 0 0 1 0 6.6M18 14.2a6.5 6.5 0 0 1 3.5 5.8"/>',
    "refresh": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3L19.5 9"/><path d="M19.5 4v5h-5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    "moon": '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="1.5"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15h4.5"/>',
    "code": '<path d="M9 7l-5 5 5 5M15 7l5 5-5 5"/>',
    "branch": '<circle cx="7" cy="5.5" r="2"/><circle cx="7" cy="18.5" r="2"/><circle cx="17" cy="8" r="2"/><path d="M7 7.5v9M17 10c0 4-10 2.5-10 6.5"/>',
    "package": '<path d="M12 3.5l8 4v9l-8 4-8-4v-9z"/><path d="M4 7.5l8 4 8-4M12 11.5v9"/>',
    "grid": '<rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/>',
    "list": '<path d="M9 7h11M9 12h11M9 17h11M4.5 7h.01M4.5 12h.01M4.5 17h.01"/>',
    "send": '<path d="M20.5 3.5L10 14M20.5 3.5l-6.5 17-4-6.5-6.5-4z"/>',
    "image": '<rect x="4" y="5" width="16" height="14" rx="1.5"/><circle cx="9" cy="10" r="1.5"/><path d="M20 15.5l-4.5-4.5L7 19"/>',
    "power": '<path d="M12 3.5v8M7.2 6.5a7 7 0 1 0 9.6 0"/>',
  };

  const sprite = '<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">'
    + Object.entries(ICONS).map(([name, body]) => '<symbol id="ds-icon-' + name + '" viewBox="0 0 24 24">' + body + '</symbol>').join("")
    + "</svg>";

  function inject() { document.body.insertAdjacentHTML("afterbegin", sprite); }
  if (document.body) inject(); else document.addEventListener("DOMContentLoaded", inject);

  window.DS_ICONS = ICONS;
})();

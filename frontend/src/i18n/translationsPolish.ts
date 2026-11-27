import type { LangBundleKey } from './locales';

export interface PolishTranslationDict {
  themeSwitchToLight: string;
  themeSwitchToDark: string;
  githubRepoTooltip: string;
  navBuildTitle: string;
  navBuildTag: string;
  navBuildShort: string;
  navBuildTooltip: string;
  navRadarTitle: string;
  navRadarTag: string;
  navRadarShort: string;
  navRadarTooltip: string;
  navDiffTitle: string;
  navDiffTag: string;
  navDiffShort: string;
  navDiffTooltip: string;
  navSimTitle: string;
  navSimTag: string;
  navSimShort: string;
  navSimTooltip: string;
}

export const POLISH_TRANSLATIONS: Record<LangBundleKey, PolishTranslationDict> = {
  tr: {
    themeSwitchToLight: 'Açık temaya geç',
    themeSwitchToDark: 'Koyu temaya geç',
    githubRepoTooltip: 'GitHub Açık Kaynak Deposu',
    navBuildTitle: 'Akıllı Build & Rün',
    navBuildTag: 'ÖNERİ',
    navBuildShort: 'Maç durumuna özel eşya & rün',
    navBuildTooltip:
      'Şampiyonunu seç; oyunda önde veya geride olmana göre en güçlü 6 eşyayı, 9 rünü ve minyon eşiklerini anında gör.',
    navRadarTitle: '0. Gün Meta Radarı',
    navRadarTag: 'CANLI',
    navRadarShort: 'Gizli bufflar & efsane testi',
    navRadarTooltip:
      'Yeni yamada adı geçmeden güçlenen gizli şampiyonları ve kağıt üstünde yanıltıcı buff/nerfleri ilk günden yakala.',
    navDiffTitle: 'Yama Özeti',
    navDiffTag: 'CANLI VERİ',
    navDiffShort: 'Tüm şampiyon & eşya farkları',
    navDiffTooltip:
      'Son LoL yamasındaki tüm şampiyon, eşya ve rün değişimlerini tek ekranda filtrele ve simülatöre aktar.',
    navSimTitle: 'Hasar Simülatörü',
    navSimTag: 'SANDBOX',
    navSimShort: 'Seviye 1–20 kombo & EHP testi',
    navSimTooltip:
      'İstediğin eşya dizilimini veya özel yama notunu girerek Seviye 1–20 arası net hasar ve dayanıklılık eğrisini ölç.',
  },
  en: {
    themeSwitchToLight: 'Switch to light theme',
    themeSwitchToDark: 'Switch to dark theme',
    githubRepoTooltip: 'Open-Source GitHub Repository',
    navBuildTitle: 'Smart Builds & Runes',
    navBuildTag: 'COACH',
    navBuildShort: 'Items & 9 runes for any tempo',
    navBuildTooltip:
      'Pick your champion and see the strongest 6-item build, full 9-slot rune page, and minion thresholds whether ahead or behind.',
    navRadarTitle: 'Day-0 Patch Radar',
    navRadarTag: 'META',
    navRadarShort: 'Hidden winners & mythbuster',
    navRadarTooltip:
      'Spot unlisted champions secretly buffed by item changes and catch deceptive paper buffs/nerfs on patch day.',
    navDiffTitle: 'Patch Notes Feed',
    navDiffTag: 'LIVE DIFF',
    navDiffShort: 'Every champ, item & rune delta',
    navDiffTooltip:
      'Browse every verified champion, item, and rune change in the latest patch and test any setup in one click.',
    navSimTitle: 'Damage Sandbox',
    navSimTag: 'LAB',
    navSimShort: 'Lv 1–20 DPS & EHP curve test',
    navSimTooltip:
      'Mix any items or custom patch numbers to compare Level 1–20 burst, DPS, and survivability curves side by side.',
  },
  de: {
    themeSwitchToLight: 'Zum hellen Design wechseln',
    themeSwitchToDark: 'Zum dunklen Design wechseln',
    githubRepoTooltip: 'Open-Source-GitHub-Repository',
    navBuildTitle: 'Smarte Builds & Runen',
    navBuildTag: 'COACH',
    navBuildShort: 'Items & 9 Runen für jede Lage',
    navBuildTooltip:
      'Wähle deinen Champion und erhalte das beste 6-Item-Build, 9 Runen sowie Vasallen-Schwellenwerte für Rückstand oder Führung.',
    navRadarTitle: 'Day-0 Meta-Radar',
    navRadarTag: 'META',
    navRadarShort: 'Geheime Gewinner & Mythen-Check',
    navRadarTooltip:
      'Entdecke schon am ersten Patch-Tag versteckte Item-Gewinner und entlarve trügerische Buffs oder Nerfs.',
    navDiffTitle: 'Patch-Übersicht',
    navDiffTag: 'LIVE-DIFF',
    navDiffShort: 'Alle Champion- & Item-Updates',
    navDiffTooltip:
      'Sieh dir alle aktuellen Champion-, Item- und Runen-Änderungen übersichtlich an und teste sie direkt.',
    navSimTitle: 'Schadens-Sandbox',
    navSimTag: 'LABOR',
    navSimShort: 'Stufe 1–20 DPS & EHP-Kurve',
    navSimTooltip:
      'Kombiniere beliebige Items oder eigene Patch-Werte und vergleiche Schaden sowie Überlebenswerte bis Stufe 20.',
  },
  es: {
    themeSwitchToLight: 'Cambiar a tema claro',
    themeSwitchToDark: 'Cambiar a tema oscuro',
    githubRepoTooltip: 'Repositorio Open-Source en GitHub',
    navBuildTitle: 'Builds y Runas IA',
    navBuildTag: 'GUÍA',
    navBuildShort: 'Objetos y runas según partida',
    navBuildTooltip:
      'Elige tu campeón y descubre al instante los mejores 6 objetos, 9 runas y limpieza de súbditos vayas ganando o perdiendo.',
    navRadarTitle: 'Radar Día-0',
    navRadarTag: 'META',
    navRadarShort: 'Ganadores ocultos y mitos',
    navRadarTooltip:
      'Detecta campeones beneficiados en secreto por cambios de objetos y desmonta buffs o nerfs engañosos.',
    navDiffTitle: 'Resumen del Parche',
    navDiffTag: 'EN VIVO',
    navDiffShort: 'Todos los cambios del parche',
    navDiffTooltip:
      'Explora todos los cambios de campeones, objetos y runas del último parche y pruébalos en un clic.',
    navSimTitle: 'Simulador de Daño',
    navSimTag: 'SANDBOX',
    navSimShort: 'Curva de daño y aguante Nv 1–20',
    navSimTooltip:
      'Combina objetos o notas personalizadas para medir tu burst, DPS y resistencia exacta de nivel 1 a 20.',
  },
  fr: {
    themeSwitchToLight: 'Passer au thème clair',
    themeSwitchToDark: 'Passer au thème sombre',
    githubRepoTooltip: 'Dépôt GitHub Open Source',
    navBuildTitle: 'Builds & Runes IA',
    navBuildTag: 'COACH',
    navBuildShort: 'Objets et runes selon l’avance',
    navBuildTooltip:
      'Choisissez votre champion pour voir instantanément les 6 meilleurs objets, 9 runes et seuils de sbires selon votre avance.',
    navRadarTitle: 'Radar Jour-0',
    navRadarTag: 'MÉTA',
    navRadarShort: 'Gagnants cachés & mythes',
    navRadarTooltip:
      'Repérez dès le premier jour les champions renforcés indirectement par les objets et évitez les faux buffs.',
    navDiffTitle: 'Résumé du Patch',
    navDiffTag: 'DIRECT',
    navDiffShort: 'Tous les changements du patch',
    navDiffTooltip:
      'Consultez chaque changement de champion, objet et rune du dernier patch et lancez une simulation en un clic.',
    navSimTitle: 'Simulateur Dégâts',
    navSimTag: 'LABO',
    navSimShort: 'Courbes Nv 1–20 DPS & survie',
    navSimTooltip:
      'Testez librement vos objets ou notes personnalisées et comparez vos courbes de burst, DPS et résistance.',
  },
  it: {
    themeSwitchToLight: 'Passa al tema chiaro',
    themeSwitchToDark: 'Passa al tema scuro',
    githubRepoTooltip: 'Repository GitHub Open Source',
    navBuildTitle: 'Build e Rune Smart',
    navBuildTag: 'COACH',
    navBuildShort: 'Oggetti e 9 rune su misura',
    navBuildTooltip:
      'Scegli il campione e trova subito i 6 oggetti migliori, 9 rune e soglie minion per partite in vantaggio o svantaggio.',
    navRadarTitle: 'Radar Giorno-0',
    navRadarTag: 'META',
    navRadarShort: 'Vincitori nascosti e falsi miti',
    navRadarTooltip:
      'Scopri i campioni potenziati indirettamente dagli oggetti ed evita i buff ingannevoli sin dal giorno della patch.',
    navDiffTitle: 'Note della Patch',
    navDiffTag: 'LIVE',
    navDiffShort: 'Tutte le modifiche della patch',
    navDiffTooltip:
      'Esplora tutte le modifiche a campioni, oggetti e rune dell’ultima patch e simulale con un clic.',
    navSimTitle: 'Sandbox Danni',
    navSimTag: 'LAB',
    navSimShort: 'Curve danni & EHP Lv 1–20',
    navSimTooltip:
      'Combina oggetti o note personalizzate per testare burst, DPS e resistenza reale dal livello 1 al 20.',
  },
  pt: {
    themeSwitchToLight: 'Mudar para tema claro',
    themeSwitchToDark: 'Mudar para tema escuro',
    githubRepoTooltip: 'Repositório Open Source no GitHub',
    navBuildTitle: 'Builds & Runas IA',
    navBuildTag: 'GUIA',
    navBuildShort: 'Itens e runas para cada ritmo',
    navBuildTooltip:
      'Escolha seu campeão e veja na hora os 6 melhores itens, 9 runas e abates de tropas estando atrás ou na frente.',
    navRadarTitle: 'Radar Dia-0',
    navRadarTag: 'META',
    navRadarShort: 'Vencedores ocultos e mitos',
    navRadarTooltip:
      'Descubra campeões fortalecidos indiretamente por itens e identifique buffs enganosos logo no dia do patch.',
    navDiffTitle: 'Resumo do Patch',
    navDiffTag: 'AO VIVO',
    navDiffShort: 'Mudanças de campeões e itens',
    navDiffTooltip:
      'Veja todas as alterações de campeões, itens e runas do patch atual e teste qualquer combinação em um clique.',
    navSimTitle: 'Simulador de Dano',
    navSimTag: 'LAB',
    navSimShort: 'Curvas de DPS e EHP Nv 1–20',
    navSimTooltip:
      'Monte combinações ou edite valores de patch para comparar burst, DPS e resistência do nível 1 ao 20.',
  },
  pl: {
    themeSwitchToLight: 'Przełącz na jasny motyw',
    themeSwitchToDark: 'Przełącz na ciemny motyw',
    githubRepoTooltip: 'Repozytorium Open Source GitHub',
    navBuildTitle: 'Inteligentne Buildy',
    navBuildTag: 'COACH',
    navBuildShort: 'Przedmioty i runy na każdy stan',
    navBuildTooltip:
      'Wybierz bohatera, aby zobaczyć najlepsze 6 przedmiotów, 9 run i progi stworów przy stracie lub przewadze.',
    navRadarTitle: 'Radar Dnia 0',
    navRadarTag: 'META',
    navRadarShort: 'Ukryci zwycięzcy i mity',
    navRadarTooltip:
      'Wykryj bohaterów wzmocnionych pośrednio przez przedmioty oraz zwodnicze wzmocnienia już w dniu patcha.',
    navDiffTitle: 'Przegląd Patcha',
    navDiffTag: 'NA ŻYWO',
    navDiffShort: 'Zmiany bohaterów i przedmiotów',
    navDiffTooltip:
      'Sprawdź wszystkie zmiany bohaterów, przedmiotów i run w najnowszym patchu i przetestuj je jednym kliknięciem.',
    navSimTitle: 'Symulator Obrażeń',
    navSimTag: 'LAB',
    navSimShort: 'Krzywe DPS i EHP Poz 1–20',
    navSimTooltip:
      'Łącz dowolne przedmioty lub własne notatki patcha i porównuj obrażenia oraz wytrzymałość do 20. poziomu.',
  },
  ru: {
    themeSwitchToLight: 'Включить светлую тему',
    themeSwitchToDark: 'Включить тёмную тему',
    githubRepoTooltip: 'Репозиторий Open Source на GitHub',
    navBuildTitle: 'Умные Сборки и Руны',
    navBuildTag: 'ГИД',
    navBuildShort: 'Предметы и 9 рун под темп',
    navBuildTooltip:
      'Выберите чемпиона и получите лучшие 6 предметов, 9 рун и пороги зачистки волн для отставания или преимущества.',
    navRadarTitle: 'Мета-Радар Дня 0',
    navRadarTag: 'МЕТА',
    navRadarShort: 'Скрытые фавориты и мифы',
    navRadarTooltip:
      'Находите чемпионов, усиленных косвенно через предметы, и распознавайте обманчивые баффы в день патча.',
    navDiffTitle: 'Сводка Патча',
    navDiffTag: 'ДАННЫЕ',
    navDiffShort: 'Все правки чемпионов и вещей',
    navDiffTooltip:
      'Просматривайте все изменения чемпионов, предметов и рун последнего патча и тестируйте их в один клик.',
    navSimTitle: 'Песочница Урона',
    navSimTag: 'ТЕСТ',
    navSimShort: 'Кривые DPS и EHP ур. 1–20',
    navSimTooltip:
      'Комбинируйте любые предметы или свои заметки патча для точного расчёта урона и живучести с 1 по 20 уровень.',
  },
  cs: {
    themeSwitchToLight: 'Přepnout na světlý motiv',
    themeSwitchToDark: 'Přepnout na tmavý motiv',
    githubRepoTooltip: 'Open-Source GitHub Repozitář',
    navBuildTitle: 'Chytré Buildy & Runy',
    navBuildTag: 'RÁDCE',
    navBuildShort: 'Výbava a runy podle tempa hry',
    navBuildTooltip:
      'Vyberte šampiona a okamžitě uvidíte 6 nejlepších předmětů, 9 run a hranice poskoků při ztrátě i vedení.',
    navRadarTitle: 'Meta Radar Den 0',
    navRadarTag: 'META',
    navRadarShort: 'Skrytí vítězové a boření mýtů',
    navRadarTooltip:
      'Odhalte šampiony nepřímo posílené změnami předmětů a rozpoznávejte klamné buffy hned první den patche.',
    navDiffTitle: 'Přehled Patche',
    navDiffTag: 'ŽIVĚ',
    navDiffShort: 'Všechny změny šampionů a věcí',
    navDiffTooltip:
      'Prohlédněte si všechny změny šampionů, předmětů a run posledního patche a otestujte je jedním kliknutím.',
    navSimTitle: 'Simulátor Poškození',
    navSimTag: 'LAB',
    navSimShort: 'Křivky DPS a EHP Úr. 1–20',
    navSimTooltip:
      'Sestavte si libovolné předměty nebo vlastní hodnoty patche a porovnejte poškození a odolnost do 20. úrovně.',
  },
  el: {
    themeSwitchToLight: 'Αλλαγή σε φωτεινό θέμα',
    themeSwitchToDark: 'Αλλαγή σε σκοτεινό θέμα',
    githubRepoTooltip: 'Αποθετήριο Open Source στο GitHub',
    navBuildTitle: 'Έξυπνα Builds & Ρούνοι',
    navBuildTag: 'ΟΔΗΓΟΣ',
    navBuildShort: 'Αντικείμενα & 9 ρούνοι ανά ροή',
    navBuildTooltip:
      'Διάλεξε ήρωα και δες τα 6 καλύτερα αντικείμενα, 9 ρούνους και όρια minions είτε είσαι μπροστά είτε πίσω.',
    navRadarTitle: 'Ραντάρ Ημέρας 0',
    navRadarTag: 'META',
    navRadarShort: 'Κρυφοί νικητές & μύθοι patch',
    navRadarTooltip:
      'Βρες ήρωες που ενισχύθηκαν έμμεσα από αλλαγές αντικειμένων και ξεχώρισε τα παραπλανητικά buffs.',
    navDiffTitle: 'Σύνοψη Patch',
    navDiffTag: 'ΖΩΝΤΑΝΑ',
    navDiffShort: 'Όλες οι αλλαγές ηρώων & ειδών',
    navDiffTooltip:
      'Δες κάθε αλλαγή σε ήρωες, αντικείμενα και ρούνους του τελευταίου patch και δοκίμασέ τη με ένα κλικ.',
    navSimTitle: 'Εργαστήριο Ζημιάς',
    navSimTag: 'LAB',
    navSimShort: 'Καμπύλες DPS & EHP Επ. 1–20',
    navSimTooltip:
      'Συνδύασε αντικείμενα ή δικά σου νούμερα patch για να μετρήσεις burst, DPS και αντοχή από το Επίπεδο 1 έως το 20.',
  },
  hu: {
    themeSwitchToLight: 'Váltás világos témára',
    themeSwitchToDark: 'Váltás sötét témára',
    githubRepoTooltip: 'Nyílt forráskódú GitHub tárhely',
    navBuildTitle: 'Okos Buildek és Rúnák',
    navBuildTag: 'EDZŐ',
    navBuildShort: 'Tárgyak és 9 rúna helyzethez',
    navBuildTooltip:
      'Válassz hőst, és azonnal lásd a legjobb 6 tárgyat, 9 rúnát és minion-küszöböket előnyben vagy hátrányban.',
    navRadarTitle: '0. Napi Meta Radar',
    navRadarTag: 'META',
    navRadarShort: 'Rejtett nyertesek és tévhitek',
    navRadarTooltip:
      'Találd meg a tárgyváltozások miatt titokban megerősödött hősöket és a megtévesztő buffokat már az első napon.',
    navDiffTitle: 'Patch Összefoglaló',
    navDiffTag: 'ÉLŐ ADAT',
    navDiffShort: 'Minden hős- és tárgyváltozás',
    navDiffTooltip:
      'Böngészd át az új patch összes hős-, tárgy- és rúnaparaméterét, és teszteld őket egyetlen kattintással.',
    navSimTitle: 'Sebzés Szimulátor',
    navSimTag: 'LABOR',
    navSimShort: '1–20. szintű DPS és EHP görbe',
    navSimTooltip:
      'Állíts össze saját tárgyakat vagy egyéni patch-értékeket a sebzés és túlélőképesség pontos összehasonlításához.',
  },
  ro: {
    themeSwitchToLight: 'Comută la tema luminoasă',
    themeSwitchToDark: 'Comută la tema întunecată',
    githubRepoTooltip: 'Depozit Open Source pe GitHub',
    navBuildTitle: 'Builduri & Rune Smart',
    navBuildTag: 'GHID',
    navBuildShort: 'Obiecte și rune după ritm',
    navBuildTooltip:
      'Alege campionul și vezi imediat cele mai bune 6 obiecte, 9 rune și pragurile de minioni indiferent de avantaj.',
    navRadarTitle: 'Radar Ziua-0',
    navRadarTag: 'META',
    navRadarShort: 'Câștigători ascunși și mituri',
    navRadarTooltip:
      'Descoperă campionii întăriți indirect prin obiecte și evită buff-urile înșelătoare chiar din prima zi.',
    navDiffTitle: 'Sumar Patch',
    navDiffTag: 'LIVE',
    navDiffShort: 'Toate schimbările din patch',
    navDiffTooltip:
      'Explorează toate modificările de campioni, obiecte și rune din ultimul patch și testează-le cu un clic.',
    navSimTitle: 'Simulator Daune',
    navSimTag: 'LAB',
    navSimShort: 'Curbe DPS și EHP Nv 1–20',
    navSimTooltip:
      'Combină orice obiecte sau valori proprii pentru a măsura exact burst-ul, DPS-ul și supraviețuirea.',
  },
  ar: {
    themeSwitchToLight: 'التبديل إلى الوضع الفاتح',
    themeSwitchToDark: 'التبديل إلى الوضع الداكن',
    githubRepoTooltip: 'مستودع GitHub مفتوح المصدر',
    navBuildTitle: 'أبنية ورونز ذكية',
    navBuildTag: 'مدرب',
    navBuildShort: 'عناصر و9 رونز حسب إيقاع اللعب',
    navBuildTooltip:
      'اختر بطلك وشاهد فوراً أفضل 6 عناصر وصفحة 9 رونز وحدود التابعين سواء كنت متقدماً أو متأخراً.',
    navRadarTitle: 'رادار اليوم الأول',
    navRadarTag: 'ميتا',
    navRadarShort: 'فائزون خفيون وكشف الخرافات',
    navRadarTooltip:
      'اكتشف الأبطال الذين تعززوا بشكل غير مباشر عبر العناصر وتجنب التغييرات الخادعة من أول يوم للتحديث.',
    navDiffTitle: 'ملخص التحديث',
    navDiffTag: 'مباشر',
    navDiffShort: 'كل تغييرات الأبطال والعناصر',
    navDiffTooltip:
      'استعرض كافة تعديلات الأبطال والعناصر والرونز في التحديث الأخير وجربها بنقرة واحدة.',
    navSimTitle: 'محاكي الضرر',
    navSimTag: 'مختبر',
    navSimShort: 'منحنى الضرر والتحمل 1–20',
    navSimTooltip:
      'اجمع أي عناصر أو أرقام تحديث مخصصة لمقارنة ضرر الانفجار والضرر المستمر والتحمل حتى المستوى 20.',
  },
  ja: {
    themeSwitchToLight: 'ライトテーマに切替',
    themeSwitchToDark: 'ダークテーマに切替',
    githubRepoTooltip: 'GitHub オープンソース',
    navBuildTitle: '最適ビルド＆ルーン',
    navBuildTag: 'コーチ',
    navBuildShort: '有利・劣勢に応じた6枠＋9ルーン',
    navBuildTooltip:
      'チャンピオンを選ぶだけで、試合展開（優勢/劣勢）に最適な6アイテム・9ルーン・ミニオン処理ラインが即座に分かります。',
    navRadarTitle: '初日メタレーダー',
    navRadarTag: 'メタ',
    navRadarShort: '隠れた勝者＆見かけ倒し検証',
    navRadarTooltip:
      '装備変更で密かに強くなったチャンピオンや、数字に騙されやすい見かけ上のバフ/ナーフをパッチ初日に見抜きます。',
    navDiffTitle: 'パッチ変更一覧',
    navDiffTag: '最新データ',
    navDiffShort: '全チャンピオン＆装備差分',
    navDiffTooltip:
      '最新パッチのチャンピオン・アイテム・ルーン変更点を一覧で確認し、ワンクリックでシミュレーターへ送れます。',
    navSimTitle: 'ダメージ検証ラボ',
    navSimTag: 'ラボ',
    navSimShort: 'Lv1–20 火力・耐久カーブ検証',
    navSimTooltip:
      '好きなアイテム構成やパッチ数値を組み合わせて、Lv1〜20の実戦ダメージと耐久力をグラフで比較できます。',
  },
  ko: {
    themeSwitchToLight: '라이트 테마로 전환',
    themeSwitchToDark: '다크 테마로 전환',
    githubRepoTooltip: 'GitHub 오픈소스 저장소',
    navBuildTitle: '스마트 빌드 & 룬',
    navBuildTag: '코치',
    navBuildShort: '유리·불리 상황별 6코어 & 9룬',
    navBuildTooltip:
      '챔피언을 고르면 현재 유리·불리 흐름에 맞춘 최적 6아이템, 9슬롯 룬, 미니언 원콤 기준까지 바로 확인합니다.',
    navRadarTitle: '0일차 메타 레이더',
    navRadarTag: '메타',
    navRadarShort: '숨은 수혜자 & 함정 패치 검증',
    navRadarTooltip:
      '패치 노트에 없지만 아이템 변화로 강해진 챔피언과 숫자에 속기 쉬운 거짓 버프·너프를 첫날에 잡아냅니다.',
    navDiffTitle: '패치 변경 요약',
    navDiffTag: '실시간',
    navDiffShort: '챔피언·아이템·룬 변경점',
    navDiffTooltip:
      '최신 패치의 모든 챔피언, 아이템, 룬 수치 변화를 한눈에 필터링하고 클릭 한 번으로 시뮬레이션합니다.',
    navSimTitle: '데미지 시뮬레이터',
    navSimTag: '실험실',
    navSimShort: '레벨 1–20 폭딜·DPS·EHP 곡선',
    navSimTooltip:
      '원하는 아이템이나 커스텀 패치 수치를 조합해 레벨 1~20 구간별 실제 피해량과 생존력을 비교해 보세요.',
  },
  'zh-TW': {
    themeSwitchToLight: '切換淺色主題',
    themeSwitchToDark: '切換深色主題',
    githubRepoTooltip: 'GitHub 開源專案庫',
    navBuildTitle: '智慧出裝與符文',
    navBuildTag: '教練',
    navBuildShort: '順逆風最佳六件裝與九符文',
    navBuildTooltip:
      '選擇英雄即可依順風或逆風局勢，查看最強六件神裝、完整九格符文與遠程兵斬殺線。',
    navRadarTitle: '零日版本雷達',
    navRadarTag: '版本',
    navRadarShort: '隱藏贏家與假改動破解',
    navRadarTooltip:
      '在版本第一天揪出因裝備改動而暗中變強的英雄，以及表面加強實則削弱的陷阱改動。',
    navDiffTitle: '版本改動總覽',
    navDiffTag: '即時資料',
    navDiffShort: '全英雄、裝備與符文差異',
    navDiffTooltip:
      '一站瀏覽最新版本的英雄、裝備與符文數值變動，並可一鍵送入傷害模擬器驗證。',
    navSimTitle: '傷害模擬實驗室',
    navSimTag: '實驗室',
    navSimShort: 'Lv 1–20 輸出與坦度曲線',
    navSimTooltip:
      '自由搭配裝備或貼上自訂改動數值，精準比較 1 至 20 級的爆發、持續輸出與有效生命曲線。',
  },
  th: {
    themeSwitchToLight: 'สลับเป็นธีมสว่าง',
    themeSwitchToDark: 'สลับเป็นธีมมืด',
    githubRepoTooltip: 'คลังโค้ดโอเพนซอร์ส GitHub',
    navBuildTitle: 'บิลด์และรูนอัจฉริยะ',
    navBuildTag: 'โค้ช',
    navBuildShort: 'ไอเทมและ 9 รูนตามจังหวะเกม',
    navBuildTooltip:
      'เลือกแชมเปียนของคุณแล้วดูชุดไอเทม 6 ชิ้น รูนครบ 9 ช่อง และเกณฑ์เคลียร์เวฟได้ทันทีไม่ว่าจะนำหรือเสียเปรียบ',
    navRadarTitle: 'เรดาร์เมต้าวันแรก',
    navRadarTag: 'เมต้า',
    navRadarShort: 'ตัวเก่งลับ & จับผิดบัฟปลอม',
    navRadarTooltip:
      'ค้นหาแชมเปียนที่เก่งขึ้นทางอ้อมจากไอเทมใหม่ และจับผิดบัฟหรือเนิร์ฟที่หลอกตาตั้งแต่วันแรกของแพตช์',
    navDiffTitle: 'สรุปแพตช์ล่าสุด',
    navDiffTag: 'ข้อมูลสด',
    navDiffShort: 'ความเปลี่ยนแปลงแชมเปียน/ไอเทม',
    navDiffTooltip:
      'ดูรายการปรับสมดุลแชมเปียน ไอเทม และรูนทั้งหมดในแพตช์ล่าสุด แล้วส่งไปจำลองดาเมจได้ในคลิกเดียว',
    navSimTitle: 'ห้องจำลองดาเมจ',
    navSimTag: 'แซนด์บ็อกซ์',
    navSimShort: 'กราฟ DPS & ความอึด Lv 1–20',
    navSimTooltip:
      'จัดเซ็ตไอเทมหรือใส่ตัวเลขแพตช์เองเพื่อเทียบดาเมจเบิร์สต์ DPS และความอึดตั้งแต่เลเวล 1 ถึง 20',
  },
  vi: {
    themeSwitchToLight: 'Chuyển sang giao diện sáng',
    themeSwitchToDark: 'Chuyển sang giao diện tối',
    githubRepoTooltip: 'Mã nguồn mở trên GitHub',
    navBuildTitle: 'Trang Bị & Ngọc AI',
    navBuildTag: 'HUẤN LUYỆN',
    navBuildShort: 'Đồ & 9 ngọc chuẩn theo thế trận',
    navBuildTooltip:
      'Chọn tướng để xem ngay bộ 6 trang bị tối ưu, bảng 9 ngọc và ngưỡng dọn lính dù đang dẫn trước hay thua thiệt.',
    navRadarTitle: 'Radar Meta Ngày 0',
    navRadarTag: 'META',
    navRadarShort: 'Tướng mạnh ngầm & giải ảo buff',
    navRadarTooltip:
      'Phát hiện sớm tướng được tăng sức mạnh gián tiếp qua trang bị và vạch trần những cú buff/nerf gây hiểu nhầm.',
    navDiffTitle: 'Tổng Hợp Bản Vá',
    navDiffTag: 'TRỰC TIẾP',
    navDiffShort: 'Mọi thay đổi tướng & trang bị',
    navDiffTooltip:
      'Xem toàn bộ thay đổi tướng, trang bị và ngọc trong bản cập nhật mới nhất và đưa vào mô phỏng chỉ với 1 lần nhấn.',
    navSimTitle: 'Mô Phỏng Sát Thương',
    navSimTag: 'PHÒNG THỬ',
    navSimShort: 'Biểu đồ DPS & độ trâu Cấp 1–20',
    navSimTooltip:
      'Tự phối hợp trang bị hoặc thông số chỉnh sửa để so sánh chính xác dồn sát thương, DPS và chống chịu từ cấp 1 đến 20.',
  },
  id: {
    themeSwitchToLight: 'Beralih ke tema terang',
    themeSwitchToDark: 'Beralih ke tema gelap',
    githubRepoTooltip: 'Repositori Open-Source GitHub',
    navBuildTitle: 'Build & Rune Cerdas',
    navBuildTag: 'PELATIH',
    navBuildShort: 'Item & 9 rune sesuai kondisi game',
    navBuildTooltip:
      'Pilih champion-mu dan langsung lihat 6 item terbaik, halaman 9 rune, serta batas waveclear baik saat unggul maupun tertinggal.',
    navRadarTitle: 'Radar Meta Hari-0',
    navRadarTag: 'META',
    navRadarShort: 'Juara tersembunyi & cek mitos',
    navRadarTooltip:
      'Temukan champion yang diam-diam menguat akibat perubahan item dan kenali buff/nerf semu di hari pertama patch.',
    navDiffTitle: 'Ringkasan Patch',
    navDiffTag: 'DATA LANGSUNG',
    navDiffShort: 'Semua perubahan champion & item',
    navDiffTooltip:
      'Jelajahi seluruh perubahan champion, item, dan rune di patch terbaru lalu uji langsung dengan satu klik.',
    navSimTitle: 'Sandbox Damage',
    navSimTag: 'LAB',
    navSimShort: 'Kurva DPS & EHP Lv 1–20',
    navSimTooltip:
      'Padukan item atau angka patch kustom untuk membandingkan burst, DPS, dan daya tahan secara akurat dari level 1 hingga 20.',
  },
};

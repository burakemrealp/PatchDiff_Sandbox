# PatchDiff Sandbox

[![Language: English](https://img.shields.io/badge/Language-English-0ea5e9)](README.md) [![Dil: Türkçe](https://img.shields.io/badge/Dil-T%C3%BCrk%C3%A7e-ef4444)](#) [![Sürüm: v1.0.0](https://img.shields.io/badge/S%C3%BCr%C3%BCm-v1.0.0-10b981)](CHANGELOG.md) [![Lisans: MIT](https://img.shields.io/badge/Lisans-MIT-f59e0b)](LICENSE) [![Riot Uyumluluğu: Zero-Vanguard](https://img.shields.io/badge/Riot%20Uyumlulu%C4%9Fu-Zero--Vanguard-6366f1)](SECURITY.md)

[English](README.md) | **Türkçe**

**League of Legends** için deterministik yama analiz motoru, Seviye 1–20 çatışma ve Efektif Can (EHP) simülatörü ile yapay zekâ destekli eşya + tam 9 slotlu rün optimizasyon laboratuvarı — **oyun istemcisinden ve Riot Vanguard'dan %100 bağımsız** çalışacak şekilde tasarlanmıştır.

---

## Temel Yetenekler

- **Deterministik Seviye 1–20 Çatışma Simülatörü (`combat_simulator.py`, `damage_calculator.py`, `stat_aggregator.py`):**
  Yama sürümleri arasında seviye bazlı Efektif Can (EHP), anlık kombo hasarı, NumPy eğrileriyle sürekli DPS, zırh/büyü nüfuzu kırılımları, **`13` modellenmiş anahtar rün** ve **`17` eşya pasifi** üzerinden matematiksel karşılaştırma yapar.
- **Yetenek Seti Odaklı AI Build & Tam Rün Laboratuvarı (`build_optimizer.py`, `full_rune_page_engine.py`, `ai_build_advisor.py`):**
  Şampiyonun yetenek arketipine ve seçilen rakip direnç/tehdit profiline göre çoklu çekirdek eşya dizilimlerini ve Sezon 16 tam 9 slotlu rün sayfasını (anahtar rün, 3 birincil, 2 ikincil, 3 stat parçası) sıralar. OpenAI uyumlu LLM açıklamalarını (`groq`, `openai`, `deepseek`), API anahtarı gerektirmeyen `offline` yedek modu ve kullanıcı varyasyon geri bildirimlerini destekler.
- **Otomatik Riot Data Dragon + CommunityDragon Yama Farkı Motoru (`ddragon_sync.py`, `cdragon_enricher.py`, `patch_diff_engine.py`, `meta_shift_analyzer.py`):**
  Eşzamanlılık kilidi (lock) altında Riot Data Dragon şampiyon/eşya/rün verilerini ve CommunityDragon yetenek katsayılarını senkronize eder; ardışık yamalar (örneğin `16.22.1` ve `16.23.1`) arasındaki sayısal farkları çıkarır ve isteğe bağlı serbest yama metinlerini LLM ile ayrıştırır (`POST /api/v1/parse-patch`).
- **25 Resmi LoL Arayüz Dili (`locale_service.py`):**
  Hem arayüz metinlerini hem de backend simülasyon/build etiketlerini **resmi `leagueoflegends.com` üzerindeki `25` dilin tamamında** (`tr_TR`, `en_US`, `ko_KR`, `ja_JP`, `zh_TW`, `th_TH`, `vi_VN`, `id_ID` ve sağdan sola RTL destekli `ar_AE` dahil) yerelleştirir.
- **İstemciden Bağımsız / Zero-Vanguard Güvenliği:**
  League of Legends istemcisine bağlanmaz, oyun belleğini (memory) okumaz, ekran içi overlay enjekte etmez veya girdi otomasyonu yapmaz. Yalnızca herkese açık statik yama verileri ve kullanıcı tarafından seçilen sandbox senaryoları üzerinden çalışır.

---

## Mimari

```mermaid
flowchart TD
    UI["React 19 + TypeScript + Vite Arayüzü"] --> API["FastAPI REST API (/api/v1)"]
    API --> ENG["Çatışma Simülatörü ve Build Optimizer (NumPy)"]
    API --> SYNC["Yama Senkronizasyon ve Fark Hattı"]
    API --> ADV["AI Build Danışmanı ve Dil Servisi (25 Dil)"]
    ENG --> PG["PostgreSQL 16 (Anlık Görüntüler, Rünler, Farklar, Loglar)"]
    SYNC --> PG
    API --> RED["Redis 7 (Simülasyon ve Öneri Önbelleği)"]
    SYNC --> DD["Riot Data Dragon CDN"]
    SYNC --> CD["CommunityDragon JSON"]
    ADV --> LLM["OpenAI Uyumlu LLM Sağlayıcısı (İsteğe Bağlı / Offline Mod)"]
```

---

## Teknoloji Yığını

| Katman | Teknolojiler |
| :--- | :--- |
| **Backend** | Python `3.12+`, FastAPI `0.115.5`, Uvicorn `0.32.0`, Pydantic `2.9.2`, NumPy `2.1.3`, HTTPX `0.27.2` |
| **Veritabanı & Önbellek** | SQLAlchemy `2.0.36`, PostgreSQL `16` (`psycopg 3.2.3`), Redis `7` (`redis 5.2.0`) |
| **Frontend** | React `19`, TypeScript `6`, Vite `8`, Tailwind CSS `v4`, Recharts `3`, Lucide Icons |
| **Veri Kaynakları** | Riot Data Dragon CDN, CommunityDragon statik verileri, OpenAI uyumlu LLM uç noktaları |
| **Test & Kalite** | Pytest `8.3.4`, ESLint + TypeScript tip denetimi (`tsc -b`) |

---

## Hızlı Kurulum

### Gereksinimler

- **Python** `3.12+`
- **Node.js** `20+` ve `npm`
- **Docker** & **Docker Compose** (yerel PostgreSQL 16 ve Redis 7 konteynerleri için)

### 1. PostgreSQL ve Redis Servislerini Başlatın

Proje ana dizininden çalıştırın:

```bash
docker compose up -d
```

Bu komut `5432` portunda `patchdiff_postgres` (`user: patchdiff`, `db: patchdiff_db`) ve `6379` portunda `patchdiff_redis` servislerini ayağa kaldırır.

### 2. Ortam Değişkenlerini Yapılandırın

`.env.example` dosyasını `.env` olarak kopyalayıp kendi ayarlarınıza göre düzenleyin:

```bash
cp .env.example .env
```

[`.env.example`](.env.example) içindeki temel değişkenler:

| Değişken | Açıklama | Örnek / Varsayılan |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy bağlantı adresi | `postgresql+psycopg://patchdiff:patchdiff_secret@localhost:5432/patchdiff_db` |
| `REDIS_URL` | Redis önbellek bağlantı adresi | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | AI açıklama modu (`groq`, `openai`, `deepseek` veya `offline`) | `offline` (anahtarsız mod) veya `groq` |
| `LLM_BASE_URL` | OpenAI uyumlu temel URL | `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | Sağlayıcı API anahtarı (`LLM_PROVIDER=offline` iken gerekmez) | `your_llm_api_key_here` |
| `LLM_MODEL` | Kullanılacak sohbet modeli | `openai/gpt-oss-20b` |
| `DDRAGON_VERSION` | Başlangıç Riot Data Dragon yama sürümü | `16.23.1` |
| `DDRAGON_LANG` | Varsayılan Riot Data Dragon dili | `tr_TR` |
| `AUTO_SYNC_ENABLED` | Arka plan otomatik yama kontrolü | `true` |
| `AUTO_SYNC_INTERVAL_MINUTES` | Otomatik senkronizasyon aralığı (dakika) | `360` |

> [!TIP]
> **%100 Ücretsiz Offline Mod:** `.env` dosyasında `LLM_PROVIDER=offline` ayarlayarak **hiçbir harici LLM API anahtarı veya ücret ödemeden** tüm simülatörü, build motorunu ve yama analizini çalıştırabilirsiniz.

### 3. Backend Kurulumu ve Başlatma

```bash
cd backend
python -m venv .venv
```

Sanal ortamı aktifleştirin:

- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source .venv/bin/activate`

Bağımlılıkları yükleyin, veritabanı tablolarını oluşturun, isteğe bağlı başlangıç verisini yükleyin ve FastAPI sunucusunu başlatın:

```bash
pip install -r requirements.txt
python -m app.init_db
python -m app.seed_data   # İsteğe bağlı: örnek başlangıç şampiyon/eşya verilerini yükler
uvicorn app.main:app --reload
```

Backend API `http://127.0.0.1:8000` adresinde çalışacaktır (`/docs` üzerinden Swagger arayüzüne ulaşabilirsiniz).

### 4. Frontend Kurulumu ve Başlatma

Proje ana dizininde ikinci bir terminal açarak çalıştırın:

```bash
cd frontend
npm install
npm run dev
```

Tarayıcınızda Vite'ın verdiği yerel adresi (genellikle `http://localhost:5173`) açın.

---

## REST API Özeti

| Metot | Uç Nokta | Amaç |
| :--- | :--- | :--- |
| `GET` | `/` | Servis bilgisi ve sürüm (`1.0.0`) |
| `GET` | `/api/v1/health` | Sağlık kontrolü (veritabanı ve Redis bağlantısı) |
| `GET` | `/api/v1/champions` | Yerelleştirilmiş şampiyon adları ve temel nitelikler |
| `GET` | `/api/v1/items` | Sihirdar Vadisi eşyaları ve ikon verileri |
| `POST` | `/api/v1/parse-patch` | Ham yama notu metnini yapılandırılmış farklara dönüştürme |
| `POST` | `/api/v1/simulate` | Seviye 1–20 A/B yama çatışma ve EHP simülasyonu |
| `GET` | `/api/v1/patches/latest` | Son senkronize yamalar ve otomatik fark akışı |
| `POST` | `/api/v1/patches/sync` | Riot Data Dragon + CommunityDragon senkronizasyonunu tetikleme |
| `GET` | `/api/v1/patches/{version}/diffs` | Belirli bir yamanın yapılandırılmış değişiklik listesi |
| `POST` | `/api/v1/recommend-builds` | Sıralı build önerileri, tam 9 slot rün ve AI gerekçesi |
| `POST` | `/api/v1/feedback` | Build varyasyonları için kullanıcı geri bildirimi (`accepted` / `rejected`) |
| `GET` | `/api/v1/feedback/summary` | Toplanmış varyasyon tercih metriklerini görüntüleme |

---

## Doğrulama ve Test Komutları

Değişiklik göndermeden önce tam test, lint ve derleme kontrollerini çalıştırın:

```bash
# Backend birim ve entegrasyon test paketi (izole bellek içi SQLite + taklit Redis)
cd backend
python -m pytest

# Frontend lint ve üretim derleme doğrulaması
cd ../frontend
npm run lint
npm run build
```

---

## Yol Haritası (Zero-Vanguard Mimarisi)

PatchDiff Sandbox, Riot Games Geliştirici Politikaları ile tam uyumlu kademeli bir açık kaynak yol haritası izler:

- **`v1.0.0` (Mevcut Sürüm):** Uçtan uca yama simülatörü, Data Dragon + CommunityDragon otomatik senkronizasyon hattı, AI build ve tam 9 slot rün laboratuvarı, 25 resmi LoL dili ve MIT açık kaynak depo altyapısı.
- **`v2.0.0` (Dalga 1 — İstemcisiz Meta Zekâsı):** Sıfırıncı Dakika Gizli Kazananlar & Yama Efsane Çürütücüsü, topluluk ARAM denge çarpanları (`aram.bin.json`), minyon dalgası tekmeleme eşikleri ve Öndeyken/Gerideyken dinamik build pivotları.
- **`v2.5.0` (Dalga 2 — %100 Web Pratik Araçları):** Tek tıkla LoL Resmi Eşya Seti JSON panoya kopyalama destekli web altın kırılma noktası koçu ve 5v5 hayatta kalma / CC sıvışma matrisi.
- **`v3.0.0` (Dalga 3 — Resmi Riot Match-V5 Maç Sonu Denetimi):** Yalnızca resmi Riot Production API anahtarı üzerinden çalışan sunucu tabanlı maç sonu zaman çizelgesi kıyaslaması ("Dükkâncı Mahkemesi").

---

## Katkı ve Güvenlik

- Kod standartları (%100 İngilizce kaynak kod/yorum zorunluluğu, şampiyon adı sabitlememe kuralı ve test kuralları) için [CONTRIBUTING.md](CONTRIBUTING.md) dosyasını okuyun.
- Gizli anahtar temizliği, Riot Vanguard uyumluluğu ve güvenlik açığı bildirimi için [SECURITY.md](SECURITY.md) dosyasını inceleyin.
- Sürüm geçmişi [CHANGELOG.md](CHANGELOG.md) dosyasında tutulmaktadır.

---

## Lisans

[MIT Lisansı](LICENSE) altında yayınlanmıştır.

---

## Yasal Uyarı (Riot Games Legal Jibber Jabber)

PatchDiff Sandbox isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.

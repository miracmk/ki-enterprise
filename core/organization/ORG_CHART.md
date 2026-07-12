# KI Enterprise — Organizasyon Şeması

Bu dosya, şirketin AI-yönetimli organizasyon yapısını ve her role atanmış skill'leri özetler. Karakter tanımları için tek doğruluk kaynağı `core/personas/PERSONAS.md`'dir; skill tanımlarının tek doğruluk kaynağı `core/skills/skills_registry.py` (`owner_role`/`source` alanları) ve rol→skill gruplaması `core.env:EXECUTIVE_ROLE_SKILLS`'tir. Bu dosya o ikisinin **okunabilir özeti**dir — kod değil, biri değişirse burası da elle güncellenmeli.

```
Miraç (kurucu)
   │
   ▼
Aethris (kişisel asistan — core/aethris, port 5008)
   │  (delegate-to-ceo ile niyet iletir, kendisi karar almaz)
   ▼
John — CEO (core/ceo, port 5000)
   │  Doğal dil sohbet: POST /api/v1/ceo/chat
   │  İş dağıtımı: POST /api/v1/ceo/dispatch (Temporal workflow)
   ▼
Executive Board (core/executives, port 5003)
   ├── CTO  — Kai   (teknik değerlendirme)
   ├── CFO  — Vera  (maliyet kapısı — cost_flag)
   ├── CMO  — Iris  (büyüme/marka)
   ├── COO  — Leo   (süreç/yürütme)
   └── CISO — Nora  (güvenlik)
   ▼
Department Managers (core/departments, port 5004)
   development / research / marketing / support (aktif)
   finance / security / design / video / operations (henüz workflow'a bağlı değil)
   ▼
Workers (core/workers, port 5005)
   Deniz(dev) / Emre(research) / Ada(marketing) / Zeynep(support) ...
   ▼
Projects (core/projects, port 5006)
   ki-business / ki-social / ki-wallet / ki-form / ki-management / aethris
```

## Rol → Skill ataması (core/skills, port 5007)

Skill'ler `core/skills/skills_registry.py`'de tanımlı, `POST /api/v1/skills/{name}/execute` ile gerçekten çalıştırılabilir. Aşağıdaki tablo hangi yönetici rolünün hangi skill'in "sahibi" (owner_role) olduğunu gösterir — bu sadece organizasyonel gruplamadır, worker'ların skill kullanımı Phase 7'nin bilinen kısıtı gereği hâlâ ayrı (persona-bazlı) çalışır.

| Rol | Skill | Kaynak |
|---|---|---|
| **John — CEO** *(Board dışı)* | request-scope-framing | gstack (garrytan/gstack: /office-hours, /plan-ceo-review) |
| | dispatch-orchestration-mode | Multi-Agent-Marketing-Course (The-Swarm-Corporation) |
| **CTO — Kai** | feature-planning | build-order (Phase 7) |
| | bug-investigation | build-order (Phase 7) |
| | test-driven-development-plan | superpowers (obra/superpowers) |
| | systematic-debugging | superpowers (obra/superpowers) |
| | code-review-audit | Anthropic code-review skill |
| | frontend-design-brief | Anthropic frontend-design skill |
| **CFO — Vera** | capital-decision-analysis | finrobot (ai4finance-foundation/finrobot) |
| | cash-runway-projection | ai-cfo-agent (daniel-st3/ai-cfo-agent) |
| | expense-anomaly-scan | ai-cfo-agent (daniel-st3/ai-cfo-agent) |
| | budget-variance-review | cfo-stack (MikeChongCan/cfo-stack) |
| | vendor-cost-audit | cfo-stack (MikeChongCan/cfo-stack) + mevcut maliyet politikası |
| **CMO — Iris** | instagram-content-generation | build-order (Phase 7) |
| | competitor-analysis | build-order (Phase 7) |
| | landing-page-audit | build-order (Phase 7) |
| | competitive-perception-scan | gstack (garrytan/gstack: /browse, /qa, /investigate) |
| | marketing-copy-quality-gate | kai-cmo-harness (cgallic/kai-cmo-harness) |
| | multi-channel-marketing-audit | kai-cmo-harness (cgallic/kai-cmo-harness) |
| | channel-budget-allocation | kai-cmo-harness (cgallic/kai-cmo-harness) |
| | campaign-ab-test-analysis | Multi-Agent-Marketing-Course (The-Swarm-Corporation) |
| **COO — Leo** | institutional-memory-digest | claude-mem (thedotmack/claude-mem) |
| | production-readiness-check | gstack (garrytan/gstack: /ship, /land-and-deploy) |
| | operational-retro-report | gstack (garrytan/gstack: /retro) |
| **CISO — Nora** | security-vulnerability-audit | Anthropic security-review skill |
| | stride-threat-model | gstack (garrytan/gstack: /cso) |
| | high-risk-action-guardrail-check | gstack (garrytan/gstack: /careful, /freeze, /guard) |
| **Worker — development** *(Board dışı, owner_role="development")* | adversarial-test-case-design | gstack (garrytan/gstack: /qa) |

## Dış kaynaklardan uyarlanan 8 yeni skill — ne değişti, ne değişmedi

Hiçbir dış repo'nun kodu satır satır kopyalanmadı (bu sistemin skill'leri Claude Code slash-command'ı değil, `name/description/tools/inputs/outputs/workflow` şemasında AI Gateway'e giden çalıştırılabilir JSON tanımlarıdır — bkz. `core/skills/main.py`). Bunun yerine her kaynağın **metodolojisi** bu şemaya uyarlandı:

- **superpowers** (`github.com/obra/superpowers`) — TDD (RED-GREEN-REFACTOR) ve 4 fazlı sistematik debugging disiplini → `test-driven-development-plan`, `systematic-debugging`.
- **claude-mem** (`github.com/thedotmack/claude-mem`) — oturumlar-arası sıkıştırılmış hafıza özeti fikri → `institutional-memory-digest` (KI Enterprise'ın zaten var olan Memory Layer'ına ek bir "özetleme" skill'i olarak, ayrı bir hafıza sistemi KURULMADI).
- **gstack** (`github.com/garrytan/gstack`) — algı (`/browse`, `/qa`, `/investigate`) ve yürütüm (`/ship`, `/land-and-deploy`) skilleri → `competitive-perception-scan`, `production-readiness-check`.
- **Anthropic** frontend-design / code-review / security-review skilleri → `frontend-design-brief`, `code-review-audit`, `security-vulnerability-audit`.

## CFO (Vera) — finans skilleri (2026-07-12 eklendi)

Üç dış repo incelendi, hiçbiri doğrudan uygun değildi (FinRobot gerçek piyasa verisi/DCF motoru, cfo-stack gerçek Beancount defteri/banka entegrasyonu, ai-cfo-agent gerçek CSV/KPI pipeline'ı gerektiriyor — bunların HİÇBİRİ henüz bu sistemde yok). Metodolojileri, mevcut skill formatına (LLM-narrated, gerçek sayısal motor değil) uyarlandı:

- **finrobot** (`ai4finance-foundation/finrobot`) — "deterministic compute, LLM narration" ilkesi + bull/base/bear senaryo disiplini → `capital-decision-analysis`.
- **ai-cfo-agent** (`daniel-st3/ai-cfo-agent`) — runway/burn-rate/sağlık-skoru kavramı, anomali tespiti sezgisel kuralları → `cash-runway-projection`, `expense-anomaly-scan`.
- **cfo-stack** (`MikeChongCan/cfo-stack`) — C.L.E.A.R. döngüsünün Extract/Report fazları (bütçe sapma analizi, reconciliation) → `budget-variance-review`, `vendor-cost-audit` (ikincisi doğrudan şirketin var olan "önce ücretsiz → self-hosted → açık kaynak → ücretli" politikasına bağlanır).

**Önemli sınır (o an geçerliydi, aşağıda giderildi):** Bu 5 skill LLM'e verilen metin/rakamları YORUMLAR, kendisi veri ÇEKMEZ. Gerçek veri artık `core/finance` servisinden gelir, oradan alınan gerçek rakamlar bu skill'lerin `inputs` alanına (`financial_snapshot`, `known_numbers` vb.) elle/CEO tarafından aktarılır — otomatik boru hattı (skill'in kendisi finance servisini çağırması) henüz kurulmadı.

## core/finance (port 5011) — gerçek veri katmanı (2026-07-12 eklendi)

Kullanıcının "gerçek banka, gerçek piyasa verisi çekelim" talebiyle kuruldu. Yeni, bağımsız bir servis (diğer 11/12 servisle aynı mimari: FastAPI + kendi venv + Memory Layer'a HTTP ile yazar/okur).

**Gerçekten çalışan 5 uç (canlı test edildi):**
- `POST /api/v1/finance/statements/upload` — banka ekstresi/CSV'sini (`date,description,amount[,category]`) **deterministik** (Python `csv` modülü, LLM'e gitmez — FinRobot'un "deterministic compute, LLM narration" ilkesi) ayrıştırır, Memory Layer'a (`mem_type=global`, `scope_key="finance:transactions"`) satır-bazlı idempotency_key ile kaydeder (aynı ekstre iki kez yüklenirse çift kayıt OLUŞMAZ — canlı testte doğrulandı).
- `GET /api/v1/finance/transactions` — kayıtlı işlemleri döner.
- `GET /api/v1/finance/market/crypto/{coin_id}` — CoinGecko'dan CANLI kripto fiyatı (anahtarsız).
- `GET /api/v1/finance/market/stock/{ticker}` — Yahoo Finance chart API'sinden CANLI hisse fiyatı (anahtarsız; `AAPL`, `THYAO.IS` gibi Yahoo sembolleri).
- `GET /api/v1/finance/market/fx/{base}/{quote}` — open.er-api.com'dan CANLI döviz kuru (anahtarsız).

**Canlı testte bulunup düzeltilen 2 kaynak sorunu:** Stooq (ilk seçilen hisse kaynağı) Cloudflare JS-challenge sayfası döndürüyordu (User-Agent'tan bağımsız, tutarsız) → Yahoo Finance'e geçildi. exchangerate.host artık ücretsiz erişim için access_key istiyor (politika değişmiş) → open.er-api.com'a geçildi. İkisi de canlı curl testleriyle doğrulanarak seçildi, varsayımla bırakılmadı.

**Bilerek kapsam dışı bırakılanlar (kullanıcıyla netleştirildi):**
- **Gerçek banka API bağlantısı yok** — kullanıcı "banka API'si yok, CSV yeter" dedi; gerçek bir banka/Open Banking entegrasyonu ayrı bir karar (kimlik bilgisi/erişim izni gerektirir).
- **Rakip/ürün fiyatlandırma verisi CANLI ÇEKİLMEZ** — hedef-spesifik scraping ayrı, çok daha büyük bir mühendislik/yetkilendirme kararı; CMO/CFO hâlâ `competitor-analysis` (LLM akıl yürütmesi) kullanır.
- **LiteLLM'in kendi `/spend` uçları** (şirketin gerçek AI/bulut maliyeti) mevcut master key ile 403 dönüyor (proxy_admin scope kısıtı) — `infrastructure/litellm` config değişikliği gerektirir, ayrı onay konusu.

## CMO (Iris) — pazarlama skilleri (2026-07-12 eklendi)

Üç dış repo incelendi:

- **kai-cmo-harness** (`cgallic/kai-cmo-harness`) — en doğrudan isabetli kaynak: kalite kapıları (Four U's başlık/kopya skoru + yasak kelime kontrolü), çoklu-kanal pazarlama denetimi (SEO/içerik/email/reklam/CRO), aşama-bazlı kanal/bütçe tahsis planlaması → `marketing-copy-quality-gate`, `multi-channel-marketing-audit`, `channel-budget-allocation`.
- **Multi-Agent-Marketing-Course** (`The-Swarm-Corporation`) — somut tek yeni katkı: A/B test sonucu yorumlama disiplini → `campaign-ab-test-analysis`.
- **metagpt** (`foundationagents/metagpt`) — incelendi ama CMO'ya özgü yeni bir katkı **bulunmadı**: sunduğu "rekabet analizi/gereksinim dokümanı" zaten `competitor-analysis` (CMO) ve `feature-planning` (CTO) ile karşılanıyor, kendisi asıl bir yazılım-geliştirme SOP çerçevesi (PM/Architect/Engineer rolleri) — buradan bilerek skill eklenmedi.

## CEO / Executive Board / Worker skilleri (2026-07-12, 3. tur eklendi)

Dört repo incelendi — bu turun odağı CEO (John), Executive Board'un geri kalanı (CISO/COO) ve worker katmanıydı:

- **gstack** (`garrytan/gstack`) — ikinci, çok daha derin bir tur: `/office-hours`+`/plan-ceo-review` (talebi zorlayıcı sorularla çerçeveleyip kapsam kararı verme) → `request-scope-framing` (John/CEO); `/cso` (STRIDE tehdit modeli, güven-eşikli) → `stride-threat-model` (CISO); `/careful`+`/freeze`+`/guard` (yıkıcı komut uyarısı/kilit) → `high-risk-action-guardrail-check` (CISO); `/retro` (operasyonel retrospektif) → `operational-retro-report` (COO); `/qa` (gerçek tarayıcı testi — burada gerçek tarayıcı YOK, LLM akıl yürütmesine uyarlandı) → `adversarial-test-case-design` (**worker-tier**, `owner_role="development"`).
- **Multi-Agent-Marketing-Course** (`The-Swarm-Corporation`) — sequential/parallel/dynamic orkestrasyon deseni → `dispatch-orchestration-mode` (John/CEO: bir talebin departmanlara sırayla mı paralel mi dağıtılacağına karar verir).
- **foundationagents/metagpt** — **İKİNCİ KEZ** incelendi (CMO turunda da incelenmişti), yine özgün bir katkı bulunamadı: "Code=SOP(Team)" felsefesi kavramsal olarak gstack'in plan-review zincirinin aynı fikrini taşıyor, somut hiyerarşi/onay mekanizması genel dokümanlardan çıkarılamadı.
- **RunMaestro/Maestro** — incelendi, skill eklenmedi: bu bir **masaüstü uygulaması** (git worktree/oturum yönetimi, bir insanın birden fazla kodlama ajanını yönetmesi için), akıl yürütme/skill içeriği taşımıyor. En yakın kavramı (Group Chat: stratejik karar için multi-ajan istişaresi) zaten `core/executives`'in review ucunda karşılanıyor.

**Not — `owner_role` genişletildi:** Bu turda `owner_role` artık `core/executives:ROLES` (cto/cfo/cmo/coo/ciso) ile sınırlı değil — `"ceo"` (Board dışı, ayrı `core/ceo` servisi) ve `"development"` (worker/departman katmanı) da kullanıldı. Worker-tier skill'ler `core/workers`'a henüz OTOMATİK entegre değil (bilinen kısıt, aşağıda tekrar not edildi) — `adversarial-test-case-design` şimdilik sadece `POST /api/v1/skills/adversarial-test-case-design/execute` ile doğrudan çağrılabilir.

## John (CEO) — karakter genişletmesi + Ki Ecosystem canlı taraması (2026-07-12, gerçek bir hatadan yola çıkarak)

**Tetikleyen olay:** Miraç Telegram'da John'a "tüm Ki Ecosystem'i tara ve projeleri listele" dedi. Bridge bunu YANLIŞ şekilde bir iş talebi (`workflow=research_request`, `project="Ki Ecosystem"`) olarak sınıflandırdı, CEO bunu geçersiz proje adıyla 422 ile reddetti, kullanıcı ham JSON hatasını Telegram'da gördü. Kullanıcı bunu "gerçek bir CEO ile konuşur gibi konuşmak istiyorum" talebiyle bildirdi ve ayrıca John'un karakterinin, sattığı şeyin ürün değil itibar/güven/uzmanlık olduğu bir "beyin takımı" lideri profiline göre derinleştirilmesini istedi.

**Kök neden ikiye ayrıldı, ikisi de düzeltildi:**
1. **Yanlış sınıflandırma** — `core/telegram-bridge/main.py:classify_message` artık "mevcut bilgiyi soran/özetleyen istekler (listele, tara, ne durumda) bir iş talebi DEĞİLDİR" kuralını açıkça içeriyor, bunlar `workflow=none`'a düşüp doğrudan `chat_as_ceo`'ya (→ `/api/v1/ceo/chat`) yönleniyor.
2. **`core.env:PROJECTS`'in gerçeklikten kopukluğu** — statik liste (`ki-business, ki-social, ki-wallet, ki-form, ki-management, aethris`) gerçek `/opt/ki-ecosystem` klasörleriyle (12 gerçek app, örn. `ki-chat`, `ki-life-os`, `ki-software` hiç listede yoktu) örtüşmüyordu. Kalıcı çözüm: **iki katmanlı proje modeli**. `core/ceo` artık `GET /api/v1/ceo/ecosystem-scan` ile `/opt/ki-ecosystem/{apps,websites}`'i **CANLI, doğrudan diskten** tarar (`_scan_ecosystem_subdir` — `docker-compose.yml`/`README.md` varlığına göre aktif/planlanan ayrımı yapar, `-config-archive` klasörlerini hariç tutar). `POST /api/v1/ceo/dispatch`'in proje validasyonu artık `PROJECTS ∪ ecosystem_tarama_sonucu` birleşimini kabul ediyor — **Miraç yeni bir proje devraldığında sadece `/opt/ki-ecosystem/apps/<ad>/` klasörünü açması yeterli, core.env'e elle dokunmasına gerek yok.** `core.env:PROJECTS` (formal bütçe/roadmap takibi, core/projects Phase 6) ayrı, daha küçük/resmi bir katman olarak kalmaya devam ediyor — biri diğerinin yerine geçmiyor.
3. **Ham hata mesajı** — `handle_dispatch` artık CEO'nun 422 JSON gövdesini olduğu gibi kullanıcıya dökmüyor, John'un karakterine uygun bir cümleye çeviriyor ("'X' diye tanımlı bir projemiz yok, hangisini kastettiğini söylersen hemen başlatırım").

**Canlı testte doğrulandı:** Orijinal hatalı mesaj artık doğru şekilde sohbete düşüyor ve John gerçek tarama verisiyle cevap veriyor; gerçek bir ecosystem projesiyle (`ki-chat`) dispatch denemesi artık `202 Accepted` dönüyor (önceden bu da başarısız olurdu, çünkü `ki-chat` hiçbir zaman `PROJECTS`'te yoktu).

**Karakter genişletmesi:** `CEO_PERSONA` (hem `core/ceo/main.py` hem `core/workflow/activities.py`, kaynak `PERSONAS.md`) kullanıcının verdiği detaylı liderlik profiline göre yeniden yazıldı — temel öncül: "itibar John'un gerçek ürünüdür" (fiziksel ürün satmıyoruz). Beş özellik sisteme gömüldü: (1) soğukkanlı risk-matrisi düşüncesi ("en kötü senaryo nedir?"), (2) şeffaflığı hayatta kalma stratejisi sayma, (3) kararları dayatmak yerine "satmak" (Executive Board'a sunarken konsensüs arama), (4) gerekince statükoyu bozma cesareti, (5) sahadan kopmayan, tempoyu kendi belirleyen operasyonel taraf. Canlı testte doğrulandı: "hangi boş projeye öncelik vermeliyiz" sorusuna John risk/pazar-değeri matrisi + en-kötü-senaryo analiziyle cevap verdi ve kararı dayatmadan Miraç'ın onayına sundu ("Kararı **senin** onayına sunuyorum").

## İptal mekanizması + Telegram konuşma tarzı düzeltmesi (2026-07-12, ikinci gerçek hatadan yola çıkarak)

**Tetikleyen olay:** Miraç Telegram'da bir workflow dispatch ettikten sonra "bu workflowu durdur" dedi. Sistemde **hiçbir iptal ucu yoktu** — `classify_message` bunu zorunlu olarak mevcut workflow türlerinden birine (`feature_request`) sığdırdı ve durdurma isteği, durdurmak yerine **YENİ bir iş** dispatch etti. Ayrıca Miraç'ın kısa bir şikayetine ("bu iş böyle yürümüyor") John dev bir risk-matrisi tablosu + 4 bölümlü numaralı rapor döndürdü — Telegram'a hiç uygun değildi.

**Düzeltmeler:**
1. **Gerçek iptal ucu eklendi** — `POST /api/v1/ceo/dispatch/{workflow_id}/cancel` (`core/ceo/main.py`), Temporal'in `handle.cancel()` (nazik iptal, workflow kendi temizliğini yapabilir) ile. Bu uç daha önce **hiç yoktu**.
2. **telegram-bridge** artık her chat için son dispatch edilen `workflow_id`'yi hatırlıyor (`LAST_DISPATCH_BY_CHAT`), `classify_message`'ın JSON şemasına `"cancel": true|false` alanı eklendi (açık iptal niyeti — "durdur/iptal et/dur" — artık ayrı, öncelikli bir dal olarak işleniyor, asla yeni bir işe dönüşmüyor). `/cancel [workflow_id]` komutu da eklendi (ID verilmezse son dispatch'e düşer).
3. **Telegram-uygun konuşma tarzı** — `core/ceo/main.py`'a `CHAT_STYLE_GUIDANCE` eklendi (SADECE `/api/v1/ceo/chat` için, `core/workflow/activities.py`'deki plan üretimi hâlâ yapılandırılmış/detaylı kalıyor çünkü o gerçekten bir plan istiyor): kısa/gündelik mesajlara 2-5 cümlelik doğrudan cevap, markdown tablo/numaralı rapor YOK — bunlar sadece kullanıcı açıkça "detaylı analiz/rapor yaz" derse kullanılıyor.

**Canlı testte doğrulandı:** Dispatch → "bu workflowu durdur" senaryosu artık gerçekten doğru workflow'u iptal ediyor (yeni iş başlatmıyor). "Bu iş böyle yürümüyor" mesajına John artık kısa, doğrudan bir soruyla cevap veriyor ("Anladım, tam olarak hangi iş akışı sorun yaratıyor?"). Açıkça "detaylı risk analizi/rapor" istendiğinde ise hâlâ derinlemesine, analitik cevap verebiliyor — davranış artık talebe duyarlı, her mesaja aynı ağırlıkta cevap vermiyor.

**Bilinen sınır:** `LAST_DISPATCH_BY_CHAT` süreç-içi bellektir, kalıcı değil — bridge yeniden başlarsa unutulur (kullanıcı `/status` ile workflow_id'yi tekrar sorup `/cancel <id>` ile belirtebilir).

## John (CEO) — doğal dil sohbeti

`core/ceo/main.py`: `POST /api/v1/ceo/chat` — kullanıcı (Miraç) ile serbest, doğal dilde konuşur (karakter: kararlı, doğrudan, az laf çok iş — bkz. `PERSONAS.md`). Bu uç **sadece danışma**dır, otomatik olarak bir workflow tetiklemez; gerçek iş dağıtımı hâlâ `POST /api/v1/ceo/dispatch` ile yapısal olarak yapılır. `core/telegram-bridge` artık kendi persona kopyasını tutmaz, bu uca proxy yapar — tek merkezi kaynak.

**Yürüyen/bekleyen iş raporlama (2026-07-12 düzeltmesi):** Phase 2/8/9'da ÜÇ KEZ bulunan aynı kök neden ("pending_approval_count" hep yanlış/null dönüyordu çünkü Memory'deki `ceo:decisions` SADECE tamamlanmış işleri içeriyor, RUNNING işler hiç kayıt üretmiyordu) burada gerçekten çözüldü: `GET /api/v1/ceo/workflows?status=RUNNING` artık Memory'e değil doğrudan Temporal'ın visibility store'una sorar, `/api/v1/ceo/chat` bu canlı listeyi "son kararlar" (sadece tamamlanmış işler) bağlamından AYRI olarak sistem promptuna ekler. Canlı testte doğrulandı: dispatch edilen bir iş saniyeler içinde John'a "şu anda çalışan tek iş: research_request..." şeklinde doğru raporlatıldı. Not: `_status_to_query_value` fonksiyonu enum adını (`RUNNING`) Temporal'ın beklediği `PascalCase` değere (`Running`) çevirir — ikisini karıştırmak "invalid ExecutionStatus value" hatası verir, canlı testte bulundu ve düzeltildi. Aethris/Dashboard'daki aynı kök nedenli `pending_approval_count`/`expired_approval_count` alanları henüz bu uca taşınmadı (istenirse aynı endpoint'i onlar da kullanabilir).

## Bilinen sınırlamalar

- Skill'ler Worker Pool'a OTOMATİK entegre değil (Phase 7'nin build-order'daki 5 örnek skille aynı bilinen kısıtı) — worker'lar hâlâ sabit persona kullanıyor, tüm skiller (worker-tier `adversarial-test-case-design` dahil) sadece doğrudan `POST /api/v1/skills/{name}/execute` ile çağrılabilir.
- CEO'nun yeni skill'leri (`request-scope-framing`, `dispatch-orchestration-mode`) `POST /api/v1/ceo/dispatch` akışına OTOMATİK bağlanmadı — John bunları henüz kendiliğinden çalıştırmaz, elle/CEO tarafından çağrılması gerekir (tıpkı CFO/CMO skillerinde olduğu gibi, tutarlılık için bilerek aynı sınırda bırakıldı).
- `EXECUTIVE_ROLE_SKILLS` (core.env) ile `skills_registry.py:owner_role` iki ayrı yerde aynı bilgiyi taşıyor (ayrı venv/süreç kısıtı, bkz. `core.env` PROJECTS/WORKFLOW_TO_DEPARTMENT ile aynı gerekçe) — biri değişirse diğeri elle güncellenmeli.

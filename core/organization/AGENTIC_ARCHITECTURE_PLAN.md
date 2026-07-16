# KI Enterprise — Hiyerarşik Agent Mimarisi: Uygulama Planı

**Durum: ONAYLANDI, UYGULANMADI.** Bu dosya başka bir context/oturumdan devam edilebilmesi için yazıldı — burayı okuyan biri (insan ya da ajan) sıfırdan başlamalı, önceki konuşmaya erişimi olmayabilir. Aşağıdaki her şey gerçek araştırma/kod incelemesiyle doğrulandı (varsayım değil).

---

## 1. Hedef

Miraç'ın tarif ettiği hiyerarşi:

```
John (CEO) — Telegram üzerinden Miraç'la konuşur, doğal dil anlama
  └── Board of Chiefs (CTO/CFO/CMO/COO/CISO) — John'a itaat eder, agentic çalışır
       ├── CTO/Kai → Code Review, Architecture Risk, Bug Triage, TDD Plan, Frontend Brief
       ├── CFO/Vera → Profitability, Cash Runway, Expense Anomaly, Budget Variance, Vendor Audit
       ├── CMO/Iris → Rivals Review, Social Media, Content Writer, Marketing Audit, Budget Allocation, A/B Test
       ├── COO/Leo → Ops Retro, Production Readiness, Memory Digest
       └── CISO/Nora → Security Audit, Threat Model, Guardrail Check
```

**Üst-seviye ilke:** Ki-Life-OS (Miraç'ın kişisel asistanı) ve Ki-Enterprise (John + Board) **birbirinden BAĞIMSIZ ama HABERLEŞEN iki ayrı agentic sistem** olmalı — tek bir sürece/instance'a sıkıştırılmayacak, ama iletişim kanalı olacak (bkz. §6).

---

## 2. Neden buradayız — özet geçmiş (yeni okuyan biri için)

1. John (CEO) zaten `core/ceo` (FastAPI, port 5000, Temporal dispatch, cost-approval kapısı) olarak çalışıyordu ve Telegram'a `core/telegram-bridge` (custom `classify_message` LLM sınıflandırıcısı) ile bağlıydı.
2. **Gerçek, canlı bir hata bulundu:** Miraç'ın çok-niyetli bir mesajı ("kibusiness.co'ya git, Cloudflare'den subdomain çek, henüz başlama sadece not al") yanlış sınıflandırılıp geçersiz bir proje adıyla dispatch edilmeye çalışıldı, 422 hatası kullanıcıya ham JSON olarak döküldü.
3. Kök neden araştırıldı (Fable 5): `classify_message` tek-atımlık, kapalı-dünya bir şema kullanıyor, gerçek araç kullanımı (web fetch, Cloudflare DNS) hiç yok.
4. **Keşif:** Bu host'ta zaten olgun, çalışan bir agent framework — **OpenClaw** (`openclaw-gateway.service`) — kurulu. Miraç'ın kişisel asistanı "Ki" (a.k.a. Aethris, bkz. §7 — isimlendirme belirsizliği var) zaten bunun üzerinde çalışıyor, gerçek araç kullanımı (web, Cloudflare, node/cihaz kontrolü, exec onayı) var.
5. Karar: John'u custom Python sınıflandırıcı yerine gerçek bir OpenClaw agent'ı yapmak. `core/ceo`'nun REST uçları (`dispatch/cancel/approve/workflows/ecosystem-scan`) bir MCP sunucusuyla (`ceo-mcp`, zaten yazıldı: `/opt/ki-enterprise/core/ceo-mcp/server.py`) sarıldı.
6. **John, MEVCUT/PAYLAŞILAN OpenClaw instance'ında** (Ki'nin de bulunduğu instance) bir agent olarak kuruldu ve TEST EDİLDİ — çalışma mantığı MÜKEMMEL sonuç verdi: gerçek `kibusiness.co`'ya gitti, gerçek Cloudflare DNS kayıtlarını çekti, ekosistemle karşılaştırdı, gerçek bir iş tutarsızlığı buldu (`kibi-ai` sitede "Live" ama subdomain'i yok), dispatch etmeden not aldı.
7. **KRİTİK, ÇÖZÜLMÜŞ BUG (ama mimari kararı değiştirdi):** Diğer agent'ların (özellikle "main"/Ki) `ceo-mcp` araçlarına (dispatch/approve_cost dahil) erişemediğinden emin olunmaya çalışıldı (`agents.list[id].tools.deny`). Üç farklı pattern denendi (`ceo-mcp.*`, `mcp__ceo-mcp__*`, `ceo-mcp__*`) — SONUNCUSU (`ceo-mcp__*`) kod seviyesinde doğru pattern olduğu KANITLANDI (`denylistBlocksMcpServerNamespace`, `/usr/lib/node_modules/openclaw/dist/tool-policy-pipeline-B59DnRAr.js`) ve **`--local` (gömülü) modda ÇALIŞTI** (log kanıtı: "tool policy removed 10 tool(s)... matched ceo-mcp__*"). AMA **gerçek "Gateway üzerinden" modda (Telegram'ın kullanacağı GERÇEK yol, `provider=claude-cli`/cli-backend) deny HİÇ UYGULANMADI** — main hâlâ ceo-mcp'yi çağırabildi. Bu, OpenClaw'un KENDİ kodunun kabul ettiği bir sınırlama: ACP/cli-backend modunda per-tool `deny` (görünürlük filtresi) çalışmıyor (`ACP_UNSUPPORTED_INHERITED_TOOL_DENY` listesi, "Use runtime=subagent" hatası).
8. **Bu yüzden karar değişti:** Aynı OpenClaw instance'ı içinde "main" (Ki) ile "john" (CEO) arasında tool-deny ile izolasyon sağlamak GÜVENİLMEZ. Miraç'ın kararı: **John + tüm Board + skill-tabanlı sub-görevleri, Ki'nin mevcut instance'ından TAMAMEN BAĞIMSIZ, yeni/ayrı bir OpenClaw instance'ına taşı** (`openclaw --profile <isim>` ile izole state-dir/config, ayrı systemd servisi). Bu şekilde izolasyon sorunu MİMARİ OLARAK ortadan kalkıyor (aynı süreçte başka bir "yabancı" agent olmadığı için sızıntı riski yok).
9. **İkinci araştırma turu (Fable 5):** CrewAI/LangChain bu host'ta KURULU DEĞİL, kurulumu ağır, host'un kaynak marjı yok (15GB RAM'in 9.7GB'ı dolu, **4GB swap'ın TAMAMI dolu** — bu genel bir host-sağlığı endişesi, bu görevden bağımsız ayrıca göz atılmalı). OpenClaw'un KENDİ subagent mekanizması (`sessions_spawn` tool'u + `agents.list[id].subagents.allowAgents` config'i) yeterli VE güvenilir bulundu — çünkü bu, `tools.deny` (görünürlük filtresi, buggy) ile AYNI KATMAN DEĞİL: `sessions_spawn` çağrısının izin kontrolü (`resolveSubagentTargetPolicy`) gateway sürecinin İÇİNDE, SUNUCU TARAFINDA (execute-time) yapılıyor — model ne isterse istesin, `allowAgents` listesinde yoksa `status:"forbidden"` döner. Kod kanıtı: `openclaw-tools-DnJ9m035.js:11796`, `acp-spawn-DI_8oKzY.js:905`.
10. **core/skills (port 5007, 28 çalıştırılabilir skill, `owner_role` etiketli)** zaten Miraç'ın istediği "sub-agent" (Rivals Review, Profitability vb.) işlevini karşılıyor — yeni skill YAZILMAYACAK, sadece rol-bazlı MCP sunucularıyla ilgili Chief'e sunulacak.

---

## 3. Mevcut durum — ne YAPILDI, ne YARIM KALDI (implementasyona başlamadan önce KONTROL ET)

**Yapıldı (ama MUHTEMELEN paylaşılan/eski instance'da — taşınması/temizlenmesi gerekebilir, bkz. Faz A):**
- `/opt/ki-enterprise/core/ceo-mcp/server.py` — ceo-mcp MCP sunucusu (6 tool: ecosystem_scan, list_workflows, get_dispatch_status, dispatch_project, cancel_workflow, approve_cost). **Kod olarak sağlam, konum/bağlama değişebilir.**
- `~/.openclaw/workspace/john/` — John'un workspace'i (IDENTITY/SOUL/AGENTS/TOOLS/USER/HEARTBEAT.md). **İçerik iyi, muhtemelen YENİ instance'a KOPYALANMALI.**
- `openclaw.json`'da (PAYLAŞILAN/eski instance) `agents.list` içinde "john" girdisi + 11 diğer agent'ta (main, mind-coach, financial-advisor, health-coach, business-manager, social-media, research-desk, life-secretary, studio, device-control, self-improvement) `tools.deny: ["ceo-mcp__*"]` denemeleri var. **BUNLAR TEMİZLENMELİ** (yeni ayrı instance'a geçilince bu paylaşılan instance'ta ceo-mcp/john'a dair hiçbir iz KALMAMALI — Ki'nin instance'ı John'dan haberdar olmamalı).
- Test sürecinde Temporal'da 6 gerçek/test workflow'u dispatch edilip SONRA iptal edildi (`research_request-test-report-1783872883`, `research_request-15363276...`, `new_project-3eb892de...`, `feature_request-fb446c80...`, `new_project-79d36025...`, `research_request-8893b718...`) — hepsi CANCELED durumda, temiz, ekstra işlem gerekmiyor.
- `core.env`, `core/organization/ORG_CHART.md`, `core/personas/PERSONAS.md` zaten güncel (CEO_PERSONA, ekosistem tarama, cancel ucu, skill registry — hepsi `core/ceo` REST katmanında SAĞLAM, bunlara dokunulmayacak).

**Yapılmadı:**
- Yeni, bağımsız OpenClaw instance'ı (profile) HENÜZ KURULMADI.
- 5 Chief agent'ı (CTO/CFO/CMO/COO/CISO) HENÜZ YOK.
- Rol-bazlı `skills-mcp-*` sunucuları HENÜZ YAZILMADI.
- Telegram binding HENÜZ YAPILMADI (John'un kendi botu `JOHN_BOT_TOKEN`, `/opt/ki-enterprise/core/telegram-bridge/.env`'de duruyor, hiçbir OpenClaw instance'ına henüz bağlanmadı).
- Aethris↔John iletişim protokolü HENÜZ TASARLANMADI (bkz. §6, bu turda eklendi).

---

## 4. Uygulama Fazları

### Faz A — Temizlik (YENİ, bu turda eklendi)
Paylaşılan/eski OpenClaw instance'ından (Ki'nin instance'ı) şunları kaldır:
- `openclaw mcp remove ceo-mcp` (eğer o instance'da kayıtlıysa).
- `openclaw agents delete john` (o instance'daki "john" girdisini sil — workspace dosyalarını SİLMEDEN önce `~/.openclaw/workspace/john/`i yeni instance'ın state-dir'ine KOPYALA).
- Diğer 11 agent'taki `tools.deny: ["ceo-mcp__*"]` girdilerini temizle (artık gereksiz, o instance'ta ceo-mcp olmayacak).
- **Doğrulama:** `openclaw agents list` (eski instance) artık "john" göstermemeli, `openclaw mcp list` "ceo-mcp" göstermemeli.

### Faz 0 — Yeni İzole Instance + Kuru Test
1. `openclaw --profile ki-enterprise ...` ile yeni, izole state-dir/config kur (Ki'nin `~/.openclaw`'ına DOKUNMA, ayrı `~/.openclaw-ki-enterprise` gibi bir dizin). Ayrı systemd servisi (`openclaw-gateway-enterprise.service` gibi) — Ki'nin servisiyle KARIŞMASIN, farklı port.
2. Bu yeni instance'a `ceo-mcp`'yi tekrar kaydet (`openclaw mcp add`, aynı server.py, aynı env).
3. John'u bu yeni instance'a agent olarak ekle (`openclaw agents add john ...`), workspace dosyalarını (Faz A'da kopyalanan) kullan.
4. **Tek bir skills-mcp prototipi** yaz: `/opt/ki-enterprise/core/skills-mcp/server.py`, `OWNER_ROLE` env'ini okur, `core/skills/skills_registry.py:SKILLS`'i `owner_role == $OWNER_ROLE` ile filtreler, her skill için MCP tool üretir (gövde: `POST core/skills:5007/api/v1/skills/{name}/execute`, `INTERNAL_API_KEY` ile).
5. `OWNER_ROLE=cfo` ile elle çalıştır, `tools/list`'in SADECE CFO skill'lerini döndürdüğünü doğrula.
- **Doğrulama:** `openclaw agent --agent john --local` (yeni instance'ta) ile ecosystem_scan/dispatch akışının hâlâ doğru çalıştığını (önceki testteki gibi) tekrar doğrula — instance taşındığı için regresyon olmadığından emin ol.
- **Rollback:** Yeni instance'ı komple sil (`rm -rf ~/.openclaw-ki-enterprise`), Ki'nin instance'ı hiç etkilenmedi.

### Faz 1 — Beş Chief Agent Tanımı
- Her Chief için workspace + kimlik dosyaları (John'unkiyle aynı şablon), `PERSONAS.md`'deki Kai/Vera/Iris/Leo/Nora karakterlerinden uyarlanır.
- **Model:** John ile tutarlı — LiteLLM/ki-cloud alias (native anthropic değil, maliyet tek noktadan izlenir).
- **AGENTS.md kuralı (her Chief):** "Sen John'un iç danışmanısın. Telegram'a/Miraç'a DOĞRUDAN yazmazsın. Sadece kendi skills-mcp araçlarını kullanır, analiz döner, John'a rapor edersin. Para/maliyet onaylayamazsın, iş dispatch edemezsin."
- **Doğrulama:** Her Chief `openclaw agent --agent <chief> --local` ile tek başına spawn olup kendi skill'ini çağırabilmeli.

### Faz 2 — Rol-Bazlı skills-mcp Kayıtları
- **Tek script + 5 config instance'ı** (`openclaw mcp add skills-mcp-cto/-cfo/-cmo/-coo/-ciso`, hepsi aynı `server.py`, farklı `OWNER_ROLE` env'i).
- Her kayıt SADECE ilgili Chief'in agent scope'una bağlanır.
- **Doğrulama:** Her Chief oturumunda `tools/list` sadece o rolün skill sayısını göstermeli, başka rolün skill'i SIZMAMALI.

### Faz 3 — Sub-görev (Skill) Eşleştirmesi — yeni skill YOK
Zaten var olan `core/skills/skills_registry.py` skill'leri "sub-agent" ismiyle sunuluyor (bkz. §1 tablosu). Kod değişikliği yok, sadece dokümantasyon/isimlendirme.

### Faz 4 — John'un Subagent Yetkilendirmesi
- `agents.list[john].subagents.allowAgents: ["cto","cfo","cmo","coo","ciso"]`.
- `maxChildrenPerAgent: 5` (varsayılan, 5 Chief paralel çağrılabilsin).
- `maxSpawnDepth: 1` (varsayılan, DEĞİŞTİRME — Chief'ler başka agent spawn edemez, doğal 2-seviyeli sınır).
- `runTimeoutSeconds: ~300`.
- **AGENTS.md (John):** "Bağımsız analizler için Chief'leri PARALEL çağır. Bir Chief'in çıktısı diğerinin girdisiyse SIRAYLA çağır. Sentezi sen yap, Miraç'a/Aethris'e TEK cevap dön."
- **Doğrulama:** John'a çok-disiplinli bir görev ver, paralel spawn + sentez gözlemle. `allowAgents` dışı bir agent istenirse `status:"forbidden"` döndüğünü doğrula.
- **Kaynak notu:** 5 Chief paralel spawn = 5 eşzamanlı LLM çağrısı; RAM/swap zaten dar (§2.9), önce 2 paralel ile test et, sonra 5'e çık.

### Faz 5 — Yetki Sızıntısı Garantisi (approve_cost)
- Chief agent'lara **ceo-mcp HİÇ bağlanmaz**. Chief'in tek MCP'si kendi skills-mcp'sidir — `approve_cost`/`dispatch_project`/`cancel_workflow` Chief tool listesinde hiç yer almaz (deny bug'ından bağımsız, çünkü bağlantı hiç kurulmuyor).
- John'un salt-okunur ekosistem/durum verisine ihtiyacı olan Chief'ler için: ceo-mcp'yi Chief'e AÇMA, John bu veriyi kendi ceo-mcp'sinden çekip Chief'e PROMPT olarak ver.
- **Doğrulama:** Her Chief oturumunda ceo-mcp tool'larının `tools/list`'te OLMADIĞINI kanıtla.

### Faz 6 — Aethris ↔ John İletişimi + Telegram/Dashboard (bkz. §6 için detaylı analiz)
- Sadece John'un botu (`JOHN_BOT_TOKEN`) Telegram'a bağlanır. Chief'ler Telegram'a bağlanmaz.
- İzolasyon/instance ayrımı tamamlanıp Faz 0-5 doğrulanmadan Telegram'a BAĞLANMA (en son adım).
- Dashboard (port 5009): büyük redesign yok, Chief spawn sonuçları (rol, skill, özet, zaman) Memory Layer'a yazılır, dashboard "Board Activity" olarak okur (salt-okunur ekleme).

---

## 5. Genel Risk Notları
- **Host kaynak durumu KÖTÜ** (15GB RAM'in 9.7GB'ı dolu, 4GB swap'ın TAMAMI dolu) — bu görevden bağımsız bir sorun, ayrıca ele alınmalı (belki gereksiz süreçler/eski test session'ları temizlenmeli). Yeni bir OpenClaw instance'ı + 5-6 yeni agent tanımı EK RAM YÜKÜ değildir (agent'lar config kaydı, boştayken 0 maliyet) ama EŞZAMANLI ÇALIŞTIRMA (run) gerçek RAM tüketir (~300-400MB/aktif run) — dikkatli test edilmeli.
- **Faz sırası kritik:** A→0→1→2→3→4→5 tamam olmadan Telegram (Faz 6) BAĞLANMAZ.
- **Değişmeyen sözleşme:** `core/executives` (5003, statik 5-persona review + CFO cost_flag kapısı) ve `core/skills`'in execute API'si dokunulmadan kalır — yeni katman bunların ÖNÜNDE salt-proxy'dir.

---

## 6. YENİ ANALİZ — Aethris ↔ John İlişkisi (bu turda eklendi, Miraç'ın sorusu üzerine)

### Miraç'ın isteği
"Ki-Life-OS ile Ki-Enterprise birbirine bağlı değil, birbirinden bağımsız ama haberleşen iki ayrı sistem olsun. John'u Aethris'in altına yerleştirebilirsin — ilk aşamada tek kontağım Aethris olur, sonra istersem John'la da ayrı görüşürüm, ama Aethris John'un supervisor'ı olabilir."

Bu iki gereksinim İLK BAKIŞTA gerilimli görünüyor: "bağımsız iki sistem" ile "Aethris, John'un supervisor'ı" — supervisor kelimesi genelde AYNI hiyerarşide/süreçte üstlük ima eder. Aşağıda 3 somut senaryo analiz edildi.

### Senaryo 1 — Tam altyapı birleşmesi (REDDEDİLDİ)
John, Ki'nin MEVCUT/PAYLAŞILAN OpenClaw instance'ında Ki'nin (Aethris'in) bir subagent'ı olarak kurulur (`agents.list[main].subagents.allowAgents`'a "john" eklenir).
- **Neden reddedildi:** Bu, tam olarak §2.7-8'de bulduğumuz ve KAÇTIĞIMIZ mimariye geri dönüş demek — John yine Ki'yle AYNI süreçte/instance'da yaşar. `sessions_spawn`/`allowAgents` mekanizması güvenilir OLSA BİLE (ki öyle), bu Miraç'ın AÇIKÇA istediği "birbirinden bağımsız iki sistem" ilkesini ihlal eder — Ki-Life-OS'un instance'ı çökerse/yeniden başlarsa John da etkilenir, ikisinin kaynak/config/state'i karışır. **Ayrıca** John'un KENDİ Board'u (CTO/CFO/CMO/COO/CISO, §1) olacak — bunlar da Ki'nin subagent ağacına (`maxSpawnDepth:1` sınırı hatırlanırsa, Ki→John→Chief zaten 2 seviye, üstüne bir de Ki'nin KENDİ subagent'ları varsa depth çakışması/karmaşası olur) karışır.

### Senaryo 2 — Protokol-seviyesi supervisor, altyapı bağımsız (ÖNERİLEN)
İki ayrı OpenClaw instance'ı (Ki-Life-OS mevcut haliyle kalır, Ki-Enterprise Faz 0'da kurulan yeni instance) TAMAMEN BAĞIMSIZ süreçler olarak kalır. "Aethris, John'un supervisor'ı" ilişkisi bir **İLETİŞİM SÖZLEŞMESİ** olarak kurulur, süreç paylaşımı olarak DEĞİL:
- Miraç'ın birincil Telegram kontağı Aethris'in (Ki'nin) mevcut botu olmaya devam eder.
- Miraç Aethris'e iş/şirketle ilgili bir niyet ifade ettiğinde, Aethris bunu John'a **Telegram üzerinden bir mesaj olarak** iletir (John'un kendi botuna/ortak gruba yazarak) — TIPKI Miraç'ın daha önce onayladığı deseni ("Aethris zaten... telegram üstünden iletir zaten") — YA DA (daha güvenilir/yapısal alternatif) Aethris, `core/aethris`'in ZATEN VAR OLAN `/delegate-to-ceo` ucunu (bkz. §7, isimlendirme netleşirse) çağırarak niyeti AÇIKÇA John'un `core/ceo` katmanına iletir.
- Miraç, İSTEDİĞİ ZAMAN John'un kendi botuna DOĞRUDAN da yazabilir (John'un botu zaten ayrı, `JOHN_BOT_TOKEN`) — bu, "sonra istersem John'la ayrı görüşürüm" ihtiyacını hiçbir ek işlem gerektirmeden karşılar, çünkü iki bot zaten bağımsız.
- **Neden önerilir:** Her iki gereksinimi de (bağımsızlık + supervisor hissi) çelişkisiz karşılar. Instance'lar arası HİÇBİR paylaşılan state/config/süreç yok (gerçek bağımsızlık), ama Miraç'ın günlük deneyiminde Aethris "önce O'na gider, gerekirse John'a iletir" davranışı sağlanır (protokol/alışkanlık seviyesinde supervisor hissi).

### Senaryo 3 — Tam eşler-arası (peer), supervisor yok
İki bot da baştan eşit, Miraç ikisine de bağımsız yazar, hiçbir otomatik yönlendirme yok.
- **Neden reddedildi (kısmen):** Miraç'ın "ilk aşamada tek kontağım Aethris olsun" isteğini karşılamıyor — Miraç açıkça bir başlangıç-noktası tercihi belirtti, bunu görmezden gelmek yanlış olur.

### KARAR — ONAYLANDI (2026-07-13)
**Senaryo 2.** Açık soru §7.1 ÇÖZÜLDÜ: `core/aethris` (FastAPI, port 5008) KI Enterprise'ın kendi Phase 8 build'iydi — **SİLİNDİ ve temizlendi** (bkz. §7a). Gerçek, tek "Aethris" artık Ki-Life-OS'un OpenClaw "main" agent'ı — KI Enterprise'ın kod tabanının/org şemasının bir PARÇASI DEĞİL, tamamen ayrı, önceden var olan, bağımsız bir sistem. KI Enterprise bundan sonra Aethris'i asla "sahiplenmez", sadece §6b'deki protokolle haberleşir.

### Faz 6b — Aethris→John Köprüsü (SOMUT UYGULAMA, onaylandı)

**Kapsam sınırı:** Bu fazın KI Enterprise tarafında YAPACAK HİÇBİR ŞEYİ YOK — John zaten Faz 6'da kendi Telegram botuyla (`JOHN_BOT_TOKEN`) mesaj almaya hazır olacak. Bu faz SADECE Ki-Life-OS (Aethris'in kendi, KI Enterprise dışındaki instance'ı) tarafında, KÜÇÜK bir ekleme:

1. **Ki-Life-OS'un `main` agent workspace'ine** (muhtemelen `/root/.openclaw/workspace/` kökü — Aethris'in KENDİ instance'ı, KI Enterprise'ın DEĞİL, dikkatli ol, YANLIŞ instance'a yazma) AGENTS.md'ye şu kural eklenir (metin taslağı):
   > "Miraç şirket/iş (KI Enterprise, projeler, dispatch, bütçe onayı vb.) konusunda bir niyet belirtirse KENDİN KARAR VERME. Bunu John'a (KI Enterprise CEO'su, Telegram botu: [JOHN_BOT_TOKEN'a karşılık gelen @username, kurulumda netleşecek]) bir mesaj olarak ilet — ya doğrudan o bot'a/ortak gruba yaz, ya da Miraç'a 'Bunu John'a iletmemi ister misin?' diye sor. Kendi başına iş dispatch etmeye ya da onay vermeye ÇALIŞMA, bu senin yetki alanın değil."
2. Bu ekleme dışında Ki-Life-OS'a HİÇBİR MCP sunucusu/tool/config eklenmez — iletişim SADECE Telegram mesajlaşması seviyesinde (John kendi NLU'suyla gelen mesajı yorumlar, gerekirse netleştirici soru sorar — Faz 0-5'te zaten kurulan davranış).
3. **Doğrulama:** Miraç Aethris'e ("Ki") bir iş/şirket niyeti söyler (örn. "John'a söyle ki-chat için bir durum raporu hazırlasın") → Aethris bunu KENDİSİ YAPMAZ, John'a iletir (mesaj olarak) → John kendi NLU'suyla bunu işler (gerekirse Chief spawn eder, gerekirse netleştirici soru sorar).
4. **Rollback:** Ki-Life-OS AGENTS.md'sine eklenen birkaç satırı geri al — Aethris eski davranışına (iş konularında da kendi cevap verme) döner. KI Enterprise tarafında geri alınacak hiçbir şey yok (hiç değişiklik yapılmadı).
5. **Miraç'ın John'la doğrudan konuşması:** Ek bir işlem GEREKMEZ — John'un botu zaten ayrı (`JOHN_BOT_TOKEN`), Miraç istediği an ona doğrudan yazabilir. Aethris'in "supervisor" rolü sadece "Miraç'ın VARSAYILAN/ilk kontağı" anlamına gelir, TEK kontak değil.

---

## 7. Uygulanan Temizlik (2026-07-13, bu turda YAPILDI — açık soru artık kapalı)

**a) `core/aethris` tamamen silindi:**
- Servis durduruldu (`kill`, port 5008 artık boş) ve dizin silindi (`rm -rf /opt/ki-enterprise/core/aethris`).
- `core.env:PROJECTS` — `"aethris"` çıkarıldı (artık `["ki-business","ki-social","ki-wallet","ki-form","ki-management"]`).
- `core/dashboard/config.py` — `AETHRIS_API_URL` alanı kaldırıldı.
- `core/dashboard/main.py` — `ALL_SERVICES` dict'inden `"aethris"` girdisi kaldırıldı (health-check/panel artık var olmayan bir servisi ping'lemeye çalışmıyor).
- `core/projects/main.py` — üstteki proje listesi yorumu güncellendi (5 proje, "aethris" tarihsel not olarak açıklandı).
- `core/improvement/main.py:_known_architectural_gaps` — Aethris'e dair evidence satırı "artık tarihsel" olarak güncellendi, CEO tarafının (GET /api/v1/ceo/workflows) zaten düzeldiği, kalan tek eksiğin Dashboard olduğu netleştirildi.
- `core/organization/ORG_CHART.md` — org şeması diyagramından Aethris/core/aethris satırı çıkarıldı, yerine "Aethris artık KI Enterprise dışında, Ki-Life-OS'ta bağımsız" notu eklendi.
- **Dokunulmadı (bilerek):** `core/dashboard/main.py` ve `core/improvement/main.py` içindeki "Aethris Phase 8" tarihsel yorum satırları (K1/K2 kök-neden referansları) — bunlar gerçek bir servise işaret ETMİYOR, sadece geçmişte bulunan bir mimari örüntüyü (3 serviste tekrarlayan aynı bug) belgeleyen tarihsel notlar, silinmesine gerek yok.

**b) Hiçbir servis şu an bu değişikliklerden etkilenen bir şekilde ÇALIŞMIYORDU** (dashboard/improvement bu oturumda aktif process olarak çalışmıyordu) — bir sonraki başlatmalarında yeni config otomatik geçerli olacak, ekstra restart/migration adımı gerekmiyor.

---

## 8. AÇIK, ÇÖZÜLMEMİŞ SORULAR (implementasyona başlamadan önce Miraç'a sorulmalı)

1. ~~"Aethris" isimlendirme belirsizliği~~ — **ÇÖZÜLDÜ** (bkz. §6/§7 yukarıda).
2. Model faturalama: John için "LiteLLM/ki-cloud alias" seçildi (önceki turda onaylandı) — Chief'ler için de AYNI mı, yoksa Chief'ler (daha sık/paralel çağrılacağı için) daha ucuz bir alias mı kullanmalı?
3. Host'un dolu swap'ı (§5) bu görevi engellemez ama ayrıca ele alınmalı mı, yoksa şimdilik göz ardı mı edilsin?
4. Faz 6b'nin metnini Ki-Life-OS'un AGENTS.md'sine EKLEME işlemi — bu, KI Enterprise'ın kod tabanı DIŞINDA bir dosya (Aethris'in kendi workspace'i). Bunu kim/ne zaman yapacak netleşmeli (Miraç kendisi mi ekleyecek, yoksa aynı Haiku implementasyon turunda mı, DİKKATLİCE doğru instance'a dokunularak, yapılacak)?

---

## 9. Süreç notu
Kullanıcının talimatı: "Önce Fable 5 (araştırma/mimari), sonra Opus (planlama), onay, sonra Haiku (kodlama)." Bu dosya Fable 5 (×4 tur) + Opus (×3 tur) çıktılarının konsolidasyonudur ve KULLANICI TARAFINDAN ONAYLANDI (yukarıdaki §6/§7 hariç — bunlar bu son turda eklendi, henüz onaylanmadı). Bir sonraki adım: §7'deki açık sorular yanıtlanınca, Haiku (veya eşdeğer) ile Faz A'dan başlanarak sırayla uygulama.

---

## 10. Düzeltilmiş Uygulama Talimatları (Fable 5 bulgularına göre, Opus tarafından planlandı, 2026-07-13)

**Durum: ONAYLANDI — Haiku uygulama turu için hazır.** Bu bölüm §4'teki Faz A ve Faz 0'ı, repo'nun GERÇEK durumuyla (Fable 5 araştırma turu) doğrulanan bulgulara göre DÜZELTİR. §4 ile çeliştiği yerlerde **bu bölüm geçerlidir**. Aşağıdaki her komut/dosya-yolu gerçek dosya incelemesiyle doğrulandı.

### 10.0 — Kritik zemin gerçekleri (Haiku bunu okumadan başlama)

1. **ceo-mcp bir OpenClaw-managed MCP DEĞİL.** `openclaw mcp list` BOŞ dönüyor ("No OpenClaw-managed MCP servers configured"). ceo-mcp aslında **proje-bazlı `.mcp.json` mekanizmasıyla** tanımlı:
   - Konum: `/root/.openclaw/workspace/john/.mcp.json`
   - İçerik: `mcpServers.ceo-mcp` → `command: /opt/ki-enterprise/core/ceo-mcp/venv/bin/python3`, `args: [.../server.py]`, `env.INTERNAL_API_KEY: <düz metin anahtar>`.
   - **Sonuç:** §4'teki `openclaw mcp remove ceo-mcp` (Faz A) ve `openclaw mcp add` (Faz 0.2) komutları YANLIŞ/no-op'tur — bu komutlar `openclaw.json`'un managed-mcp bölümüne bakar, ama ceo-mcp orada değil. Gerçek işlem **`.mcp.json` dosyasını kopyalamak/silmektir**. (Not: Bu, KI Enterprise'ın kendi izole instance'ının HENÜZ kurulmamış olmasıyla tutarlı — plan zaten baştan "tamamen ayrı instance" öngörüyordu, §2.8.)
2. **John'un modeli şu an native, ama BUNUN DEĞİŞMESİ GEREKİYOR.** `openclaw.json` → `agents.list[john].model = "anthropic/claude-sonnet-4-6"` (claude-cli runtime). Repo'nun geri kalanı (`ai-gateway`/`executives`/`finance`/`workers`) **LiteLLM proxy'si + `ki-cloud` alias'ı** kullanıyor — bu YERLEŞİK desen. Karar: John/Chief'ler de LiteLLM'e taşınacak, bkz. §10.4.
3. **John'un tool erişimi `allow` ile, deny ile DEĞİL.** `agents.list[john].tools.allow = ["ceo-mcp__*"]` (openclaw.json ~satır 238). Diğer agent'larda ise **11 adet** `tools.deny: ["ceo-mcp__*"]` girdisi var (main + 10 diğer agent).
4. **Swap DOLU:** `Swap: 4.0Gi / 4.0Gi, ~324Ki boş`. Faz 4 paralel-spawn ihtiyati ZORUNLU (bkz. §10.6).
5. **Düz metin anahtar uyarısı:** `.mcp.json` ve `openclaw.json` düz metin `INTERNAL_API_KEY` / gateway token içerir. Bunlar `/root/.openclaw` altında (KI Enterprise `/opt/ki-enterprise` git reposunun DIŞINDA), dolayısıyla §10.1 commit checkpoint'i bunları git'e SOKMAZ — ama `/root/.openclaw/workspace/john/` içinde AYRI bir `.git` var; kopyalama sırasında anahtarı yanlışlıkla başka bir repoya commit'leme.
6. **LiteLLM + Vault altyapısı ÇALIŞIYOR ama TAM BAĞLI DEĞİL** — bkz. §10.4.0. Bu turda (kullanıcı onayıyla) Faz A ile BİRLİKTE ele alınacak.

### 10.1 — ADIM 0: Commit checkpoint (Faz A'dan ÖNCE, ZORUNLU)

Faz A'yı geri alınabilir kılmak için mevcut unstaged değişiklikleri commit et. Bu SADECE `/opt/ki-enterprise` reposunu kapsar (öncesinde `~/.openclaw` değişmedi).

```bash
cd /opt/ki-enterprise
git status                      # D core/aethris/*, M dashboard/improvement/... , ?? AGENTIC_ARCHITECTURE_PLAN.md
git add -A
git commit -m "checkpoint: §7 aethris temizliği + plan §10 düzeltilmiş talimatlar (Faz A öncesi)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git rev-parse HEAD              # rollback için bu hash'i NOT AL
```

Bu commit'ten sonra Faz A geri almak istenirse: `git reset --hard <bu-hash>` + §10.3'teki `.openclaw` yedeğini geri yükle.

### 10.2 — ADIM 0.5: Swap durumu log'u (host'a MÜDAHALE ETME, sadece not al)

Faz A'ya başlamadan önce host durumunu kayda geçir. **Hiçbir süreç öldürme / swap temizleme / servis restart YAPMA** (openclaw-gateway ve litellm/vault restart'ları hariç, onlar ayrıca §10.3/§10.4'te ele alınıyor) — bu görevin kapsamı dışı, ayrı bir host-sağlığı işi.

```bash
free -h | tee /tmp/claude-0/-opt-ki-enterprise/2dd3c514-a01f-42c5-8ee7-9c7bb72633c6/scratchpad/preflight-mem.log
```

Eğer swap yine ~%100 doluysa (beklenen): UYARI olarak not et ve devam et — Faz A/0/1/2/3 config-only'dir, RAM tüketmez. Gerçek risk Faz 4'te (eşzamanlı run); oraya gelince §10.6 zorunlu testi devreye girer.

### 10.3 — Faz A (DÜZELTİLMİŞ): Paylaşılan instance temizliği

Amaç: Ki'nin paylaşılan `~/.openclaw` instance'ından John + ceo-mcp'ye dair HER İZİ kaldırmak, ama ÖNCE John workspace'ini yeni instance için güvene almak.

**A.1 — Önce yedek (rollback güvencesi):**
```bash
cp /root/.openclaw/openclaw.json /root/.openclaw/openclaw.json.pre-fazA.bak
cp -a /root/.openclaw/workspace/john /root/.openclaw/workspace/john.pre-fazA.bak
```

**A.2 — John workspace'ini yeni instance state-dir'ine KOPYALA (silmeden önce).** Faz 0'da kurulacak instance'ın workspace kökü (örn. `/root/.openclaw-ki-enterprise/workspace/john`) hedeftir. `.mcp.json` (ceo-mcp tanımı) bu kopyayla birlikte TAŞINIR.

```bash
mkdir -p /root/.openclaw-ki-enterprise/workspace
cp -a /root/.openclaw/workspace/john /root/.openclaw-ki-enterprise/workspace/john
test -f /root/.openclaw-ki-enterprise/workspace/john/.mcp.json && echo "OK: .mcp.json kopyalandı"
```

**A.3 — `openclaw.json`'dan john agent girdisini + ceo-mcp deny/allow izlerini sil.** JSON düzenlemesi (elle Edit ya da doğrulanmış `jq`):
- `agents.list[]`'ten `id: "john"` nesnesini kaldır.
- Kalan 11 agent'taki `tools.deny: ["ceo-mcp__*"]` girdilerini kaldır (boş kalan `deny`/`tools` anahtarlarını da temizle, geçerli JSON bırak).
- **`openclaw mcp remove ceo-mcp` KOMUTUNU ÇALIŞTIRMA** — no-op'tur.

**A.4 — John workspace'ini paylaşılan instance'tan SİL** (yalnızca A.2 kopyası ve A.1 yedeği doğrulandıktan SONRA):
```bash
rm -rf /root/.openclaw/workspace/john
```

**A.5 — Gateway'e config'i yeniden okut:**
```bash
systemctl reload openclaw-gateway.service 2>/dev/null || systemctl restart openclaw-gateway.service
```

**A.6 — Doğrulama (hepsi geçmeli):**
```bash
grep -c "ceo-mcp" /root/.openclaw/openclaw.json        # beklenen: 0
grep -c '"id": "john"' /root/.openclaw/openclaw.json    # beklenen: 0
test ! -e /root/.openclaw/workspace/john && echo "OK: john workspace silindi"
openclaw agents list 2>&1 | grep -i john && echo "HATA: john hâlâ görünüyor" || echo "OK: john yok"
python3 -m json.tool /root/.openclaw/openclaw.json >/dev/null && echo "OK: openclaw.json geçerli JSON"
```

**Faz A rollback:** `.pre-fazA.bak` dosyalarını geri kopyala + gateway reload.

### 10.4 — Model/Alias/Vault/Billing Mimarisi (düzeltilmiş, Faz A ile BİRLİKTE uygulanacak — kullanıcı onayı)

> **Not — önceki taslağın düzeltilmesi:** Bu bölümün ilk hali "`ki-cloud` alias'ı hiçbir yerde yok, native anthropic kullan" diyordu — bu YANLIŞTI, kullanıcı düzeltti ve bash ile doğrulandı. Ayrıca kullanıcı, Vault/billing entegrasyonunun AYRI bir sonraki tura değil, BU Haiku turuna (Faz A ile birlikte) dahil edilmesini istedi — aşağıdaki sıralama (§10.4.5) buna göre GÜNCELLENDİ.

#### 10.4.0 — Doğrulanmış zemin

1. `ki-enterprise-litellm` (port 4000) ve `ki-enterprise-vault` (port 8200, healthy) container'ları ÇALIŞIYOR.
2. `infrastructure/litellm/config.yaml` içinde **`ki-cloud` adlı gerçek bir alias var**: birincil `groq/openai/gpt-oss-120b`, `litellm_settings.fallbacks: [ki-cloud: ["groq-llama-3.1-70b", "ollama-llama3.1", "groq-llama-3.1-8b"]]`. Onlarca sağlayıcı modeli tanımlı (OpenAI/Anthropic/Gemini/Mistral/Groq/OpenRouter/HuggingFace/Ollama/EdenAI/Cloudflare).
3. `ki-cloud` repo'da YERLEŞİK desen: `core/ai-gateway`, `core/executives`, `core/finance`, `core/workers` hepsi `LITELLM_API_BASE="http://localhost:4000/v1"` + `DEFAULT_*_MODEL="ki-cloud"` + `core.env:LITELLM_API_KEY` kullanıyor.
4. John'un OpenClaw tanımı şu an native `anthropic/claude-sonnet-4-6` — LiteLLM'den GEÇMİYOR, repo standardından sapmış.
5. **Vault gerçek ama BAĞLI DEĞİL:** `infrastructure/vault/init-vault.sh` secret'ları Vault'a yazıyor, ama `config.yaml` hâlâ `api_key: os.environ/OPENAI_API_KEY` gibi düz env okuyor; `docker/litellm/docker-compose.yml`'da Vault entegrasyonu yok, secret'lar düz `/opt/ki-enterprise/docker/litellm/.env`'den geliyor.
6. **Billing KAPALI:** `disable_spend_logs: true`, `disable_add_log_to_database: true`, `disable_load_cache_before_adding_spend_logs: true`, `disable_prometheus: true`. Postgres `database_url` zaten tanımlı.

#### 10.4.1 — Model mimarisi kararı: John ve Chief'ler LiteLLM proxy'sinden geçer

**Karar:** John ve 5 Chief, native `anthropic/...` yerine **LiteLLM proxy'si** (`http://localhost:4000/v1`) üzerinden çalışacak. Gerekçe: repo tutarlılığı, merkezi fallback (`ki-cloud` zinciri), merkezi billing (§10.4.4).

**OpenClaw'da yönlendirme mekanizması:** Agent tanımında (`agents.list[<id>]`) `model` (LiteLLM alias'ı), `baseUrl`/`apiBase` (`http://localhost:4000/v1`), `apiKey` (`core.env:LITELLM_API_KEY` ya da §10.4.4'teki per-agent key) alanları verilir.

> **DOĞRULANMALI:** Alan adlarının TAM biçimi (`baseUrl` vs `apiBase`, `provider: "openai-compatible"` gerekip gerekmediği) uygulama sırasında `openclaw agents add --help` / mevcut config şemasıyla doğrulanmalı, UYDURULMAMALI. Kuru testte tek bir agent kurulup LiteLLM erişim log'unda alias'ın göründüğü teyit edilmeli.

#### 10.4.2 — Rol-bazlı alias: `ki-cloud-ceo` ve `ki-cloud-chief`

`infrastructure/litellm/config.yaml`'a `ki-cloud`'un fallback desenini örnek alan **iki yeni alias** eklenir:

- **`ki-cloud-ceo`** (John): birincil **en güçlü/en yetenekli model**, ardından `ki-cloud` zinciri fallback. Gerekçe: John sistemin giriş kapısı (§2.2'deki 422 hatası hatırlanırsa), kalite > maliyet.
- **`ki-cloud-chief`** (5 Chief): birincil **daha ucuz/hızlı** (`groq/openai/gpt-oss-120b`, yani mevcut `ki-cloud`'un birincili), aynı fallback zinciri. Gerekçe: 5× paralel çağrı, maliyet/hız öncelikli.

Bu, billing raporunda John vs Board harcamasını `model` bazında ayırt edilebilir kılar. Alias'ların birincil modelleri kesinleşmeden önce (özellikle John için hangi "en güçlü model") Miraç'a teyit ettirilmeli — Haiku bunu uygularken varsayılan olarak mevcut `ki-cloud` birincilini (`groq/openai/gpt-oss-120b`) her iki alias için de birincil koyabilir, John'a farklı/daha pahalı bir model atanması AYRICA onay gerektirir.

#### 10.4.3 — Vault entegrasyonu (BU TURDA, Faz A ile birlikte — kullanıcı onayı)

Amaç: `config.yaml`'daki `api_key: os.environ/X` okumalarını Vault'tan çekilen değerlerle değiştirmek.

**Yön:** LiteLLM'in secret-manager entegrasyonu (`general_settings.key_management_system: "hashicorp_vault"` + Vault bağlantı env'leri, ör. `HCP_VAULT_ADDR`/`HCP_VAULT_TOKEN`/`HCP_VAULT_NAMESPACE` benzeri).

> **DOĞRULANMALI (versiyona bağlı):** Tam config anahtarları, env değişken adları ve `config.yaml`'da bir secret'a Vault path'inden atıfta bulunma sözdizimi, container'daki LiteLLM sürümünün resmi "Secret Managers / HashiCorp Vault" dokümanıyla teyit edilmeli — UYDURULMAMALI. `docker/litellm/docker-compose.yml`'a Vault erişimi için gerekli env/network eklentileri bu adımda yapılır (litellm ve vault zaten aynı `ki-enterprise` docker network'ünde).

**Uygulama sırası (dikkatli, geri alınabilir):**
1. Önce Vault'ta secret'ların gerçekten `vault kv get ki-enterprise/<provider>` ile okunabildiğini doğrula (mevcut root token ile 403 alındıysa önce doğru token'ı bul/`vault status`ile kontrol et — bkz. Fable bulgusu, token sorunu OLABİLİR).
2. `config.yaml`'ı DEĞİŞTİRMEDEN önce yedekle (`config.yaml.pre-vault.bak`).
3. `key_management_system` ayarını ekleyip TEK bir provider (ör. `openai`) üzerinde test et — `ki-cloud` zincirini KIRMADAN önce doğrula.
4. Çalıştığı doğrulanınca geri kalan provider'lara genişlet.
5. **Rollback:** `config.yaml.pre-vault.bak`'ı geri koy + litellm container restart — düz env okumaya anında döner (`.env` dosyası hâlâ yerinde, silinmedi).

#### 10.4.4 — Billing aktivasyonu

`config.yaml`'da: `disable_spend_logs: false`, `disable_add_log_to_database: false`, `disable_load_cache_before_adding_spend_logs: false` (opsiyonel: `disable_prometheus: false`, mevcut Prometheus/Grafana yığınıyla grafiklenebilir).

Agent-bazlı kırılım için John ve her Chief'e `/key/generate` ile **ayrı LiteLLM key'i** üretilmesi önerilir (paylaşılan tek key ile harcama sadece `model` bazında ayrışır, agent bazında değil). Postgres tablo büyümesi/RAM host kaynak kısıtı (§5) göz önünde tutularak gözlemlenmeli.

**Rollback:** flag'leri `true`'ya geri çek + container restart.

#### 10.4.5 — Sıralama (GÜNCELLENDİ — kullanıcı Vault/billing'i bu turda istedi)

Kullanıcının açık talimatı üzerine, Vault ve billing artık AYRI bir sonraki tura ERTELENMİYOR — Faz A ile aynı Haiku turunda, ama Faz A'nın kendisinden SONRA ve dikkatli/geri-alınabilir adımlarla uygulanıyor (§10.4.3'teki kademeli test sırası korunarak):

1. **ADIM 0-0.5** (§10.1-10.2): commit checkpoint + swap log.
2. **Faz A** (§10.3): paylaşılan instance temizliği — DEĞİŞMEDEN.
3. **Model routing hazırlığı:** `ki-cloud-ceo` + `ki-cloud-chief` alias'larını `config.yaml`'a ekle (§10.4.2), litellm container'ı reload/restart et, TEK bir test çağrısıyla (`curl http://localhost:4000/v1/chat/completions` ya da litellm `/model/info`) her iki alias'ın da yanıt verdiğini doğrula.
4. **Billing aktivasyonu** (§10.4.4) — düşük risk, tersine çevrilebilir, hemen yap.
5. **Vault entegrasyonu** (§10.4.3) — YÜKSEK RİSK, `config.yaml` yedeklenmeden ve tek-provider testi yapılmadan TÜM provider'lara genişletme YAPILMAZ. Bu adım başarısız olursa (Vault bağlantısı/izin sorunu vb.) 10.4.3.5'teki rollback ile ANINDA düz env'e dönülür — Faz A/model-routing'in tamamlanmış olması bundan etkilenmez.
6. Faz 0'dan (yeni izole OpenClaw instance kurulumu) itibaren John/Chief'ler `ki-cloud-ceo`/`ki-cloud-chief` ile (ve varsa Vault-destekli secret'larla) kurulur.

**Genel risk notu:** Vault adımı (5) TÜM sistemin (ai-gateway/executives/finance/workers dahil) kullandığı `ki-cloud` zincirini de etkileme potansiyeli taşır (aynı `config.yaml`). Bu yüzden 10.4.3'teki "önce tek provider, sonra genişlet" sırası ZORUNLU — atlanamaz.

### 10.5 — Faz 0.2 (DÜZELTİLMİŞ): ceo-mcp'yi yeni instance'a "add" ETME, `.mcp.json` ile taşı

§4 Faz 0 adım 2'deki `openclaw mcp add` YANLIŞ (ceo-mcp managed değil). Doğru mekanizma:

1. ceo-mcp tanımı, Faz A.2'de kopyalanan `/root/.openclaw-ki-enterprise/workspace/john/.mcp.json` içinde **zaten mevcut**. Ek "add" komutu gerekmez.
2. Doğrula: `command` yolu erişilebilir, `env.INTERNAL_API_KEY` `core/ceo`'nun beklediği anahtarla eşleşiyor, John agent'ının yeni instance'taki workspace'i `/root/.openclaw-ki-enterprise/workspace/john`'a işaret ediyor.
3. `openclaw.json` (yeni instance) → john girdisinde `tools.allow: ["ceo-mcp__*"]` KORUNUR; `model`/`baseUrl`/`apiKey` alanları §10.4.1'e göre `ki-cloud-ceo`'ya işaret eder.

### 10.6 — Faz 4 paralel-spawn testi: ZORUNLU (opsiyonel değil)

Swap'ın kanıtlı doluluğu nedeniyle §4 Faz 4'teki "önce 2 paralel ile test et" notu artık **ZORUNLU BİR ADIM**:

1. John'a ilk çok-disiplinli görevde **en fazla 2 Chief paralel** spawn olacak şekilde test et.
2. `free -h` ile spawn sırasında RAM/swap'ı izle. OOM/swap-thrash belirtisi varsa DUR, 5'e çıkma.
3. Yalnızca 2-paralel testi temiz geçerse 5-Chief paralele çık, ayrı ve gözlemlenerek.

### 10.7 — §8.4 ÇÖZÜMÜ (Faz 6b hedef dosyası — KESİN)

Faz 6b'nin AGENTS.md eklemesi kesin olarak **`/root/.openclaw/workspace/AGENTS.md`**'ye yapılır (Ki'nin/main agent'ın ana workspace'i — KI Enterprise'ın yeni izole instance'ı `/root/.openclaw-ki-enterprise/...` DEĞİL). Kullanıcı bunu tekrar vurguladı: iki instance'ın (Ki-Life-OS ve KI Enterprise) tamamen ayrı kalması kuralı burada da geçerli — Faz 6b sadece Ki-Life-OS'un KENDİ workspace'ine, KI Enterprise koduna hiçbir karşılık gelen değişiklik yapılmadan, birkaç satır ekler.

### 10.8 — Faz sırası hatırlatması

`ADIM 0 (commit) → ADIM 0.5 (swap log) → Faz A → [model routing hazırlığı → billing → Vault] (§10.4.5) → Faz 0 → Faz 1 → Faz 2 → Faz 3 → Faz 4 (§10.6 zorunlu 2-paralel testi) → Faz 5 → Faz 6 → Faz 6b (§10.7 hedef)`. Faz 6 (Telegram) A–5 doğrulanmadan BAĞLANMAZ.

---

## 11. UYGULAMA GÜNLÜĞÜ — Gerçekte Ne Yapıldı (2026-07-13, Haiku turları + Miraç'ın canlı düzeltmeleri)

**Durum: ADIM 0 → Faz A → LiteLLM/model altyapısı → Faz 0 → Faz 1 TAMAMLANDI ve DOĞRULANDI (gerçek LLM çağrılarıyla). Faz 2 uygulanıyor.** Bu bölüm §10'un TASLAK/planlanan halinden SAPAN kısımları ve gerçek karşılaşılan hataları kayda geçirir — bir sonraki turu okuyan biri (insan/ajan) buradan devam etmeli, §10'daki bazı adımlar bu bölümle ÇELİŞİRSE §11 (daha yeni, gerçekte olan) KAZANIR.

### 11.1 — Miraç'ın canlı düzeltmeleri (§10.4'ü geçersiz kılan kararlar)

1. **Vault entegrasyonu (§10.4.3) atlandı** — açık talimat: "vault kısmını geç". Secret'lar hâlâ düz `.env` dosyalarından okunuyor (`docker/litellm/.env`, `infrastructure/vault/.env` — ikincisi sadece Vault'a yazmak için var ama Vault'a hiç yazılmadı/kullanılmadı bu turda).
2. **John'un LiteLLM'de olup olmaması "önemli değil"** dendi — ama pratikte John LiteLLM'e taşındı (bkz. §11.3), çünkü native `anthropic/claude-sonnet-4-6` claude-cli/subscription auth'u yeni izole instance'ta YOKTU (aşağıda açıklanıyor) ve API-key tabanlı LiteLLM yolu ANINDA çalışan, test edilmiş bir alternatifti.
3. **Yeni API key seti sağlandı** (Cloudflare Full-Permission token + R2 S3 credentials, Google AI Studio, Ollama Cloud, Mistral, Groq, OpenRouter, HuggingFace, OpenAI, Anthropic, Eden AI). `docker/litellm/.env` ve `infrastructure/vault/.env` içine yazıldı — çoğu zaten bir önceki oturumdan oradaydı, sadece eksik `ANTHROPIC_API_KEY` (vault/.env'e) eklendi ve rotasyonu değişmiş `OLLAMA_CLOUD_API_KEY` güncellendi.
4. **"LiteLLM'deki local modellerin TAMAMI kaldırıldı"** — `local-llama3.1`, `local-llama3.2-3b`, `local-nomic-embed`, `local-llama3.2-1b` (host.docker.internal Ollama, host RAM tüketen) `infrastructure/litellm/config.yaml`'dan silindi. Ollama Cloud (`ollama-llama3.1`) cloud olduğu için KALDI.
5. **Embedding varsayılanı** (`core/ai-gateway/config.py:DEFAULT_EMBEDDING_MODEL`, `core/memory/config.py:EMBEDDING_MODEL`) `local-nomic-embed` → önce `text-embedding-3-small` denendi, **OpenAI key'in quota'sı sıfır çıktığı için** (bkz. §11.5) **`mistral-embed`'e** (1024 boyut, gerçek çağrıyla test edildi) çevrildi. `EMBEDDING_DIM: 768 → 1024`.
6. **Qdrant `ki_memory` koleksiyonu** (eski boyut 768, 1 önemsiz kayıt) Miraç'ın onayıyla SİLİNİP 1024 boyutla YENİDEN OLUŞTURULDU.
7. **Fallback zinciri isteği:** "OpenClaw'da claude-cli dahil tüm abonelik bazlı modellerle birlikte var olsun; OpenRouter free, Google Flash, Gemma gibi modellerle güçlüden güçsüze bir Main→Fallback sıralaması olsun, ücretsiz öncelikli, abonelik modeller de olabilir." Bkz. §11.4 için GERÇEKTE neyin çalıştığı.

### 11.2 — Faz A + model altyapısı: gerçek sonuç (Haiku turu 1)

Faz A (§10.3) plandaki gibi UYGULANDI ve DOĞRULANDI — commit checkpoint (`22d5de8`), John+ceo-mcp izleri paylaşılan `~/.openclaw`'dan tamamen temizlendi, yedekler alındı. `ki-cloud-ceo`/`ki-cloud-chief` alias'ları eklendi, billing flag'leri açıldı. **Bu turda Faz 0 (yeni instance) sadece "dry run" (config) seviyesinde kalmıştı** — gerçek LLM çağrısı (wet run) BAŞARISIZDI (auth store sorunu, aşağıda §11.3'te çözüldü).

### 11.3 — Faz 0: gerçek engel ve çözümü (John'un LLM çağrısı çalışana kadar 4 ayrı sorun bulundu)

Yeni izole instance'ta (`/root/.openclaw-ki-enterprise/`, profile `ki-enterprise`) John'u GERÇEKTEN çalışır hale getirmek için sırayla şu 4 sorun bulunup çözüldü — **§10'un "DOĞRULANMALI" dediği OpenClaw şema belirsizlikleri artık ÇÖZÜLDÜ, aşağıdaki gerçek yapı KULLANILMALI:**

1. **Gateway hiç başlamıyordu** — `openclaw.json`'da (yeni instance) `secrets.providers.filesecrets` bloğu TANIMLI DEĞİLDİ (Ki'nin paylaşılan instance'ında var, yenisinde unutulmuştu). Çözüm: aynı blok eklendi, `path` yeni instance'ın KENDİ `credentials/provider-secrets.json`'ına işaret edecek şekilde:
   ```json
   "secrets": { "providers": { "filesecrets": {
     "source": "file", "path": "/root/.openclaw-ki-enterprise/credentials/provider-secrets.json", "mode": "json"
   } } }
   ```
   **Not:** Bu credentials dizini (mtime incelemesiyle görüldü) muhtemelen bir önceki, bu oturumdan BAĞIMSIZ bir denemede Ki'nin `~/.openclaw/credentials/`'ından kopyalanmış — içinde Ki'nin KENDİ `telegram_bot_token`'ı gibi, John'a ait OLMAMASI gereken sırlar da var. Bu, şu an aktif bir sızıntı değil (Telegram/channel binding'i Faz 6'ya kadar yok) ama Faz 6 öncesi bu dosyanın John'a özgü sırlarla temizlenmesi/değiştirilmesi gerekir.

2. **John native `anthropic/claude-sonnet-4-6` ile "No API key found for provider anthropic" hatası veriyordu** — çünkü claude-cli/subscription auth'u PER-AGENT bir sqlite dosyasında (`agents/<id>/agent/openclaw-agent.sqlite`) tutuluyor ve bu, Ki'nin paylaşılan instance'ında John için HİÇ OLUŞMAMIŞTI (`/root/.openclaw/agents/john/` sadece `sessions/` içeriyordu, `agent/` alt dizini — yani auth store — YOKTU; sadece `main` agent'ta vardı). Yani John'un §2.6'daki "mükemmel çalıştı" testi muhtemelen Ki'nin `main` agent'ının auth'unu (aynı süreç/instance içinde) DOLAYLI kullanmıştı. İzole instance'ta bu paylaşım YOK, ve interactive `claude login` bu (headless) oturumda YAPILAMAZ. **Çözüm (Miraç'ın "LiteLLM'de kalsın önemli değil" onayıyla): John'un modeli native anthropic yerine LiteLLM proxy'sine taşındı** (bkz. §11.4 için tam mekanizma).

3. **`baseUrl`/`apiKey` alanlarının agent tanımına DOĞRUDAN eklenmesi ÇALIŞMIYOR** (önceki Haiku turu bunu "doctor" tarafından reddedildiği için denemişti). **GERÇEK/DOĞRU mekanizma bulundu:** OpenClaw, üçüncü-parti OpenAI-compatible sağlayıcıları `openclaw.json` kökünde `models.providers.<ad>` bloğuyla tanımlıyor (Ki'nin paylaşılan config'inde `groq`/`cerebras`/`cloudflare`/`deepseek`/`fireworks` için AYNI desen zaten kullanılıyordu — şema oradan kopyalandı):
   ```json
   "models": { "providers": { "litellm": {
     "baseUrl": "http://localhost:4000/v1",
     "api": "openai-completions",
     "apiKey": { "source": "file", "provider": "filesecrets", "id": "/litellm_api_key" },
     "models": [
       { "id": "ki-cloud-ceo", "name": "KI Cloud CEO (LiteLLM, groq/gpt-oss-120b + fallback)", "api": "openai-completions" },
       { "id": "ki-cloud-chief", "name": "KI Cloud Chief (LiteLLM, groq/gpt-oss-120b + fallback)", "api": "openai-completions" }
     ]
   } } }
   ```
   Ardından agent'ın `model` alanına `"litellm/ki-cloud-ceo"` (John) / `"litellm/ki-cloud-chief"` (Chief'ler) yazılır. `provider-secrets.json`'a `litellm_api_key` eklendi (değeri: `core.env:LITELLM_API_KEY`, yani LiteLLM `general_settings.master_key`).

4. **ceo-mcp tool'ları hiç yüklenmiyordu** ("No callable tools remain after resolving explicit tool allowlist") — workspace'teki proje-bazlı `.mcp.json` (Fable 5'in bulduğu mekanizma, §10.0 madde 1) bu YENİ/temiz instance'ta OTOMATİK keşfedilmiyor. **Çözüm:** `openclaw --profile ki-enterprise mcp set ceo-mcp '{"command":"...python3","args":["...server.py"],"env":{"INTERNAL_API_KEY":"..."}}'` komutuyla OpenClaw-managed MCP olarak KAYDEDİLDİ (bu, `openclaw.json`'un `mcp.servers.ceo-mcp` bloğuna yazıyor). **§10.0 madde 1'in "gerçek işlem .mcp.json dosyasını kopyalamak/silmektir" notu KISMEN DÜZELTİLMELİDİR: workspace'teki `.mcp.json` taşınması hâlâ doğru/zararsız ama YETERLİ DEĞİL — hedef instance'ta AYRICA `openclaw mcp set` ile kayıt gerekiyor.**

Bu 4 düzeltmeden sonra John GERÇEK bir LLM çağrısıyla doğrulandı: `openclaw --profile ki-enterprise agent --agent john --local -m "..."` → gerçek metin yanıtı, `stopReason=stop`, ceo-mcp tool'una erişim teyit edildi (bir ara denemede `ceo-mcp__prompts_get` çağrısı yapıp zararsızca "unknown prompt" hatası aldı, sonra doğru şekilde düz metin yanıtına döndü).

### 11.4 — Fallback zinciri: gerçekte hangi modeller ÇALIŞIYOR (gerçek çağrıyla test edildi, 2026-07-13)

İlk kurulan geniş zincir (Groq → Gemini 2.5 Flash → 2x OpenRouter free → Gemma → Groq 8B → Ollama Cloud) **John'un ilk gerçek çağrısında 51 saniye sonra tamamen BAŞARISIZ oldu** — LiteLLM, bir fallback adayı "model bulunamadı" (404, retry edilemez sınıf hata) ile başarısız olunca ZİNCİRİN GERİ KALANINI DENEMEDEN tamamen hata döndürüyor (LiteLLM'in fallback mekanizmasının gözlemlenen gerçek davranışı — hata tipi retry-edilebilir değilse zincir kesiliyor). Tek tek curl testiyle GERÇEK durum:

| Model | Durum | Detay |
|---|---|---|
| `groq-llama-3.1-70b` | ✅ ÇALIŞIYOR | |
| `groq-llama-3.1-8b` | ✅ ÇALIŞIYOR | |
| `openrouter-google-gemma-4-31b-it` | ✅ ÇALIŞIYOR | |
| `ollama-llama3.1` | ✅ ÇALIŞIYOR | (boş içerik dönebilir, düşük max_tokens + reasoning-token tüketimi yüzünden, HATA değil) |
| `gemini-1.5-flash` (→ gemini-2.5-flash) | ❌ KIRIK | Google: "models/gemini-2.5-flash is no longer available to new users" (404) |
| `gemini-2.0-flash`, `gemini-2.0-flash-lite` | ❌ KULLANILAMAZ | Bu Google AI Studio key'inin free-tier quota'sı **0** (`limit: 0`) — hesapta faturalandırma/plan sorunu var, Miraç'ın kontrol etmesi gerekir |
| `openrouter-qwen-qwen3-next-80b-a3b-instruct` | ⚠️ GEÇİCİ | Upstream'de (Venice sağlayıcı) rate-limitli (429), kalıcı kırık değil, tekrar denenebilir |
| `openrouter-meta-llama-llama-3-3-70b-instruct` | ⚠️ GEÇİCİ | Aynı upstream rate-limit sorunu |
| `text-embedding-3-*`, `gpt-4o*` (OpenAI) | ❌ KULLANILAMAZ | OpenAI key quota'sı **sıfır** (429 insufficient_quota) — Miraç'ın OpenAI hesap/bakiye kontrolü gerekir |

**Güncel, ÇALIŞAN `infrastructure/litellm/config.yaml` fallback zinciri** (`ki-cloud`/`ki-cloud-ceo`/`ki-cloud-chief` ortak, YAML anchor `&fallback_chain` ile):
```yaml
fallbacks:
  - ki-cloud: &fallback_chain
      - groq-llama-3.1-70b
      - openrouter-google-gemma-4-31b-it
      - groq-llama-3.1-8b
      - ollama-llama3.1
  - ki-cloud-ceo: *fallback_chain
  - ki-cloud-chief: *fallback_chain
```
**Not:** Gemini ve 2 OpenRouter modeli BİLEREK zincirden ÇIKARILDI (kırık/geçici-kırık oldukları için TÜM zinciri düşürüyorlardı). Google key quota'sı ve OpenAI key quota'sı düzelirse (Miraç hesap tarafında), bunlar geri eklenebilir — ama LiteLLM'in "retry-edilemez hata zinciri keser" davranışı göz önüne alınarak, zincire eklenecek her yeni model MUTLAKA tekil curl testiyle doğrulanmalı, sadece "muhtemelen çalışır" varsayımıyla eklenmemeli.

### 11.5 — Faz 1: 5 Chief agent (TAMAMLANDI, gerçek çağrıyla doğrulandı)

`openclaw.json` (yeni instance) → John'un yanına `cto`(Kai)/`cfo`(Vera)/`cmo`(Iris)/`coo`(Leo)/`ciso`(Nora) eklendi, hepsi `model: "litellm/ki-cloud-chief"`, `tools` alanı TANIMLANMADI (ceo-mcp erişimi YOK — boş `{"allow":[]}` yerine alanın TAMAMEN ATLANMASI gerektiği önceki bir denemede öğrenildi: boş allow listesi "no callable tools" hatasıyla agent'ı TAMAMEN durduruyor). Her biri için `/root/.openclaw-ki-enterprise/workspace/<id>/AGENTS.md` (kimlik + "John'un iç danışmanısın, Telegram'a yazmazsın, para onaylayamazsın" kuralı + PERSONAS.md'den karakter) oluşturuldu. TEK TEK (paralel DEĞİL) sırayla gerçek LLM çağrısıyla test edildi, hepsi karaktere uygun gerçek metin yanıtı verdi (`stopReason=stop`). `openclaw-gateway-enterprise.service` aktif/stabil.

**Kaynak durumu (2026-07-13, Faz 1 sonrası):** RAM 9.7/15 GiB, **swap ~%97 dolu** (3.9/4.0 GiB) — Faz 4'ün (5-Chief paralel spawn) ÖNCE 2-paralel testiyle başlaması kuralı (§10.6) DAHA DA KRİTİK hale geldi, atlanmamalı.

### 11.6 — Faz 2: rol-bazlı skills-mcp (TAMAMLANDI, 2026-07-13)

`/opt/ki-enterprise/core/skills-mcp/server.py` yazıldı — tek script, `OWNER_ROLE` env değerine göre `core/skills/skills_registry.py:SKILLS`'i filtreler, her skill'i bir MCP tool olarak `POST http://localhost:5007/api/v1/skills/{name}/execute`'e proxy'ler (body şeması: `{"inputs": {...}}`, `Authorization: Bearer <INTERNAL_API_KEY>`). **Önemli gerçek detay:** sistem Python'unda (`/usr/bin/python3`) `mcp` paketi YOKTU — script'i çalıştıran komut `/opt/ki-enterprise/core/finance/venv/bin/python3` olarak ayarlandı (bu venv'de `mcp`+`httpx` zaten kurulu, ödünç alındı; kendi izole venv'i YOK, ileride `core/skills-mcp/venv/` açılması daha temiz olur ama şu an çalışıyor).

5 MCP kaydı `openclaw --profile ki-enterprise mcp set skills-mcp-<rol> '{...}'` ile yapıldı (§11.3 madde 4'teki mekanizmayla aynı). Her Chief'in `tools.allow`'u SADECE kendi `skills-mcp-<rol>__*`'una kilitlendi (`{"allow": ["skills-mcp-cto__*"]}` vb.) — `tools` alanı hiç TANIMLANMAMASI gerektiği (boş `allow:[]` "no callable tools" hatası verir, §11.5) burada da uygulandı. John'un `tools.allow`'una dokunulmadı.

**Rol → skill sayısı:** CTO 6, CFO 5, CMO 8, COO 3, CISO 3 (toplam 25). Tablo `ORG_CHART.md`'deki mevcut Rol→Skill eşlemesiyle birebir örtüşüyor.

**Doğrulama:** CTO ve CFO gerçek LLM çağrısıyla test edildi (Haiku turu + ben bağımsız olarak) — ikisi de SADECE kendi skill'lerini doğru listeledi, sızıntı yok. **CMO/COO/CISO'nun canlı testi host'un swap baskısı yüzünden (bkz. §11.5 sonu, ~%97 dolu) 150 saniyede timeout aldı** — doğrudan LiteLLM çağrısı (`ki-cloud-chief`) AYNI ANDA 0.3 saniyede döndüğü için bu bir model/rate-limit sorunu DEĞİL, muhtemelen host kaynak baskısı altında agent-süreç/MCP-subprocess başlatmanın yavaşlamasıdır. Config (JSON, tools.allow, mcp servers) bağımsız olarak doğrulandı ve doğru — sadece uçtan-uca "konuşma" testi üçü için TAMAMLANAMADI. **Host swap/RAM baskısı düzeltilince bu üçü de tekrar canlı test edilmeli.**

### 11.7 — Faz 3: Skill → Sub-agent eşleştirmesi (TAMAMLANDI, dokümantasyon-only, 2026-07-13)

Plan §4 Faz 3'ün öngördüğü gibi **kod değişikliği YOK** — Faz 2 zaten var olan skill'leri OpenClaw Chief agent'larında canlı MCP tool'u yaptığı için, Faz 3 sadece bunu belgelemekten ibaretti. `ORG_CHART.md`'ye "Skill → Sub-agent eşleştirmesi (OpenClaw üzerinden canlı)" bölümü eklendi ve org şeması diyagramındaki "kurulum sürüyor" notları "canlı" olarak güncellendi.

### 11.8 — Faz 4 gerçek engeli ve mimari düzeltme (2026-07-13, KRİTİK)

**Host kaynağı sorunu değildi — OpenClaw'un subagent-spawn mekanizmasının gerçek bir sınırı bulundu.** 3 ayrı 2-paralel-spawn testi çalıştırıldı:

1. **Host/kaynak tarafı HER SEFERİNDE temiz** — swap hiçbir testte büyümedi (3.4GiB'de sabit kaldı), OOM/thrash gözlenmedi. §10.6'nın endişe ettiği host-kaynak riski gerçekleşmedi.
2. **İlk 2 model sorunu bulunup düzeltildi:** (a) `ki-cloud-ceo`'nun birincili `groq/openai/gpt-oss-120b` (reasoning modeli) tool-çağıran görevlerde boş yanıt veriyordu → John için `groq/llama-3.3-70b-versatile`'a (doğrudan/instruct model) çevrildi, ki-cloud/ki-cloud-chief'e dokunulmadı. (b) Ollama Cloud fallback'i (`ollama-llama3.1`) `gpt-oss:20b` ile gerçek "Internal Server Error" veriyordu → `gpt-oss:120b`'ye yükseltildi (model adı kataloğunda GERÇEKTEN vardı, sorun boyuttu/güvenilirlikti), artık gerçek yanıt veriyor.
3. **ASIL KÖK NEDEN (mimari, config değil):** İzole/zorlayıcı bir testle `sessions_spawn`'ın GERÇEKTEN çağrıldığı kanıtlandı (John CTO'yu başarıyla spawn etti) — ama spawn edilen Chief'in KENDİ MCP sunucusu (`skills-mcp-<rol>`) subagent çalışma bağlamında HİÇ YÜKLENMEDİ: `"No callable tools remain after resolving explicit tool allowlist (agents.cto.tools.allow: skills-mcp-cto__*; inherited tools.allow: sessions_list, sessions_spawn, sessions_yield); no registered tools matched"`. `runtime="acp"` zorlaması da aynı sonucu verdi. OpenClaw'un kaynak kodu incelendi (`subagent-spawn-plan-*.js`) — bu dosya SADECE "kim kimi spawn edebilir" izin mantığını içeriyor, MCP sunucu başlatma/bağlama mantığından HİÇ bahsetmiyor. Sonuç: per-agent MCP sunucuları (Faz 2 mimarisi) sadece bir agent KENDİ BAŞINA (`--local`/kendi top-level session'ında) çalıştırıldığında başlıyor, `sessions_spawn` ile subagent olarak başlatıldığında DEĞİL — bu OpenClaw'un bu sürümünün (2026.6.11) bilinen bir sınırı gibi görünüyor.

**KARAR (Miraç onayıyla) — mimari değişiklik, sessions_spawn/subagent yerine John'a doğrudan skill erişimi:**

- John'un `subagents.allowAgents` config'i ve `sessions_spawn`/`sessions_list`/`sessions_yield` tool izinleri KALDIRILDI (artık gerekmiyor, hatalı/işe yaramaz bir yolu tutmanın anlamı yok).
- Bunun yerine John'un `tools.allow`'una 5 Chief'in TÜM skills-mcp sunucuları eklendi: `["ceo-mcp__*", "skills-mcp-cto__*", "skills-mcp-cfo__*", "skills-mcp-cmo__*", "skills-mcp-coo__*", "skills-mcp-ciso__*"]`. John artık kendi top-level session'ında çalıştığı için (subagent DEĞİL) bu MCP sunucuları GÜVENİLİR şekilde yükleniyor.
- `workspace/john/AGENTS.md`'deki "sessions_spawn ile çağırma" bölümü "skill araçlarını DOĞRUDAN çağırma" olarak yeniden yazıldı: John artık ayrı bir Chief agent spawn etmiyor, ilgili rolün skill tool'unu KENDİSİ çağırıp o rolün karakterini (Kai/Vera/Iris/Leo/Nora) yanıtı çerçevelerken kullanıyor.
- **Gerçek çağrıyla doğrulandı:** John, "mikroservis eklemek" görevinde CTO VE CFO skill'lerini gerçekten ÇAĞIRMAYA ÇALIŞTI (log'da tool-call denemesi görüldü, önceki "no callable tools remain" hatası ARTIK YOK). Bir denemede skill'e verilen argümanlar eksik/yanlış olduğu için 422 aldı — John bunu ŞEFFAFÇA kullanıcıya bildirip kendi analiziyle devam etti (zarif hata yönetimi, çökme yok). `core/skills` REST API'sinin kendisi doğru body ile ayrıca curl'le test edildi, MÜKEMMEL çalışıyor — 422'nin sebebi modelin ara sıra tool argümanını tam dolduramaması, altyapı sorunu DEĞİL.

**Sonuç:** Faz 4'ün ASIL amacı (John'un çok-disiplinli bir görevde ilgili uzmanlık alanlarına erişip sentezleyebilmesi) ARTIK ÇALIŞIYOR — ama mekanizma plandaki gibi "5 ayrı Chief agent paralel spawn" değil, "John'un kendisinin ilgili skill tool'larını sırayla/gerektikçe çağırması" şeklinde. **Bu, plan §1'deki "Board of Chiefs paralel çalışır" vizyonundan SAPMADIR** — 5 Chief agent hâlâ VAR ve bağımsız olarak (`--local` ile) danışılabilir durumda, ama John'un OTOMATİK/günlük orkestrasyonu artık onları gerçek ayrı agent session'ları olarak spawn ETMİYOR. İleride OpenClaw bu subagent-MCP sınırını giderirse (versiyon güncellemesi/resmi çözüm), plan orijinal "paralel spawn" mimarisine geri döndürülebilir — şu an için PRAGMATİK, ÇALIŞAN bir orta yol seçildi.

**Faz 5 notu:** Bu değişiklikle Chief'lerin ceo-mcp'ye hâlâ hiç erişimi yok (değişmedi) — ama John'un ARTIK TÜM skills-mcp-* sunucularına erişimi var (öncekinden daha GENİŞ bir yetki alanı). Bu, plan §5'in "yetki sızıntısı garantisi" ilkesini İHLAL ETMİYOR (John zaten CEO, en yetkili rol) ama planın orijinal "her Chief sadece kendi rolünü görür" tasarımının bir parçası olan "John bile diğer rollerin skill'ini görmemeli" varsayımı (eğer öyle bir varsayım vardı ise) artık geçerli değil — John kasıtlı olarak TÜM rollerin skill'lerine erişebiliyor, bu onun CEO rolünün gereği.

### 11.9 — Faz 5 (resmi doğrulama), yeni entegrasyonlar, Faz 6/6b (TAMAMLANDI, 2026-07-13)

**Faz 5 — resmi doğrulama TAMAMLANDI:** Her Chief'in (`cto`/`cfo`/`cmo`/`coo`/`ciso`) `tools.allow` listesi tek tek kod/config üzerinden kontrol edildi — HİÇBİRİNDE `ceo-mcp__*` deseni YOK. Yetki sızıntısı garantisi resmi olarak doğrulandı.

**Yeni entegrasyonlar (Miraç'ın talebiyle, §11.8'deki "John'a doğrudan skill erişimi" mimarisiyle AYNI desen genişletildi):**
- **Twenty CRM** (`/opt/ki-enterprise/core/twenty-mcp/server.py`) — GraphQL API'ye (`list_people`, `list_companies`, `list_opportunities`, `search_person`, `create_note`) John+CFO+CMO erişimi var (okuma+yazma, Miraç onayı). Gerçek API key ile gerçek müşteri verisiyle test edildi.
- **ki-social yayınlama** (`/opt/ki-enterprise/core/social-mcp/server.py`) — `ki-social-backend` host'a açıldı (`127.0.0.1:8021`, sadece localhost), `generate_content`/`publish_content`/`list_accounts` tool'ları SADECE CMO+John'da. `publish_content` (gerçek Composio bağlantılı Twitter/LinkedIn/2xInstagram hesaplarına GERÇEK yayın) Miraç'ın "tam otonom" onayıyla HİÇBİR onay kapısı OLMADAN kuruldu — kod incelemesiyle doğrulandı ama test turunda GERÇEKTEN çağrılmadı (gerçek/halka açık post riski nedeniyle bilerek).
- Her iki MCP de `openclaw mcp set` ile kaydedildi, ilgili agent'ların `tools.allow`'una eklendi, gerçek çağrıyla doğrulandı.

**Faz 6 — Telegram bağlama TAMAMLANDI:**
- John'un kendi botu (`@KiJohn_bot`, `JOHN_BOT_TOKEN`) `/root/.openclaw-ki-enterprise/openclaw.json`'a `channels.telegram` olarak eklendi.
- **Gerçek bir hata bulunup düzeltildi:** `provider-secrets.json`'daki `telegram_bot_token` (§11.3 madde 1'de flag edilen "yabancı sır" sorunu) hâlâ Ki'nin KENDİ bot token'ıydı — JOHN_BOT_TOKEN'ın gerçek değeriyle DEĞİŞTİRİLDİ. Değiştirilmeden önce gateway logu bunu "bot identity change" olarak YAKALADI (kanıt: sorun gerçekti, varsayım değil).
- **İkinci gerçek çakışma bulundu:** Eski `core/telegram-bridge` custom servisi (`ki-enterprise-telegram-bridge.service`, systemd) AYNI JOHN_BOT_TOKEN'ı hâlâ dinliyordu (`getUpdates conflict` hatası) — bu, planın baştan beri John'u TAŞIMAYI amaçladığı eski mimariydi (§2.1-2.5). Servis durduruldu ve devre dışı bırakıldı (`systemctl stop/disable`). Gateway restart sonrası çakışma YOK, `@KiJohn_bot` temiz şekilde polling'e başladı.
- **Güvenlik notu (henüz yapılmadı):** `channels.telegram.allowFrom` şu an BOŞ (Ki'nin kendi deseniyle tutarlı, ama John `approve_cost`/`dispatch_project` gibi tehlikeli araçlara sahip) — Miraç ilk mesajı attığında gateway log'undan kendi Telegram user ID'sini alıp `allowFrom`'a eklemesi düşünülebilir, ŞİMDİLİK açık bırakıldı.

**Faz 6b — Aethris→John köprüsü TAMAMLANDI:** `/root/.openclaw/workspace/AGENTS.md`'ye (Ki'nin KENDİ workspace'i, KI Enterprise kod tabanı DIŞINDA) §6b'deki taslağa uygun bir bölüm eklendi — Aethris artık iş/şirket niyeti gördüğünde kendi karar vermeyip John'a (`@KiJohn_bot`) yönlendiriyor.

**WhatsApp notu (ilgisiz ama aynı turda yapıldı):** Ki'nin paylaşılan instance'ındaki KİŞİSEL WhatsApp oturumu (`openclaw channels logout --channel whatsapp`) bilinçli olarak kapatıldı — ticari numara ile yeniden eşleştirilecek, kanal config'i (allowlist vb.) SİLİNMEDİ.

### 11.10 — Kalan açık noktalar

- **Faz 4** (5-Chief GERÇEK paralel çalışma senaryosu) artık §11.8'deki YENİ mimariyle (John'un doğrudan skill erişimi) farklı bir şekilde ele alınıyor — orijinal "ayrı agent paralel spawn" senaryosu OpenClaw'un subagent-MCP sınırı yüzünden terk edildi, bkz. §11.8.
- **provider-secrets.json'daki DİĞER yabancı sırlar** (Ki'nin google/groq/cerebras/cloudflare/deepseek/fireworks key'leri) hâlâ ki-enterprise instance'ında duruyor ama HİÇBİR YERDE referans edilmiyor (John/Chief'ler sadece litellm_api_key + gateway_auth_token + telegram_bot_token kullanıyor) — aktif risk değil, ama temizlik için düşük öncelikli bir kalem.
- **Vault entegrasyonu** hâlâ YAPILMADI (bilinçli atlandı).
- **skills-mcp'nin ödünç venv'i** (`core/finance/venv`) kalıcı çözüm değil — kendi `core/skills-mcp/venv/` açılması önerilir (düşük öncelik, şu an çalışıyor).
- **Telegram `allowFrom`** boş — Miraç'ın kendi Telegram ID'siyle kısıtlanması önerilir (bkz. yukarı, Faz 6 güvenlik notu).

---

## 12. 9-Chief Genişleme Planı (2026-07-15, ONAYLANDI — henüz UYGULANMADI)

**Durum: SADECE TASARIM/PLANLAMA.** Miraç'ın talebi: mevcut 5 Chief (CTO/CFO/CMO/COO/CISO, §11'de CANLI) yapısını CPO/CRO/CDO eklenerek 9 Chief'e genişletmek, altına ~45 department + worker koymak, hepsine "free as possible" prensibiyle model ataması yapmak, hepsinin gerçekten çift-yönlü (emir/rapor/geliştirme/geri bildirim) haberleşebildiği otonom bir yapı kurmak. Bu turda kullanıcı açıkça SADECE plan+dokümantasyon istedi, kod/config implementasyonu (org tree'nin tamamı için gerçek OpenClaw agent/skill/MCP kaydı) İSTEMEDİ — o, ayrı bir onaylanacak sonraki tur (Faz 13).

**Bu turda GERÇEKTEN yapılanlar (kod/config, düşük riskli/katkısal, geri alınabilir):**
1. `core/organization/ORG_CHART.md` → "Hedef organizasyon — 9-Chief genişleme" bölümü: tam org ağacı, model-tier tablosu, iletişim mekanizması tasarımı, Chief→Department→Worker örnek tablosu.
2. `core/personas/PERSONAS.md` → CPO/Selin, CRO/Doruk, CDO/Aylin karakterleri eklendi (Kai/Vera/Iris/Leo/Nora ile aynı üslup).
3. `infrastructure/litellm/config.yaml` → (a) Cerebras sağlayıcısı (yeni araştırılan, 1M token/gün ücretsiz katman) 3 model tanımıyla eklendi ama **hiçbir fallback zincirine sokulmadı** (bu repo'nun "önce curl ile doğrula" kuralı, §11.4); (b) `ki-cloud-manager` (Department Manager tier) ve `ki-cloud-worker` (Worker tier) yeni alias'ları eklendi, ikisi de mevcut `&fallback_chain`'i paylaşıyor.

**Bu turda BİLEREK yapılmayanlar (Faz 13'ün kapsamı, ayrı onay gerektirir):**
- CPO/CRO/CDO için gerçek OpenClaw agent kaydı (`openclaw.json`'a `agents.list` girdisi, workspace/AGENTS.md dosyaları) — §11.5'teki 5 Chief'in kurulduğu YÖNTEMLE aynı şekilde yapılabilir, ama HENÜZ YAPILMADI.
- ~45 department/worker için `core/skills/skills_registry.py:owner_role` genişlemesi ve karşılık gelen `skills-mcp-<birim>` sunucu kayıtları — mevcut 5 rol (cto/cfo/cmo/coo/ciso) + toplam 25 skill deseninin devasa bir genişlemesi, ayrı bir mühendislik turu gerektirir.
- `CEREBRAS_API_KEY`'in `docker/litellm/.env`'e eklenmesi ve gerçek curl testiyle doğrulanması — key kullanıcıdan sağlanmadı.
- Memory Layer'daki `report:{birim_id}` / `blocker:{birim_id}` scope şemasının (§ORG_CHART.md "İletişim mekanizması" bölümü) gerçek kod olarak (`core/memory` şeması, skill `inputs`/`outputs` genişlemesi) yazılması.

**Mimari ilke (kanıta dayalı, aspirasyonel DEĞİL):** 9-Chief/45-Department/Worker hiyerarşisinin iletişim tasarımı, §11.8'de GERÇEKTEN kanıtlanmış kısıtı (OpenClaw `sessions_spawn`'ın spawn edilen agent'ın kendi MCP sunucusunu yüklememesi) miras alır — yani "her seviye alt seviyeyi bir subagent olarak spawn eder" klasik model DEĞİL, "üst seviyenin agent'ı alt seviyenin skill-tool'unu doğrudan çağırır" (John'un bugün CTO/CFO skill'lerini doğrudan çağırdığı, §11.8'de kurulan) deseni ölçeklenir. Bu, planın "otonom çift-yönlü haberleşme" hedefini OpenClaw'un bilinen sınırlarıyla ÇELİŞMEDEN karşılamanın tek kanıtlanmış yoludur.

**Sıradaki adım (kullanıcı onayı gerekirse):** Faz 13 — CPO/CRO/CDO'nun gerçek OpenClaw agent'ı olarak kurulması (Faz 1/§11.5 ile birebir aynı yöntem) + ilk birkaç kritik department (örn. Engineering/CTO altında, Sales/CRO altında) için gerçek skill/MCP kaydı, tam ~45 birim yerine küçük, doğrulanabilir bir alt-kümeyle başlanması önerilir (mevcut projenin her zaman izlediği "önce dry-run, sonra wet-run, sonra genişlet" disiplini, §10.6/§11.4/§11.8).

### 12.1 — Faz 13 (3 Chief alt-kümesi): TAMAMLANDI, gerçek çağrıyla doğrulandı (2026-07-15)

Kullanıcı onayıyla Faz 13'ün en dar kapsamı (SADECE CPO/CRO/CDO, department/worker katmanına HENÜZ dokunulmadı) canlı `/root/.openclaw-ki-enterprise/` instance'ında uygulandı.

**Yapılanlar:**
1. `openclaw.json` yedeklendi (`openclaw.json.pre-9chief.bak`).
2. `workspace/cpo/AGENTS.md`, `workspace/cro/AGENTS.md`, `workspace/cdo/AGENTS.md` oluşturuldu — Faz 1/§11.5'teki CTO şablonuyla birebir aynı yapı (Kimlik/Temel Kurallar/Kişilik/Bağlantılı Departmanlar), `PERSONAS.md`'deki Selin/Doruk/Aylin karakterleri kullanıldı.
3. `agents.list`'e 3 yeni girdi eklendi (`id: cpo/cro/cdo`, `model: litellm/ki-cloud-chief`), gateway restart edildi (`reload` desteklenmediği görüldü, `restart` kullanıldı).

**GERÇEKTEN BULUNAN VE DÜZELTİLEN kritik güvenlik hatası (bu turda, canlı testte):** İlk denemede 3 yeni agent'a `tools` alanı HİÇ TANIMLANMADI (§11.5'in "tools alanı hiç tanımlanmaması gerektiği" notu YANLIŞ YORUMLANDI — o not, CTO/CFO gibi ZATEN bir skills-mcp'ye sahip agent'lar için "boş `allow:[]` değil, dolu bir allow listesi ver" anlamındaydı, "tools alanını tamamen atla" anlamında DEĞİLDİ). Gerçek `tools/list` çağrısıyla CANLI olarak kanıtlandı: tools alanı atlanınca CPO, **`ceo-mcp__approve_cost`/`ceo-mcp__dispatch_project`/`ceo-mcp__cancel_workflow` dahil TÜM Chief'lerin skills-mcp'sine VE twenty-mcp/social-mcp'ye** erişebiliyordu — Faz 5'in "yetki sızıntısı garantisi" ilkesinin doğrudan ihlali. **Düzeltme:** `tools.allow: ["memory_get", "memory_search", "web_search"]` (salt-okunur, dosya/exec/MCP erişimi yok) — bu 3 agent için henüz kendi skills-mcp'leri olmadığından en dar, zararsız allowlist. Düzeltme sonrası `tools/list` çağrısı log'unda `ceo-mcp__*` ve diğer `skills-mcp-*__*`'nin AÇIKÇA "tool policy removed" listesinde göründüğü (yani filtrelendiği) doğrulandı.

**Ayrıca kanıtlanan (ters yönde) sınır:** `tools.allow`'a HİÇBİR gerçek tool eşleşmeyen bir desen (`none-such-namespace__*`) verildiğinde agent "No callable tools remain after resolving explicit tool allowlist" hatasıyla TAMAMEN çöküyor (§11.5'teki bulgunun bu turda ikinci kez, farklı bir agent'ta doğrulanması) — yani bir Chief'in "sadece sohbet edebilsin, hiçbir tool'a dokunmasın" şeklinde bir izolasyon YAPILAMIYOR, en az bir gerçek (ve güvenli) tool'a izin vermek ZORUNLU.

**Canlı LLM testi:** Güvenlik düzeltmesinden ÖNCE (geniş yetkiyle) 3 agent de gerçek metin yanıtı üretti — CPO/Selin ve CRO/Doruk karakterine uygun Türkçe tanıtım cümleleri döndürdü (`stopReason=stop`), CDO/Aylin daha jenerik ama gerçek bir yanıt verdi. Güvenlik düzeltmesinden SONRA yapılan tekrar testlerde `groq/openai/gpt-oss-120b` (ki-cloud-chief'in birincili) paylaşımlı rpm=25 limitine yakın art arda çağrı yüzünden yavaşladı/timeout verdi (86s+ sonra abort) — bu, §11.4'te zaten belgelenmiş bir model-tıkanıklığı davranışı, YENİ bir config hatası değil; canlı John/Telegram'ı etkilememek için ek tekrar testi YAPILMADI.

**Bilerek yapılmayanlar (değişmedi):** CPO/CRO/CDO'nun kendi skills-mcp sunucusu yok (department/worker katmanı hâlâ Faz 13'ün kapsamı dışında), John'un `tools.allow`'una bu 3 yeni Chief eklenmedi (John henüz onları çağırmıyor, çünkü çağıracağı bir skill-tool yok).

**Rollback:** `cp openclaw.json.pre-9chief.bak openclaw.json && systemctl restart openclaw-gateway-enterprise.service` + `rm -rf workspace/{cpo,cro,cdo}`.

---

## 13. Faz 14 — Metin + Görsel Worker Katmanı: ANALİZ + PLAN (ONAY BEKLİYOR, kod YAZILMADI)

Kullanıcının süreç talimatı: "kurulumdan önce Fable 5 analiz, Opus plan, onay, sonra Haiku ile kodlama." Bu bölüm o sırayı izler — aşağıdaki HİÇBİR ADIM henüz uygulanmadı (tek istisna: §13.1'deki iki küçük/güvenli/geri-alınabilir config denemesi, analiz için gerekliydi).

### 13.1 — Analiz bulguları (gerçek kod/canlı test, varsayım değil)

1. **Mevcut Department/Worker mimarisi OpenClaw agent DEĞİL.** `core/departments` (5004) ve `core/workers` (5005), Chief'lerden tamamen ayrı bir sistem: NATS `task.>` subject'ini dinleyen FastAPI servisleri, her worker bir Python dict'teki (`WORKER_PERSONAS`) sabit persona + AI Gateway'e (LiteLLM) düz bir `/api/chat` çağrısı. Sub-agent/tool-calling YOK, sadece tek-seferlik metin üretimi.
2. **Kritik yapısal kısıt:** `WORKFLOW_TO_DEPARTMENT` (core.env) sadece 6 Temporal workflow adını 6 departmana eşliyor (development/marketing/research/support/+2 fallback). Yeni departman EKLEMEK bu eşlemeyi otomatik GENİŞLETMEZ — yeni bir departman, ya mevcut 6 workflow'dan birine eşlenir (o zaman gerçek trafik alır) ya da hiçbirine (mevcut design/security/video/finance/operations ile AYNI durum: tanımlı ama hiç iş almıyor). Bu, ~37 yeni departmanın BÜYÜK ÇOĞUNLUĞUNUN (yeni Temporal workflow türleri eklenmeden) sadece "hazır ama boş" kalacağı anlamına gelir — dürüstçe böyle işaretlenmeli, "hepsi çalışıyor" denemez.
3. **Görsel worker denemesi (cf-image-gen):** `infrastructure/litellm/config.yaml`'a Cloudflare Workers AI'ın stable-diffusion modeli eklendi, `general_settings.allowed_routes`'a `/v1/images/generations` eklendi, LiteLLM container restart edildi. **Doğrulanan olumlu yan bulgu:** `allowed_routes` LiteLLM'in Enterprise-only bir özelliği olmasına rağmen (log: "You must be a LiteLLM Enterprise user"), temel route-allowlist filtresi Community sürümde de GERÇEKTEN çalışıyor (route eklenmeden önce 403, eklenince rota açıldı) — yani bu ayar gelecekte de güvenle kullanılabilir. **Olumsuz bulgu:** `POST /v1/images/generations` çağrısı `HTTP 200` dönüyor ama `data: []` (boş) — Cloudflare Workers AI'ın görsel modeli LiteLLM'in bu sürümünde GERÇEK bir görsel üretmiyor/dönmüyor. Kök neden netleşmedi (model adı uyuşmazlığı / response-şeması adaptasyon eksikliği / provider desteği yarım olabilir) — ek araştırma gerekiyor, **görsel ÜRETİM şimdilik çalışmıyor**.
4. **Görsel ANALİZ (üretim değil, inceleme) farklı bir yol kullanabilir:** OpenClaw'ın Chief'lerde zaten gördüğümüz yerleşik `browser` ve `canvas` tool'ları var (§12.1'deki `tools/list` çıktısında görüldü) — bunlar ekstra bir görsel-üretim modeli GEREKTİRMEDEN rakip site/sosyal medya sayfası ekran görüntüsü alıp inceleme yapabilir. Bu, "görsel üretim" (henüz çalışmıyor) ile "görsel inceleme" (muhtemelen çalışır, ama HENÜZ test edilmedi) arasında net bir ayrım gerektirir.
5. **Kaynak durumu:** Bugünkü CPO/CRO/CDO testleri sırasında `groq/openai/gpt-oss-120b` (ki-cloud-chief) paylaşımlı rpm=25 limitine yakın art arda çağrı yüzünden yavaşladı (60-90s+ gecikme/timeout). Yeni worker'lar eklenirse AYNI paylaşımlı limite eklenecekler — kademeli/seyrek test ZORUNLU.

### 13.2 — Plan (fazlı, kullanıcının onayına sunulan)

**Faz 14a — Metin-worker genişletmesi (düşük risk, OpenClaw'a/Telegram'a DOKUNMAZ):**
- `core.env`'e yeni `DEPARTMENT_TO_CHIEF` JSON registry'si (her departman → hangi Chief'e bağlı, ORG_CHART.md tablosuyla birebir).
- `core/departments/main.py:DEPARTMENTS` listesi ~46 birime genişletilir (mevcut 9 + yeni ~37).
- `core/workers/main.py:WORKER_PERSONAS`'a yeni departmanlar için persona eklenir (Türkçe isim + system_prompt, mevcut Deniz/Ada/Emre/... üslubunda) — SADECE metin-üreten (kod/analiz/rakam) birimler için.
- `PERSONAS.md` senkronize edilir.
- **Dürüst not (kodun içine de yazılacak):** Yeni departmanların çoğu `WORKFLOW_TO_DEPARTMENT`'e eklenmediği sürece gerçek görev ALMAYACAK — bu, mevcut sistemin zaten belgelenmiş bilinen sınırının bir genişlemesi, yeni bir sorun değil.
- Doğrulama: `core/departments`+`core/workers` restart edilir, `/api/v1/departments` ve `/api/v1/workers` uçları gerçek `curl` ile kontrol edilir (yeni departmanların listede göründüğü, health'in bozulmadığı).

**Faz 14b — Görsel/işitsel worker'lar (orta risk, kademeli, OpenClaw'a YENİ agent ekler):**
- Pilot 1: CMO altında `cmo-visual-analyst` — sadece `tools.allow: ["browser", "memory_get", "memory_search"]` (görsel ÜRETİM yok, sadece rakip site/sosyal medya sayfası inceleme). CPO/CRO/CDO ile AYNI güvenli kurulum yöntemi (workspace+AGENTS.md+agents.list, dar allowlist).
- Görsel ÜRETİM (CPO/UX-UI mockup, CMO/Brand görseli) **Faz 14b'ye DAHİL EDİLMEZ** — cf-image-gen çalışmadığı için önce ayrı bir araştırma turu gerekir (alternatif: Cloudflare'i LiteLLM'i bypass edip doğrudan REST ile çağırmak, ya da anahtarsız ücretsiz bir görsel API'si — ör. pollinations.ai — araştırmak). Bu, Faz 14b'nin AÇIKÇA ertelenen bir alt-parçası olarak işaretlenir (Faz 14c).
- Her yeni agent TEK TEK, aralıklı (rate-limit'e dikkat ederek) `--local` ile gerçek çağrıyla doğrulanır.

**Faz 14c — Görsel ÜRETİM araştırması (ayrı, henüz planlanmadı):** cf-image-gen'in neden boş döndüğü araştırılır VEYA alternatif ücretsiz sağlayıcı bulunur, gerçek bir görsel üretilene kadar CPO/UX-ui ve CMO/Brand'in "görsel üretim" ihtiyacı AÇIK bir sınırlama olarak kalır.

### 13.3 — Onay bekleyen soru
Kullanıcıya: Faz 14a (metin-worker genişletmesi) ve Faz 14b'nin pilot kısmı (sadece `cmo-visual-analyst`, görsel üretim OLMADAN) bu turda kodlansın mı, yoksa sadece 14a mı, yoksa başka bir sıra mı istiyor?

**Kullanıcı onayı (2026-07-15):** "14a ve b devam" + KRİTİK ek talep: "sürekli workflow yazmak zorunda kalmayız" şekilde bir mimari — mevcut 6 Temporal workflow'unun her yeni departman için elle çoğaltılması yerine daha genel bir çözüm istendi, "acımasızca değerlendirip" doğru kararı uygulamam istendi. Bkz. §14.

---

## 14. Faz 14 — UYGULAMA SONUÇLARI (2026-07-15, TAMAMLANDI, gerçek Temporal/LLM çağrılarıyla doğrulandı)

### 14.0 — Mimari karar: Temporal Dynamic Workflow (kullanıcının "sürekli workflow yazmak istemiyoruz" talebine karşılık, acımasız değerlendirme)

**Bulgu:** `core/workflow/workflows.py`'deki 6 workflow class'ı (`new_project`, `feature_request`, `marketing_campaign`, `customer_support`, `research_request`, `deployment`) **BİREBİR AYNI KODU** (`_run()`'ı saran 5 satırlık kabuklar) taşıyor, aralarında SIFIR mantık farkı var. Bunu 40+ class'a çoğaltmak (her yeni departman için) saf kopyala-yapıştır olurdu — "acımasız" değerlendirme netti: bu YANLIŞ yaklaşım.

**Karar:** Temporal Python SDK'nın (`temporalio==1.30.0`, kurulu sürüm doğrulandı) **dynamic workflow** özelliği (`@workflow.defn(dynamic=True)`) kullanıldı — TEK bir `GenericTaskWorkflow` class'ı, ÖNCEDEN TANIMLANMAMIŞ herhangi bir workflow adını yakalar (`workflow.info().workflow_type`'tan okur). Yeni bir departman/kategori eklemek artık `core/workflow/workflows.py`'a HİÇ DOKUNMADAN sadece bir isim eklemek demektir (`WORKFLOW_NAMES`/`VALID_WORKFLOWS`/`WORKFLOW_TO_DEPARTMENT` — üçü de artık salt veri, Temporal kaydı değil).

**Karşılaşılan ve düzeltilen gerçek hata:** İlk denemede `converter.from_payload(args[0], str)` `'RawValue' object has no attribute 'metadata'` hatasıyla çöktü — dynamic workflow'un `run()` metodu `Sequence[RawValue]` alır, her `RawValue`'nun gerçek `Payload`'ı `.payload` alt-alanında (`args[0].payload`). Düzeltildi, canlı Temporal testiyle doğrulandı.

**Doğrulama (3 ayrı gerçek Temporal çalıştırması, hepsi başarılı):**
1. **Regresyon:** `research_request` (eski isim) → `plan_with_ai` aktivitesi tamamlandı, Executive Board onayı geçti, mevcut davranış (onay bekleme durumu) AYNEN korundu.
2. **Kanıt (CLI):** `engineering_test_never_seen_before` (kodda hiçbir yerde tanımlı olmayan bir isim) → Temporal kabul etti, iki aktivite de (`plan_with_ai`, `executive_review`) başarıyla tamamlandı, AYNI akış.
3. **Kanıt (gerçek CEO REST API + Worker Pool, uçtan uca):** `POST /api/v1/ceo/dispatch {"workflow":"data_science",...}` → Temporal workflow `COMPLETED`, `task.data_science` event'i NATS'a yayınlandı, **Worker Pool (core/workers, port 5005) bunu GERÇEKTEN işledi** — yeni "Baran" (data_scientist) personası gerçek bir LLM çağrısıyla somut, kullanıma hazır bir teslimat (GA4 tabanlı haftalık aktivite metrik planı) üretti. `GET /api/v1/workers/data_science/deliverables` ile doğrulandı.

**Yan bulgu (ayrı, önemli, benden bağımsız bir üretim hatası):** `ki-enterprise-ceo.service` (core/ceo REST, port 5000) incelemede **44000+ kez restart olmuş crash-loop** halinde bulundu — kök neden: Jul 13'ten kalma, systemd dışı bir zombi süreç (PID 3083857) port 5000'i işgal ediyordu, gerçek servis "address already in use" ile sürekli çöküyordu (log dosyası 214 bin satıra ulaşmıştı). Kullanıcı onayıyla zombi süreç sonlandırıldı, systemd servisi temiz şekilde ayağa kalktı (`/health` → 200 OK). Bu proje tarihinde defalarca bulunan "tek instance, zombi süreç öldür" dersinin BİR KEZ DAHA doğrulanmış hali.

### 14.1 — Faz 14a: Metin-worker genişletmesi (TAMAMLANDI, 38 departman)

- `core/workers/main.py:WORKER_PERSONAS` → 8'den **38 personaya** çıkarıldı (30 yeni: Ege/Defne/Kerem/Yağmur/Barış/Ceyda/Onur/Gizem/Tolga/Sena/Kaan/Nil/Umut/Pelin/Cem/Ebru/Alper/Deren/Serkan/Buse/Volkan/Melis/Arda/Naz/Taylan/Ipek/Baran/Selen/Metehan/Ceren).
- `core/departments/main.py:DEPARTMENTS` → 9'dan **38'e** çıkarıldı.
- `core.env` → `WORKFLOW_TO_DEPARTMENT` (6 eski + 34 yeni identity-mapping = 40), yeni `DEPARTMENT_TO_CHIEF` registry'si (38 departman → 9 Chief, salt bilgilendirici), `ACTIVE_DEPARTMENTS` (38'e çıkarıldı — artık HEPSİ gerçek trafik alabilir, eski "5 departman hiçbir zaman iş almıyor" kısıtı ORTADAN KALKTI).
- `core/workflow/workflows.py:WORKFLOW_NAMES` ve `core/ceo/main.py:VALID_WORKFLOWS` → 40 kayıtla birebir senkronize edildi (Python `set()` karşılaştırmasıyla doğrulandı).
- **Bilerek dışarıda bırakılan:** `core/departments` servisinin (port 5004) hiçbir zaman bir systemd unit'i olmadığı (Phase 4'ten beri, benden bağımsız bir eksiklik) keşfedildi — kod syntax/import olarak doğrulandı ama servis canlı test edilemedi (gerçek/kalıcı bir süreç olarak hiç deploy edilmemiş). Bu ayrı, düşük öncelikli bir bulgu olarak not edildi.
- **Bilerek dışarıda bırakılan (görsel/işitsel):** design/UX-UI, brand, video departmanlarının metin-persona'ları (Mert/Ebru/Elif) kaldı ama GERÇEK görsel üretim/inceleme YAPMAZLAR — bu Faz 14b/14c'nin kapsamı.

### 14.2 — Faz 14b: Görsel-analiz pilotu (TAMAMLANDI, sadece inceleme — üretim değil)

- `cmo-visual-analyst` — yeni OpenClaw sub-agent, `/root/.openclaw-ki-enterprise/workspace/cmo-visual-analyst/AGENTS.md`, model `ki-cloud-chief`, `tools.allow: ["browser","memory_get","memory_search"]` (CPO/CRO/CDO'nunkiyle AYNI güvenli/dar allowlist deseni).
- **Doğrulandı:** Gerçek LLM çağrısıyla kendini doğru tanıttı, `tool policy removed` log'unda `ceo-mcp__*` ve diğer TÜM `skills-mcp-*__*` açıkça filtrelendiği görüldü — yetki sızıntısı YOK.
- **Gerçek bir web sayfası taraması (browser tool'unun fiilen çalıştığı) bu turda TEST EDİLMEDİ** — sadece tool erişiminin doğru kısıtlandığı doğrulandı, host kaynak/rate-limit baskısı nedeniyle ek canlı tarama testi ertelendi.
- **Görsel ÜRETİM (CPO/UX-UI mockup, CMO/Brand görseli) HALA ÇALIŞMIYOR** (§13.1 madde 3, cf-image-gen boş `data:[]` döndürüyor) — Faz 14c olarak açık kalmaya devam ediyor.

### 14.3 — Kalan açık noktalar
- `core/departments` servisi hiç deploy edilmemiş (systemd unit yok) — ayrı, düşük öncelikli bir konu.
- Görsel ÜRETİM (image generation) çözülmedi — Faz 14c, ayrı araştırma gerektiriyor.
- `cmo-visual-analyst`'in gerçek `browser` taraması canlı test edilmedi (sadece tool-access izolasyonu doğrulandı).
- Diğer 37 departmandan sadece 2'si (`sales`, `data_science`) gerçek uçtan uca test edildi — kalan 35'i AYNI koddan (aynı `WORKER_PERSONAS`/`WORKFLOW_TO_DEPARTMENT` deseni) geçtiği için yapısal olarak aynı garantiyi taşır, ama her biri TEK TEK canlı test edilmedi (host/rate-limit kaynak tasarrufu için bilinçli tercih).

---

## 16. Faz 15 — 9 Chief'in tamamı için gerçek skill/persona derinleştirmesi (2026-07-16, TAMAMLANDI)

Kullanıcının talebi: CEO/CFO/CMO hariç TÜM Chief'lerin (CTO/COO/CISO/CPO/CRO/CDO) hem skill setini hem karakterini "dünya klasında" derinleştirmek — Fable5(araştırma, Workflow ile paralel)→Opus(plan/onay)→Haiku(kod) sırasıyla.

### 16.1 — Skill araştırması ve kodlama (TAMAMLANDI)

İki ayrı Workflow turu (paralel, 3'er rol) ile 30 yeni skill araştırıldı — hepsi gerçek, yayınlanmış framework'lere dayanır, hiçbiri uydurma değil:
- **CPO (5):** RICE (Intercom), Jobs-to-be-Done (Christensen/Ulwick), Kano Model, North Star (Amplitude), Opportunity Solution Tree (Teresa Torres).
- **CRO (5):** MEDDPICC, Challenger Sale (Dixon&Adamson/CEB), Bowtie Model (Winning by Design), SPICED (Winning by Design), Sandler Pain Funnel.
- **CDO (5):** DAMA-DMBOK, DataOps Manifesto, CRISP-DM, Data Mesh (Dehghani), Kimball Bus Matrix.
- **CTO (+5, mevcut 6'ya ek):** ADR (Nygard), C4 Model (Simon Brown), Team Topologies (Skelton&Pais), DORA/Accelerate (Forsgren/Humble/Kim), Wardley Mapping.
- **COO (+5, mevcut 3'e ek):** EOS/Traction (Wickman), Theory of Constraints (Goldratt), RAPID (Bain), DMAIC (Lean Six Sigma), Hoshin Kanri.
- **CISO (+5, mevcut 3'e ek):** NIST CSF 2.0, ISO/IEC 27001:2022, FAIR (Freund&Jones), Zero Trust NIST SP 800-207, SSDF NIST SP 800-218.

Kullanıcı onayıyla tüm 30 skill `core/skills/skills_registry.py`'a eklendi (toplam 43→**58 skill**), mevcut şemayla (`owner_role`/`source`/`tools:["ai-gateway"]`/`inputs`/`outputs`/`workflow`) birebir tutarlı. `core/skills` servisi restart edildi, `/health` `skills_count:58` ile doğrulandı.

### 16.2 — Persona derinleştirmesi (TAMAMLANDI)

Ayrı bir Workflow turuyla (6 rol paralel) CTO/COO/CISO/CPO/CRO/CDO'nun karakterleri, CEO John'un derinliğiyle tutarlı 5-boyutlu (temel öncül/bilişsel tarz/kurumsal kültür/iç siyaset/operasyonel taraf) formatta yeniden yazıldı — her biri gerçek, isimli kaynaklara dayanır (Fowler/Vogels/Hohpe/Fournier/Larson — CTO; Bennett&Miles/Andy Grove — COO; Kindervag/NIST/FAIR/Schneier/Ellis — CISO; Cagan/Torres/Perri/Christensen/Doshi — CPO; Ross/MEDDPICC/Challenger/Jordan/Roberge — CRO; DAMA-DMBOK/Dehghani/Seiner/Redman/Bean — CDO). `PERSONAS.md` (tek doğruluk kaynağı) güncellendi, CFO/CMO/CEO'ya (kullanıcı talebiyle) dokunulmadı. `core/executives/main.py:REVIEW_SYSTEM_PROMPT`'un CTO/COO/CISO bölümleri de (kısa/JSON-uyumlu özet halinde) güncellendi.

### 16.3 — MCP kaydı ve bağlama (TAMAMLANDI)

- `skills-mcp-cpo`, `skills-mcp-cro`, `skills-mcp-cdo` yeni MCP sunucuları kaydedildi (mevcut `skills-mcp-cto` ile AYNI script, farklı `OWNER_ROLE`).
- Her yeni Chief'in `tools.allow`'una kendi skill-mcp'si eklendi (`memory_get`/`memory_search`/`web_search` korunarak).
- **İzolasyon canlı doğrulandı:** CPO'nun `tools/list` çağrısında `ceo-mcp__*`, `image-mcp__*`, diğer TÜM `skills-mcp-*__*` (cfo/cmo/ciso/cdo/cto/coo/cro) açıkça "tool policy removed" listesinde filtrelendiği görüldü — sızıntı yok.
- **6 OpenClaw workspace AGENTS.md dosyası** (cto/coo/ciso/cpo/cro/cdo) yeni derinleştirilmiş persona + güncel skill listesiyle güncellendi.
- Model-seviyesi tam yanıt testi §15.3'teki AYNI OpenClaw CLI `--local` güvenilirlik sorununa takıldı (config/izolasyon doğru, model çağrısı flaky) — ayrı, önceden belgelenmiş, bu turda tekrar kazılmayan bir sorun.

### 16.4 — Kapsam dışı bırakılan (bilerek)
- Departman/worker (38 birim) seviyesinde skill/MCP derinleştirmesi bu turun kapsamında DEĞİL — sadece 9 Chief seviyesi ele alındı, kullanıcı talebiyle tutarlı.
- CFO/CMO/CEO skill/persona'sına dokunulmadı (kullanıcı açıkça "bunlar halloldu" dedi).

---

## 17. Dashboard'a gerçek "Görev Gönder" formu (2026-07-16, TAMAMLANDI)

Kullanıcının "worker'lar hazır görev alabiliyor olmalı" talebi üzerine — sistem 40 workflow/departmana dispatch KABUL EDİYORDU ama bunu tetiklemenin tek yolu `curl`/API'ydi, dashboard'da hiçbir UI yoktu. Eklendi:

- `core/dashboard/main.py`: `POST /api/v1/dashboard/dispatch` — `core/ceo`'nun zaten var olan `/api/v1/ceo/dispatch`'ine proxy yapar, `Idempotency-Key` üretir. `GET /api/v1/dashboard/workflows` — 40 dispatch edilebilir isim listesini döner (dropdown için).
- **Kasıtlı güvenlik ayrımı:** Mevcut `verify_api_key` (GET uçları) hem `INTERNAL_API_KEY` hem `DASHBOARD_UI_TOKEN`'ı kabul eder — ama kodun kendi docstring'i "UI token sızarsa sadece salt-okunur veri okunur, dispatch gibi yazma uçlarına ERİŞEMEZ" diye AÇIKÇA garanti veriyordu. Bu garantiyi BOZMAMAK için yeni `verify_master_key` dependency'si YAZILDI — SADECE tam `INTERNAL_API_KEY` kabul eder, `DASHBOARD_UI_TOKEN` reddedilir. UI'da master key sayfaya GÖMÜLMEZ, kullanıcı her dispatch'te elle bir password-input'a girer.
- **Canlı doğrulama:** UI token ile dispatch denemesi `401` ile reddedildi (güvenlik garantisi korunuyor), tam master key ile GERÇEK bir dispatch (`bi` departmanına) başarıyla yapıldı (`workflow_id` döndü, Temporal'da doğrulanıp temizlendi).
- `static_ui.py`: Dashboard'un en üstüne tam-genişlik bir "Görev Gönder" kartı eklendi — departman dropdown'u (40 seçenek), proje/prompt alanları, master-key password input'u, gönder butonu, sonuç alanı.
- Container yeniden build edilip devreye alındı, NPM üzerinden (container-to-container) test edildi.

---

## 15. Faz 14 devamı — core/departments deploy, Gemini/OpenAI araştırması, browser-tool kök neden düzeltmesi, image-mcp (2026-07-15/16)

### 15.1 — core/departments artık kalıcı servis (TAMAMLANDI)

`core/departments` (port 5004) Phase 4'ten beri HİÇ systemd unit'i yokmuş (benden bağımsız, keşfedilen bir eksiklik) — `ki-enterprise-departments.service` oluşturuldu, `enable --now` ile etkinleştirildi, `/health` ve `/api/v1/departments` (38 departman) gerçek curl ile doğrulandı. Ayrıca `governance` departmanına gerçek dispatch yapılıp department-manager'ın (worker'dan BAĞIMSIZ, aynı NATS stream'i paralel dinleyen ikinci tüketici) da doğru çalıştığı kanıtlandı (onay-bekleme durumu, `data_science` testiyle aynı desen).

### 15.2 — Gemini/OpenAI "browser-use" ve görsel-üretim araştırması (TAMAMLANDI, ikisi de REDDEDİLDİ)

Kullanıcının "Cloudflare tek başına yetmez, Gemini/ChatGPT browser-use kullanılabilmeli" talebi üzerine gerçek 2026 durumu araştırıldı:
- **OpenAI `computer-use-preview`:** Ücretli ($3/$12 per 1M token), preview statüsünde, sadece Responses API — "free as possible" ilkesine AYKIRI, KULLANILMAYACAK.
- **Google Project Mariner:** **2026 Mayıs'ta tamamen kapatıldı** — artık bağımsız bir API değil, sadece Gemini app (tüketici) ve Chrome "Auto Browse" (AI Pro/Ultra abonelik, sadece ABD) içine gömüldü. Geliştiricilere açık genel bir API YOK.
- **Gemini görsel üretim (Imagen/Nano Banana):** Gerçek bir ücretsiz API katmanı YOK (ücretsiz sadece web arayüzü/AI Studio, API çağrısı $0.02-$0.13/görsel).

**Karar:** İkisi de kullanılmayacak. Kullanıcının "API yok, login olabilmeli" netleştirmesiyle OpenClaw'un KENDİ yerleşik `browser` aracı (ücretsiz, gerçek Playwright/Chromium, oturum/cookie tutabilir) doğru çözüm olarak teyit edildi.

### 15.3 — `browser` tool kök neden bulundu ve DÜZELTİLDİ (Fable5→Opus→Haiku tek tur, kullanıcı onayıyla)

**Bulgu zinciri (üç ayrı katman, sırayla soyulmuş):**
1. İlk hata: `FailoverError: invalid literal for int() with base 10: 'tool_use_failed'` — OpenClaw'un kendi hata/failover kodunda bir tool başarısız olduğunda ortaya çıkan, sayı beklerken string alan bir client-side bug.
2. Bunun altında: `plugin-skills/browser-automation` dizini **tamamen boştu** (Ki'nin ana instance'ında bu bir symlink, ki-enterprise'da gerçek/boş bir dizin — Faz 0 kurulumunda hiç oluşturulmamış). Düzeltildi: `/usr/lib/node_modules/openclaw/dist/extensions/browser/skills/browser-automation`'a symlink kuruldu (global sistem paketi, Ki'nin KENDİ instance state'ine bağımlılık YARATMIYOR — bağımsızlık ilkesi korundu).
3. Bunun da altında, ASIL kök neden: `openclaw.json`'da (ki-enterprise) **`plugins` ve `browser` üst-seviye blokları HİÇ YOKTU** — `plugins.allow` listesi boş olduğu için `browser.request` gateway metodu register OLMUYORDU (`GatewayClientRequestError: unknown method: browser.request` — hem agent üzerinden hem DOĞRUDAN CLI'dan (`openclaw browser open <url>`, agent/LLM'siz) aynı hatayı verdiği kanıtlandı). Ki'nin ana instance'ında `plugins.allow` içinde `"browser"`/`"canvas"` vardı, ki-enterprise'da YOKTU. Düzeltme: `plugins.allow: ["browser","canvas"]` + `browser: {"noSandbox": true}` eklendi (Ki'nin ana instance'ından SADECE bu iki alan kopyalandı, telegram/whatsapp/diğer entegrasyonlar KOPYALANMADI — bağımsızlık ilkesi korundu).

**Doğrulama:** Düzeltme sonrası `openclaw --profile ki-enterprise browser open https://kibusiness.co` (agent'sız, doğrudan CLI) ANINDA çalıştı (`opened: https://kibusiness.co/`) — kök neden KESİN olarak çözüldü. **Bilinen açık nokta:** Bir OpenClaw AGENT'ının (LLM üzerinden) bu aracı uçtan uca çağırdığı henüz canlı doğrulanamadı — birden fazla denemede `ki-cloud-chief` (groq/gpt-oss-120b) modeli OpenClaw'un CLI `--local` modunda 45-135 saniye sonra "aborted" oldu, ama AYNI modele doğrudan curl her seferinde <1 saniyede yanıt verdi. Bu, OpenClaw'un CLI `--local` agent-çağırma katmanında AYRI, henüz kök nedeni bulunmamış bir güvenilirlik sorununu işaret ediyor (bugün defalarca gözlemlendi, sadece browser/image-mcp testlerine özgü değil).

### 15.4 — image-mcp: LiteLLM'i bypass eden görsel üretim sunucusu (KOD TAMAMLANDI, kayıt TAMAMLANDI, agent-üzerinden uçtan-uca doğrulama YARIM)

- `/opt/ki-enterprise/core/image-mcp/server.py` — tek tool (`generate_image`), Cloudflare Workers AI'i (`@cf/stabilityai/stable-diffusion-xl-base-1.0`) DOĞRUDAN çağırır (LiteLLM'in `/v1/images/generations` ucunun binary-PNG yanıtını işleyemediği §13.1'de kanıtlanmıştı), `mcp.server.fastmcp.Image` ile gerçek görsel içeriği MCP `ImageContent`'e çevirir.
- **Protokol-seviyesi doğrulama (OpenClaw'dan BAĞIMSIZ, ham MCP client ile):** `initialize` + `tools/list` çağrıları 0.52 saniyede doğru yanıt döndü, `generate_image` tool'u doğru şemayla listelendi. Sunucunun KENDİSİ sağlam.
- `openclaw --profile ki-enterprise mcp set image-mcp '...'` ile kaydedildi, `cmo-visual-analyst`'in `tools.allow`'una `image-mcp__generate_image` eklendi.
- **Agent-üzerinden (LLM'in tool'u gerçekten çağırdığı) uçtan uca test §15.3'teki AYNI OpenClaw CLI güvenilirlik sorununa takıldı** (model-fetch 45s+ sonra aborted, ama doğrudan curl <1s) — sunucu/kayıt sağlam olduğu için bu image-mcp'ye özgü bir kusur DEĞİL, §15.3'ün sonundaki genel OpenClaw `--local` sorunu.

### 15.5 — Sıradaki adım (kullanıcı onayı gerekirse)
OpenClaw'un CLI `--local` modundaki genel agent-çağırma güvenilirlik sorunu (browser VE image-mcp testlerinde AYNI belirtiyle karşılaşıldı: doğrudan model çağrısı hızlı, agent üzerinden defalarca "aborted") ayrı, daha derin bir araştırma gerektiriyor — belki `--local` yerine gateway/Telegram üzerinden (John'un gerçek kullandığı yol) test edilmeli, ya da OpenClaw'un kendi CLI embedded-run kodu incelenmeli. Bu oturumda kullanıcının "tek tur, sonra devam" talimatı gereği DAHA FAZLA kazılmadı.

### 15.6 — Regresyon kontrolü: core/dashboard + core/improvement (TAMAMLANDI, 2026-07-16)

`core.env`'deki paylaşılan alanlar (`ACTIVE_DEPARTMENTS`, `WORKFLOW_TO_DEPARTMENT`) bugün önemli ölçüde değişti — bunlara bağımlı iki servis (core/dashboard port 5009, core/improvement port 5010) **de Phase 9/10'dan beri hiç systemd unit'i yokmuş** (core/departments'la AYNI eksiklik deseni) — `ki-enterprise-dashboard.service` ve `ki-enterprise-improvement.service` oluşturuldu, `enable --now`, ikisi de sağlıklı.

**2026-07-16 devamı — Dashboard'un dış erişimi (Nginx Proxy Manager + Cloudflare, `enterprise.kibusiness.co`) kuruldu:** Kullanıcı `core/dashboard`'u `enterprise.kibusiness.co` üzerinden yayınlamak istedi ama 502 aldı. Kök neden zinciri: (1) NPM (Nginx Proxy Manager, ayrı bir Docker container, `npm-app-1`) `127.0.0.1:5009`'a proxy yapıyordu — NPM kendi container'ının İÇİNDE çalıştığı için bu, NPM'in kendi loopback'i, host'un DEĞİL. (2) Kullanıcı AÇIKÇA ufw ile host portu açılmasını YASAKLADI ("ufw ile açma sakın", "dışarıya sadece nginx üzerinden bağlanacak, ip port açılmayacak") — bunun yerine SAF DOCKER AĞI çözümü istendi. **Çözüm:** `core/dashboard` host sürecinden ÇIKARILDI, Docker container'ına alındı (`core/dashboard/Dockerfile` + `docker/dashboard/docker-compose.yml`), HEM `ki-enterprise` (iç, 192.168.144.0/20) HEM `external_network` (NPM'in de üzerinde olduğu paylaşılan ağ, 192.168.16.0/20) ağlarına bağlandı — NPM artık container adıyla (`ki-enterprise-dashboard`) DOĞRUDAN container-to-container erişiyor, host'a hiç çıkmıyor, ufw'ye hiç dokunulmadı. Eski host systemd servisi durduruldu/disable edildi (çakışma önlendi). Kök path (`/`) 404 veriyordu (sadece `/ui` route'u vardı) — `RedirectResponse("/ui")` eklendi.

**Dashboard'un kendi downstream çağrıları için (container'dan host'taki 8 servise) kullanıcı onayıyla `litellm→ollama` ile AYNI desen (host.docker.internal + ufw, ama SADECE iki docker ağının CIDR'lerinden, "Anywhere" değil) uygulandı** — bu, "dışarıdan içeri" (internet'ten dashboard'a) değil "container'dan host'a" (zaten iç ağdan) giden FARKLI bir yön olduğu için kullanıcı ayrıca onayladı. Bu sırada 2 ayrı, benden bağımsız gerçek altyapı eksikliği daha bulundu: `ai-gateway/executives/departments/workers/projects` servisleri `127.0.0.1`'e bağlıydı (artık `0.0.0.0`, ufw zaten sadece 2 docker CIDR'inden 5000-5007'ye izin verdiği için güvenli) VE `core/skills` (port 5007) `core/departments` ile AYNI eksiklikle hiç systemd unit'i olmadan manuel bir süreç olarak çalışıyordu — `ki-enterprise-skills.service` oluşturuldu. **Sonuç: dashboard artık `enterprise.kibusiness.co` üzerinden erişilebilir VE tüm 8 alt-servisten gerçek canlı veri çekebiliyor** (`/api/v1/dashboard/system` 8/8 servisi sağlıklı raporluyor, gerçek curl ile doğrulandı).

**KRİTİK, KULLANICI TARAFINDAN BULUNAN güvenlik açığı (aynı turda, hemen sonra):** `enterprise.kibusiness.co` HİÇBİR kimlik doğrulama olmadan gerçek şirket verisini gösteriyordu. Kök neden: eski Traefik kurulumunda `/dashboard` yolu `ki-dashboard-auth` (HTTP Basic Auth, kullanıcı `mirac`) middleware'iyle korunuyordu — NPM'e (`enterprise.kibusiness.co`) geçilirken bu koruma HİÇ TAŞINMADI. `core/dashboard`'un kendi `/ui` sayfası KASITLI OLARAK auth'suzdur (tasarım gereği, gerçek erişim kontrolünün proxy katmanında olması beklenir) — bu varsayım NPM'e geçince kırıldı. **Çözüm (kullanıcı tercihi):** Uygulama koduna DOKUNULMADI — kullanıcı NPM'in kendi "Access List" özelliğini (şifre korumalı liste) Proxy Host'a uygulayacak, Traefik'teki Basic Auth'un birebir NPM karşılığı. **Not:** Bu adım bu oturumda TAMAMLANDI MI doğrulanmadı — kullanıcı NPM arayüzünden kendisi yapacak, bir sonraki oturumda `enterprise.kibusiness.co`'nun gerçekten şifre sorduğu KONTROL EDİLMELİ.

**Gerçek, olumlu doğrulama:** `GET /api/v1/improvement/analyze` artık **"5 departman hiçbir zaman iş almıyor" bulgusunu ÜRETMİYOR** — bugünkü `WORKFLOW_TO_DEPARTMENT` genişlemesinin (§14.1) self-improvement servisinin KENDİ, kod-tabanlı analizine de doğru şekilde yansıdığının kanıtı (üretilen tek metin değil, gerçek veri sorgusu). Kalan 3 öneri (19 kullanılmayan skill, ki-business'ta 2 maliyet-işaretli iş, dashboard'un onay-bekleme görünürlüğü) benim değişikliklerimden ÖNCE de var olan, benimle ilgisiz gerçek bulgular — hiçbiri bugünkü değişikliklerden kaynaklı yeni bir sorun değil. `GET /api/v1/dashboard/system` 8/8 servisi sağlıklı raporluyor (departments dahil).

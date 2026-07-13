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

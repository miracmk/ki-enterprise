"""
KI Enterprise Skill Registry (Phase 7).

Build order'daki skill formati:
  name / description / tools / inputs / outputs / workflow

Skill'ler statik dokumantasyon DEGIL - gercekten CALISTIRILABILIR: her skill'in
"workflow" alani AI Gateway'e gonderilecek adim-adim talimata donusur, "inputs"
alani cagiran tarafin sagladigi degerlerin zorunlu-alan kontrolunden gecmesini
saglar. Build order'daki 5 ornek skill + disaridan uyarlanan skill'ler burada
tanimlidir.

Her skill'e "owner_role" (core/executives:ROLES - cto/cfo/cmo/coo/ciso) ve
"source" (bu skill'in hangi disaridan disiplinden uyarlandigi) eklendi -
organizasyon semasinin (core/organization/ORG_CHART.md) tek veri kaynagi
budur. Kod satir satir kopyalanmadi - kaynak projelerin metodolojisi bu
registry'nin execute-edilebilir workflow formatina uyarlandi:
  - superpowers (github.com/obra/superpowers): TDD/sistematik debugging/code-review disiplinleri.
  - claude-mem (github.com/thedotmack/claude-mem): oturumlar-arasi sikistirilmis hafiza ozeti fikri.
  - gstack (github.com/garrytan/gstack): algi (browse/qa/investigate) ve yurutum (ship/deploy) skilleri.
  - Anthropic frontend-design/code-review/security-review skilleri.
  - finrobot (ai4finance-foundation/finrobot): "deterministic compute, LLM narration" ilkesi,
    ROI/senaryo (bull/base/bear) analiz disiplini - gercek piyasa verisi/DCF motoru YOK,
    LLM'in akil yurutme sablonu uyarlandi.
  - cfo-stack (MikeChongCan/cfo-stack): C.L.E.A.R. dongusunun "Extract/Report" fazlari
    (butce sapma/reconciliation analizi) - gercek Beancount defteri/banka entegrasyonu YOK.
  - ai-cfo-agent (daniel-st3/ai-cfo-agent): runway/burn-rate/saglik-skoru kavrami ve
    anomali-tespiti sezgisel kurallari - gercek KPI/Monte Carlo motoru YOK, LLM'e
    kural-tabanli bir kontrol listesi olarak verildi.
  - kai-cmo-harness (cgallic/kai-cmo-harness): kalite kapilari (Four U's basli/kopya
    skoru, yasak kelime kontrolu), coklu-kanal pazarlama denetimi, asama-bazli
    kanal/butce tahsisi disiplini.
  - Multi-Agent-Marketing-Course (The-Swarm-Corporation): A/B test sonucu yorumlama
    disiplini + sequential/parallel/dynamic orkestrasyon mod secimi (CEO dispatch icin).
  - gstack (garrytan/gstack) - IKINCI tur, CEO/Executive Board/Worker odakli: /office-hours
    + /plan-ceo-review (talebi zorlayici sorularla cercevele + kapsam karari), /cso
    (STRIDE tehdit modeli, guven-esikli), /careful+/freeze+/guard (yikici aksiyon
    kapisi), /retro (operasyonel retrospektif), /qa (adversarial test tasarimi).

  NOT (owner_role genisletildi): Bu turda "ceo" (core/executives disindaki, ayri
  core/ceo servisi) ve worker-tier departman adlari (orn. "development") da
  owner_role olarak kullanildi - core/executives:ROLES ile SINIRLI degil, sadece
  bu registry'nin/ORG_CHART'in organizasyonel gruplamasi.

  NOT (katki bulunamadi): foundationagents/metagpt IKI KEZ incelendi (CMO turunde
  ve bu CEO/Board/Worker turunde) - ikisinde de ozgun/somut yeni bir katki
  bulunamadi, "Code=SOP(Team)" felsefesi kavramsal olarak gstack'in
  /office-hours->/plan-ceo-review->/plan-eng-review zincirinin ayni fikrini
  tasiyor, ayrica somut hiyerarsi/onay mekanizmasi genel dokumanlardan
  cikarilamadi. RunMaestro/Maestro incelendi - bu bir MASAUSTU UYGULAMASI
  (git worktree/oturum yonetimi, insan gelistiricinin birden fazla kodlama
  ajanini yonetmesi icindir), akil yurutme/skill icerigi degil - en yakin
  kavrami (Group Chat: stratejik karar icin multi-ajan istisaresi) zaten
  core/executives'in review ucunda karsilaniyor, buradan da skill eklenmedi.
"""

SKILLS = {
    "instagram-content-generation": {
        "name": "instagram-content-generation",
        "owner_role": "cmo",
        "source": "build-order",
        "description": "Belirli bir konu/marka icin Instagram gonderi metinleri ve hashtag setleri uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "topic": {"type": "str", "required": True, "description": "Icerik konusu/marka"},
            "tone": {"type": "str", "required": False, "description": "Ton (orn. eglenceli, profesyonel)", "default": "samimi ve profesyonel"},
            "count": {"type": "int", "required": False, "description": "Uretilecek gonderi sayisi", "default": 3},
        },
        "outputs": {"posts": "list[{caption: str, hashtags: list[str]}]"},
        "workflow": [
            "Konuyu ve hedef kitleyi kisaca analiz et.",
            "Belirtilen sayida, birbirinden farkli Instagram gonderi metni (caption) yaz.",
            "Her gonderi icin 5-10 ilgili, kullanima hazir hashtag oner.",
            "Ciktiyi JSON formatinda, SADECE {\"posts\": [{\"caption\": ..., \"hashtags\": [...]}]} semasina uygun dondur.",
        ],
    },
    "competitor-analysis": {
        "name": "competitor-analysis",
        "owner_role": "cmo",
        "source": "build-order",
        "description": "Belirtilen rakip(ler) icin pazar konumlandirma, guclu/zayif yon analizi uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "competitors": {"type": "list[str]", "required": True, "description": "Analiz edilecek rakip isimleri"},
            "focus_area": {"type": "str", "required": False, "description": "Odaklanilacak alan (orn. fiyatlandirma, ozellikler)", "default": "genel pazar konumlandirmasi"},
        },
        "outputs": {"analysis": "list[{competitor: str, strengths: list[str], weaknesses: list[str], notes: str}]"},
        "workflow": [
            "Her rakip icin bilinen/mantikli varsayimlara dayali guclu yonleri listele.",
            "Her rakip icin zayif yonleri/firsat alanlarini listele.",
            "Belirtilen odak alanina gore kisa bir stratejik not ekle.",
            "Ciktiyi JSON formatinda, SADECE {\"analysis\": [...]} semasina uygun dondur.",
        ],
    },
    "landing-page-audit": {
        "name": "landing-page-audit",
        "owner_role": "cmo",
        "source": "build-order",
        "description": "Bir landing page taslagi/URL'i icin donusum-odakli bir denetim raporu uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "page_description": {"type": "str", "required": True, "description": "Sayfanin mevcut icerigi/yapisi (metin olarak)"},
            "goal": {"type": "str", "required": False, "description": "Sayfanin donusum hedefi", "default": "kayit/satin alma donusumu"},
        },
        "outputs": {"findings": "list[{category: str, issue: str, recommendation: str, severity: str}]"},
        "workflow": [
            "Sayfayi basaligin netligi, deger onerisi, CTA yerlesimi, guven unsurlari acisindan degerlendir.",
            "Her sorunu bir kategori (baslik/CTA/guven/SEO/hiz) ve onem derecesi (dusuk/orta/yuksek) ile etiketle.",
            "Her sorun icin somut, uygulanabilir bir oneri ver.",
            "Ciktiyi JSON formatinda, SADECE {\"findings\": [...]} semasina uygun dondur.",
        ],
    },
    "feature-planning": {
        "name": "feature-planning",
        "owner_role": "cto",
        "source": "build-order",
        "description": "Bir ozellik talebini somut, uygulanabilir bir gelistirme planina donusturur.",
        "tools": ["ai-gateway"],
        "inputs": {
            "feature_description": {"type": "str", "required": True, "description": "Ozellik talebinin aciklamasi"},
            "constraints": {"type": "str", "required": False, "description": "Bilinen kisitlar (sure, teknoloji, vb.)", "default": ""},
        },
        "outputs": {"plan": "{summary: str, steps: list[{title: str, description: str}], risks: list[str]}"},
        "workflow": [
            "Ozelligi 1-2 cumleyle ozetle.",
            "Uygulamayi somut adimlara bol (her adim icin baslik + kisa aciklama).",
            "Olasi riskleri/acik sorulari listele.",
            "Ciktiyi JSON formatinda, SADECE {\"plan\": {...}} semasina uygun dondur.",
        ],
    },
    "bug-investigation": {
        "name": "bug-investigation",
        "owner_role": "cto",
        "source": "build-order",
        "description": "Bir hata raporunu analiz edip olasi kok nedenleri ve teshis adimlarini uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "bug_report": {"type": "str", "required": True, "description": "Hata aciklamasi/log/hata mesaji"},
            "context": {"type": "str", "required": False, "description": "Sistem/kod baglami", "default": ""},
        },
        "outputs": {"hypotheses": "list[{cause: str, likelihood: str, diagnostic_step: str}]"},
        "workflow": [
            "Hata raporunu analiz ederek olasi kok neden hipotezlerini listele.",
            "Her hipotez icin olasilik derecesi (dusuk/orta/yuksek) belirle.",
            "Her hipotezi dogrulamak/elemek icin somut bir teshis adimi oner.",
            "Ciktiyi JSON formatinda, SADECE {\"hypotheses\": [...]} semasina uygun dondur.",
        ],
    },

    # --- Asagidaki 8 skill disaridan uyarlanmistir (bkz. dosya basi aciklamasi) ---

    "test-driven-development-plan": {
        "name": "test-driven-development-plan",
        "owner_role": "cto",
        "source": "superpowers (obra/superpowers: test-driven-development)",
        "description": "Bir ozellik/degisiklik icin RED-GREEN-REFACTOR dongusune uygun bir test-once gelistirme plani uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "feature_description": {"type": "str", "required": True, "description": "Gelistirilecek ozellik/degisiklik"},
            "existing_test_setup": {"type": "str", "required": False, "description": "Mevcut test altyapisi/framework bilgisi", "default": ""},
        },
        "outputs": {"plan": "{red_steps: list[str], green_steps: list[str], refactor_steps: list[str]}"},
        "workflow": [
            "Once basarisiz olmasi beklenen (RED) somut test senaryolarini listele.",
            "Bu testleri gecirecek (GREEN) minimum implementasyon adimlarini listele.",
            "Testler yesilken uygulanabilecek (REFACTOR) temizlik adimlarini listele.",
            "Ciktiyi JSON formatinda, SADECE {\"plan\": {...}} semasina uygun dondur.",
        ],
    },
    "systematic-debugging": {
        "name": "systematic-debugging",
        "owner_role": "cto",
        "source": "superpowers (obra/superpowers: systematic-debugging)",
        "description": "Bir hatayi 4 fazli (gozlem/hipotez/test/dogrulama) kok-neden bulma surecine gore analiz eder.",
        "tools": ["ai-gateway"],
        "inputs": {
            "symptom": {"type": "str", "required": True, "description": "Gozlemlenen hata/semptom"},
            "logs_or_context": {"type": "str", "required": False, "description": "Log/stack trace/ek baglam", "default": ""},
        },
        "outputs": {"analysis": "{observation: str, hypotheses: list[str], test_plan: list[str], verification: str}"},
        "workflow": [
            "FAZ 1 - Gozlem: semptomu net, varsayimsiz sekilde tanimla.",
            "FAZ 2 - Hipotez: olasi kok nedenleri listele.",
            "FAZ 3 - Test: her hipotezi eleyecek/dogrulayacak somut bir adim oner.",
            "FAZ 4 - Dogrulama: duzeltme sonrasi neyin kontrol edilmesi gerektigini belirt.",
            "Ciktiyi JSON formatinda, SADECE {\"analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "code-review-audit": {
        "name": "code-review-audit",
        "owner_role": "cto",
        "source": "Anthropic code-review skill",
        "description": "Verilen bir kod/diff aciklamasi icin doğruluk hatalari ve sadelestirme/verimlilik bulgulari uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "diff_description": {"type": "str", "required": True, "description": "Incelenecek kod/diff'in metinsel ozeti veya icerigi"},
            "effort": {"type": "str", "required": False, "description": "Inceleme derinligi (low/medium/high)", "default": "medium"},
        },
        "outputs": {"findings": "list[{file: str, summary: str, severity: str}]"},
        "workflow": [
            "Kodu dogruluk hatalari (mantik hatasi, edge-case, hatali varsayim) acisindan incele.",
            "Gereksiz karmasiklik/tekrar/verimsizlik bulgularini ayrica listele.",
            "Her bulguyu dosya/konum + kisa ozet + onem derecesi (dusuk/orta/yuksek) ile etiketle.",
            "Ciktiyi JSON formatinda, SADECE {\"findings\": [...]} semasina uygun dondur.",
        ],
    },
    "security-vulnerability-audit": {
        "name": "security-vulnerability-audit",
        "owner_role": "ciso",
        "source": "Anthropic security-review skill",
        "description": "Verilen bir kod/sistem aciklamasi icin OWASP-tarzi guvenlik aciklarini tarar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "system_description": {"type": "str", "required": True, "description": "Incelenecek kod/sistem/akis aciklamasi"},
            "known_context": {"type": "str", "required": False, "description": "Bilinen kisitlar/mimari notlar", "default": ""},
        },
        "outputs": {"vulnerabilities": "list[{category: str, description: str, severity: str, mitigation: str}]"},
        "workflow": [
            "Girdiyi injection, auth/authz, veri sizintisi, guvensiz varsayilanlar acisindan tara.",
            "Her bulguyu OWASP benzeri bir kategori ile etiketle.",
            "Onem derecesi (dusuk/orta/yuksek/kritik) ve somut bir azaltma (mitigation) onerisi ekle.",
            "Ciktiyi JSON formatinda, SADECE {\"vulnerabilities\": [...]} semasina uygun dondur.",
        ],
    },
    "stride-threat-model": {
        "name": "stride-threat-model",
        "owner_role": "ciso",
        "source": "gstack (garrytan/gstack: /cso)",
        "description": "Bir sistemi STRIDE (Spoofing/Tampering/Repudiation/Information Disclosure/DoS/Elevation of Privilege) tehdit modeli kategorilerine gore degerlendirir, sadece yuksek-guvenli bulgulari raporlar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "system_description": {"type": "str", "required": True, "description": "Tehdit modeli cikarilacak sistem/akis aciklamasi"},
            "assets_at_risk": {"type": "str", "required": False, "description": "Korunmasi gereken varliklar/veriler (varsa)", "default": ""},
        },
        "outputs": {"threats": "list[{category: str, description: str, confidence: int, exploit_scenario: str}]"},
        "workflow": [
            "STRIDE'in her kategorisini (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) ayri ayri degerlendir.",
            "SADECE 8/10 ve uzeri guven duzeyindeki (somut, gerceklestirilebilir) tehditleri raporla - yanlis pozitif riskini azaltmak icin dusuk guvenli/teorik olanlari ele.",
            "Her tehdit icin somut, gerceklestirilebilir bir somuru (exploit) senaryosu yaz.",
            "Ciktiyi JSON formatinda, SADECE {\"threats\": [...]} semasina uygun dondur.",
        ],
    },
    "high-risk-action-guardrail-check": {
        "name": "high-risk-action-guardrail-check",
        "owner_role": "ciso",
        "source": "gstack (garrytan/gstack: /careful, /freeze, /guard power tool'lari)",
        "description": "Onerilen bir aksiyonun yikici/geri-alinamaz olup olmadigini degerlendirir, risk seviyesi verir ve daha guvenli bir alternatif onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "proposed_action": {"type": "str", "required": True, "description": "Degerlendirilecek onerilen aksiyon/komut/islem"},
            "context": {"type": "str", "required": False, "description": "Ek baglam (ortam, kapsam, geri-alinabilirlik bilgisi)", "default": ""},
        },
        "outputs": {"assessment": "{risk_level: str, destructive: bool, requires_confirmation: bool, safer_alternative: str}"},
        "workflow": [
            "Aksiyonun geri-alinamaz/yikici olup olmadigini (dosya/veri silme, veritabani DROP, force push, prod'a dogrudan mudahale gibi) degerlendir.",
            "Risk seviyesini (dusuk/orta/yuksek/kritik) belirle.",
            "Yikici ise daha guvenli/geri-alinabilir bir alternatif oner (orn. once yedekle, dry-run, once onay iste).",
            "requires_confirmation alanini risk yuksek/kritikse true yap.",
            "Ciktiyi JSON formatinda, SADECE {\"assessment\": {...}} semasina uygun dondur.",
        ],
    },
    "frontend-design-brief": {
        "name": "frontend-design-brief",
        "owner_role": "cto",
        "source": "Anthropic frontend-design skill",
        "description": "Bir arayuz/ekran talebi icin duzen, bilesen ve etkilesim onerileri iceren bir tasarim brief'i uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "screen_description": {"type": "str", "required": True, "description": "Istenen ekran/bilesenin aciklamasi"},
            "constraints": {"type": "str", "required": False, "description": "Marka/erisilebilirlik/responsive kisitlari", "default": ""},
        },
        "outputs": {"brief": "{layout: str, components: list[str], interactions: list[str], accessibility_notes: list[str]}"},
        "workflow": [
            "Ekranin genel duzenini (layout) kisaca tanimla.",
            "Gereken UI bilesenlerini listele.",
            "Onemli etkilesim/durum (hover, hata, bos-durum) davranislarini listele.",
            "Erisilebilirlik (accessibility) notlarini ekle.",
            "Ciktiyi JSON formatinda, SADECE {\"brief\": {...}} semasina uygun dondur.",
        ],
    },
    "operational-retro-report": {
        "name": "operational-retro-report",
        "owner_role": "coo",
        "source": "gstack (garrytan/gstack: /retro)",
        "description": "Tamamlanan bir donemin isini iyi/kotu giden olarak ayirip somut eylem maddeleri (action items) uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "completed_work_summary": {"type": "str", "required": True, "description": "Donem icinde tamamlanan islerin serbest metin ozeti"},
            "period_label": {"type": "str", "required": False, "description": "Donem etiketi (orn. 'bu hafta', 'Temmuz')", "default": "bu donem"},
        },
        "outputs": {"retro": "{went_well: list[str], went_poorly: list[str], action_items: list[str]}"},
        "workflow": [
            "Tamamlanan isleri iyi giden ve kotu giden/sorunlu olarak ayir.",
            "Her sorun icin somut, uygulanabilir bir eylem maddesi oner.",
            "Bir sonraki donem icin en onemli 1-3 degisikligi one cikar.",
            "Ciktiyi JSON formatinda, SADECE {\"retro\": {...}} semasina uygun dondur.",
        ],
    },
    "institutional-memory-digest": {
        "name": "institutional-memory-digest",
        "owner_role": "coo",
        "source": "claude-mem (thedotmack/claude-mem)",
        "description": "Bir donemin ham karar/rapor kayitlarini, gelecekte hizlica taranabilecek sikistirilmis bir ozete donusturur.",
        "tools": ["ai-gateway"],
        "inputs": {
            "raw_records": {"type": "str", "required": True, "description": "Ozetlenecek ham kayit/karar/rapor metinleri"},
            "focus": {"type": "str", "required": False, "description": "Ozette one cikarilacak konu", "default": "genel"},
        },
        "outputs": {"digest": "{summary: str, key_decisions: list[str], open_questions: list[str]}"},
        "workflow": [
            "Ham kayitlari kisa, arama-dostu bir ozete sikistir.",
            "Onemli kararlari ayrica madde madde cikar.",
            "Cevaplanmamis/acik sorulari listele.",
            "Ciktiyi JSON formatinda, SADECE {\"digest\": {...}} semasina uygun dondur.",
        ],
    },
    "production-readiness-check": {
        "name": "production-readiness-check",
        "owner_role": "coo",
        "source": "gstack (garrytan/gstack: /ship, /land-and-deploy)",
        "description": "Bir teslimatin production'a cikmadan once yurutum/operasyon acisindan hazir olup olmadigini kontrol eder.",
        "tools": ["ai-gateway"],
        "inputs": {
            "deliverable_description": {"type": "str", "required": True, "description": "Yayina alinacak teslimatin aciklamasi"},
            "deployment_context": {"type": "str", "required": False, "description": "Deployment/altyapi baglami", "default": ""},
        },
        "outputs": {"checklist": "list[{item: str, status: str, note: str}]"},
        "workflow": [
            "Yayin-oncesi standart kontrol maddelerini (test/gozden gecirme/geri-alma plani/izleme) listele.",
            "Verilen aciklamaya gore her maddenin durumunu (tamam/eksik/bilinmiyor) degerlendir.",
            "Eksik/bilinmeyen maddeler icin kisa bir not ekle.",
            "Ciktiyi JSON formatinda, SADECE {\"checklist\": [...]} semasina uygun dondur.",
        ],
    },
    "request-scope-framing": {
        "name": "request-scope-framing",
        "owner_role": "ceo",
        "source": "gstack (garrytan/gstack: /office-hours, /plan-ceo-review)",
        "description": "Bir talebi dispatch etmeden once zorlayici sorularla cerceveler ve bir kapsam karari (Expansion/Selective Expansion/Hold Scope/Reduction) uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "request_description": {"type": "str", "required": True, "description": "Degerlendirilecek ham talep"},
            "known_constraints": {"type": "str", "required": False, "description": "Bilinen kisitlar (sure, butce, teknik) varsa", "default": ""},
        },
        "outputs": {"framing": "{forcing_questions: list[str], scope_decision: str, rationale: str}"},
        "workflow": [
            "Talebi netlestirmek icin 4-6 zorlayici soru uret (neden simdi, kimin icin, en kucuk deger verecek surum ne, nelerden vazgecilebilir).",
            "Verilen/varsayilan cevaplara gore bir kapsam modu sec: Expansion (daha genis yap), Selective Expansion (bazi ekleri kabul et), Hold Scope (oldugu gibi dagit), Reduction (daralt).",
            "Secimin gerekcesini kisaca acikla.",
            "Ciktiyi JSON formatinda, SADECE {\"framing\": {...}} semasina uygun dondur.",
        ],
    },
    "dispatch-orchestration-mode": {
        "name": "dispatch-orchestration-mode",
        "owner_role": "ceo",
        "source": "Multi-Agent-Marketing-Course (The-Swarm-Corporation) - sequential/parallel/dynamic desenler",
        "description": "Bir talebin departmanlar arasinda sirali mi, paralel mi yoksa uyarlanabilir (dinamik) mi dagitilmasi gerektigine karar verir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "request_description": {"type": "str", "required": True, "description": "Dagitilacak talep"},
            "involved_departments": {"type": "str", "required": False, "description": "Etkilenen departmanlar (varsa, virgulle ayrilmis)", "default": ""},
        },
        "outputs": {"decision": "{mode: str, reasoning: str, suggested_sequence: list[str]}"},
        "workflow": [
            "Talebi degerlendirerek en uygun dagitim modunu sec: sequential (adimlar birbirine bagimliysa/kalite kontrolu kritikse), parallel (bagimsiz ve hiz onemliyse), dynamic (belirsizlik yuksekse, sonuclara gore uyarlanmasi gerekiyorsa).",
            "mode sequential ise onerilen departman/adim sirasini listele, degilse bos birak.",
            "Kisa bir gerekce yaz.",
            "Ciktiyi JSON formatinda, SADECE {\"decision\": {...}} semasina uygun dondur.",
        ],
    },
    "capital-decision-analysis": {
        "name": "capital-decision-analysis",
        "owner_role": "cfo",
        "source": "finrobot (ai4finance-foundation/finrobot)",
        "description": "Bir yatirim/harcama karari icin ROI, geri odeme suresi ve bull/base/bear senaryo analizi uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "decision_description": {"type": "str", "required": True, "description": "Degerlendirilecek yatirim/harcama karari"},
            "known_numbers": {"type": "str", "required": False, "description": "Bilinen maliyet/gelir/varsayim rakamlari (varsa)", "default": ""},
        },
        "outputs": {"analysis": "{roi_estimate: str, payback_period: str, scenarios: {bull: str, base: str, bear: str}, recommendation: str}"},
        "workflow": [
            "Verilen rakamlara dayanarak kaba bir ROI ve geri odeme suresi tahmini yap - rakam yoksa bunu ACIKCA varsayim olarak isaretle, uydurma kesinlik verme.",
            "Bull (iyimser), base (beklenen) ve bear (kotumser) olmak uzere 3 ayri senaryo yaz.",
            "Sirket politikasina (once ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli) gore net bir tavsiye ver.",
            "Ciktiyi JSON formatinda, SADECE {\"analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "cash-runway-projection": {
        "name": "cash-runway-projection",
        "owner_role": "cfo",
        "source": "ai-cfo-agent (daniel-st3/ai-cfo-agent)",
        "description": "Verilen nakit/gelir/gider rakamlarina dayanarak runway (kac ay), burn rate ve 0-100 finansal saglik skoru tahmini uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "financial_snapshot": {"type": "str", "required": True, "description": "Mevcut nakit, aylik gelir ve aylik gider bilgisi (serbest metin)"},
            "notes": {"type": "str", "required": False, "description": "Ek baglam (buyume beklentisi, bilinen tek seferlik harcamalar vb.)", "default": ""},
        },
        "outputs": {"projection": "{monthly_burn: str, runway_months: str, health_score: int, health_reasoning: str}"},
        "workflow": [
            "Verilen rakamlardan aylik net yakma (burn) hizini tahmin et.",
            "Mevcut nakitle kac ay dayanilabilecegini (runway) hesapla.",
            "0-100 arasi bir finansal saglik skoru ver (runway uzunlugu + gelir trendi + bilinen riskleri dikkate al) ve nedenini kisaca acikla.",
            "Rakamlar eksik/belirsizse skoru ASLA uydurma - eksik veriyi acikca belirt.",
            "Ciktiyi JSON formatinda, SADECE {\"projection\": {...}} semasina uygun dondur.",
        ],
    },
    "expense-anomaly-scan": {
        "name": "expense-anomaly-scan",
        "owner_role": "cfo",
        "source": "ai-cfo-agent (daniel-st3/ai-cfo-agent)",
        "description": "Bir harcama listesini yuvarlak-sayi/ani-artis/tek-tedarikci-yogunlasmasi gibi sezgisel kurallara gore tarayip anomalileri isaretler.",
        "tools": ["ai-gateway"],
        "inputs": {
            "expense_list": {"type": "str", "required": True, "description": "Incelenecek harcama kalemleri (serbest metin/liste)"},
            "baseline_context": {"type": "str", "required": False, "description": "Normal/beklenen harcama duzeyi hakkinda bilgi", "default": ""},
        },
        "outputs": {"anomalies": "list[{item: str, rule_triggered: str, concern_level: str, suggested_action: str}]"},
        "workflow": [
            "Her harcama kalemini su sezgisel kurallara gore degerlendir: alisilmadik yuvarlak tutarlar, ani/aciklanamayan artislar, tek bir tedarikciye asiri yogunlasma, tekrarlayan/duplicate gorunen kayitlar.",
            "Kural tetiklenen her kalemi, hangi kuralin tetiklendigini ve endise seviyesini (dusuk/orta/yuksek) belirterek listele.",
            "Her biri icin somut bir sonraki adim (dogrulama/aciklama isteme/reddetme) oner.",
            "Ciktiyi JSON formatinda, SADECE {\"anomalies\": [...]} semasina uygun dondur.",
        ],
    },
    "budget-variance-review": {
        "name": "budget-variance-review",
        "owner_role": "cfo",
        "source": "cfo-stack (MikeChongCan/cfo-stack) - C.L.E.A.R. dongusunun Extract/Report fazlari",
        "description": "Planlanan butce ile gerceklesen harcamayi karsilastirip sapma (variance) ve kok neden analizini uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "planned_budget": {"type": "str", "required": True, "description": "Planlanan butce kalemleri/tutarlari"},
            "actual_spend": {"type": "str", "required": True, "description": "Gerceklesen harcama kalemleri/tutarlari"},
        },
        "outputs": {"variance_report": "list[{category: str, planned: str, actual: str, variance_pct: str, likely_cause: str}]"},
        "workflow": [
            "Planlanan ve gerceklesen tutarlari kategori bazinda karsilastir.",
            "Her kategori icin sapma yuzdesini (yaklasik) ve olasi kok nedenini belirt.",
            "Onemli/buyuk sapmalari (>%20 gibi) ayrica vurgula.",
            "Ciktiyi JSON formatinda, SADECE {\"variance_report\": [...]} semasina uygun dondur.",
        ],
    },
    "vendor-cost-audit": {
        "name": "vendor-cost-audit",
        "owner_role": "cfo",
        "source": "cfo-stack (MikeChongCan/cfo-stack) - reconcile/consult fazlari + sirketin mevcut maliyet politikasi",
        "description": "Bir hizmet/vendor secimini sirketin 'once ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli' politikasina gore denetler ve daha ucuz alternatif onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "vendor_or_service": {"type": "str", "required": True, "description": "Degerlendirilecek hizmet/vendor/API"},
            "current_usage": {"type": "str", "required": False, "description": "Mevcut kullanim sekli/miktari (varsa)", "default": ""},
        },
        "outputs": {"audit": "{tier_checked: list[str], free_or_selfhosted_alternative: str, verdict: str, notes: str}"},
        "workflow": [
            "Sirket politikasindaki sirayi (once ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli) uygulayarak bu hizmetin daha ucuz bir alternatifi olup olmadigini degerlendir.",
            "Bilinen ucretsiz/self-hosted/acik-kaynak alternatiflerini somut olarak oner (varsa).",
            "cost_flag mantigina uygun bir sonuc (onay/kaygi/red) ver ve gerekcesini kisaca acikla.",
            "Ciktiyi JSON formatinda, SADECE {\"audit\": {...}} semasina uygun dondur.",
        ],
    },
    "competitive-perception-scan": {
        "name": "competitive-perception-scan",
        "owner_role": "cmo",
        "source": "gstack (garrytan/gstack: /browse, /qa, /investigate)",
        "description": "Bir urun/rakip aciklamasini disaridan bir kullanicinin 'algisi' perspektifinden sistematik olarak degerlendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "product_or_page_description": {"type": "str", "required": True, "description": "Incelenecek urun/sayfa/akis aciklamasi"},
            "persona": {"type": "str", "required": False, "description": "Degerlendirmeyi yapan varsayilan kullanici tipi", "default": "yeni/ilk kez gelen kullanici"},
        },
        "outputs": {"observations": "list[{moment: str, perception: str, friction_point: str}]"},
        "workflow": [
            "Belirtilen kullanici tipinin akisi adim adim nasil deneyimleyecegini simule et.",
            "Her adimda olusan ilk izlenimi/algiyi not et.",
            "Kafa karistirici veya surtunmeli (friction) noktalari ayrica isaretle.",
            "Ciktiyi JSON formatinda, SADECE {\"observations\": [...]} semasina uygun dondur.",
        ],
    },
    "marketing-copy-quality-gate": {
        "name": "marketing-copy-quality-gate",
        "owner_role": "cmo",
        "source": "kai-cmo-harness (cgallic/kai-cmo-harness) - Four U's kalite kapisi",
        "description": "Bir pazarlama metnini/basligini Four U's (Urgent/Unique/Ultra-specific/Useful) olceklerinde puanlar ve yasak/zayif kelime kullanimini isaretler.",
        "tools": ["ai-gateway"],
        "inputs": {
            "copy_text": {"type": "str", "required": True, "description": "Degerlendirilecek pazarlama metni/basligi"},
            "banned_words": {"type": "str", "required": False, "description": "Ek olarak kacinilmasi istenen kelime/ifadeler (virgulle ayrilmis)", "default": ""},
        },
        "outputs": {"scorecard": "{urgent: int, unique: int, ultra_specific: int, useful: int, flagged_words: list[str], rewrite_suggestion: str}"},
        "workflow": [
            "Metni Urgent/Unique/Ultra-specific/Useful (Four U's) olceklerinde 0-10 arasi puanla.",
            "Jenerik/abartili/yasak kelimeleri (orn. 'devrim niteliginde', 'en iyi', kullanicinin belirttigi ek kelimeler) isaretle.",
            "Dusuk puanli boyutlari iyilestiren KISA bir yeniden-yazim onerisi ver.",
            "Ciktiyi JSON formatinda, SADECE {\"scorecard\": {...}} semasina uygun dondur.",
        ],
    },
    "multi-channel-marketing-audit": {
        "name": "multi-channel-marketing-audit",
        "owner_role": "cmo",
        "source": "kai-cmo-harness (cgallic/kai-cmo-harness) - coklu-kanal denetim",
        "description": "Bir markanin/urunun mevcut pazarlama varligini (SEO, icerik, email, reklam, CRO) kanal bazinda denetleyip bulgu listesi uretir - landing-page-audit'ten farkli olarak TEK sayfa degil TUM pazarlama varligini kapsar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "brand_marketing_summary": {"type": "str", "required": True, "description": "Markanin mevcut pazarlama varliginin (site, sosyal, email, reklam) serbest metin ozeti"},
            "priority_channels": {"type": "str", "required": False, "description": "Oncelikli incelenecek kanallar (orn. 'SEO, email')", "default": "SEO, icerik, email, reklam, CRO"},
        },
        "outputs": {"findings": "list[{channel: str, issue: str, recommendation: str, severity: str}]"},
        "workflow": [
            "Belirtilen kanallarin her birini ayri ayri degerlendir.",
            "Her kanal icin somut sorun/eksiklik + onerilen duzeltme + onem derecesi (dusuk/orta/yuksek) belirle.",
            "En kritik 3 bulguyu ozetin basina koy.",
            "Ciktiyi JSON formatinda, SADECE {\"findings\": [...]} semasina uygun dondur.",
        ],
    },
    "channel-budget-allocation": {
        "name": "channel-budget-allocation",
        "owner_role": "cmo",
        "source": "kai-cmo-harness (cgallic/kai-cmo-harness) - asama-bazli buyume planlamasi",
        "description": "Sirketin buyume asamasina ve toplam pazarlama butcesine gore kanallar arasi bir tahsis onerisi uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "growth_stage": {"type": "str", "required": True, "description": "Sirket/urunun buyume asamasi (orn. erken/pre-launch, buyume, olgunluk)"},
            "total_budget_note": {"type": "str", "required": False, "description": "Toplam butce/kisit hakkinda bilgi (varsa)", "default": "belirtilmedi"},
        },
        "outputs": {"allocation": "{channels: list[{channel: str, share_pct: int, rationale: str}], notes: str}"},
        "workflow": [
            "Belirtilen buyume asamasina uygun kanal karisimini (organik/SEO, icerik, email, ucretli reklam, sosyal, ortakliklar) belirle.",
            "Her kanala yuzdesel bir pay ver (toplam %100 olmali) ve kisa bir gerekce yaz.",
            "Sirket politikasina (once ucretsiz, sonra self-hosted, sonra acik kaynak, sonra ucretli) gore ucretli kanallara asiri agirlik verilmemesi konusunda not dus.",
            "Ciktiyi JSON formatinda, SADECE {\"allocation\": {...}} semasina uygun dondur.",
        ],
    },
    "campaign-ab-test-analysis": {
        "name": "campaign-ab-test-analysis",
        "owner_role": "cmo",
        "source": "Multi-Agent-Marketing-Course (The-Swarm-Corporation)",
        "description": "Bir A/B test sonucunu (varyant metrikleri) yorumlayip kazanani, guven duzeyini ve sonraki adimi belirler.",
        "tools": ["ai-gateway"],
        "inputs": {
            "test_results": {"type": "str", "required": True, "description": "A/B test varyantlarinin metrikleri (orn. 'A: 1000 gosterim/50 tiklama, B: 1000 gosterim/68 tiklama')"},
            "test_goal": {"type": "str", "required": False, "description": "Testin olcmeye calistigi hedef (orn. tiklama orani, donusum)", "default": "donusum orani"},
        },
        "outputs": {"verdict": "{winner: str, confidence_level: str, caveats: list[str], next_step: str}"},
        "workflow": [
            "Verilen metriklere gore hangi varyantin daha iyi performans gosterdigini belirle.",
            "Ornek buyuklugune gore KABACA bir guven seviyesi (dusuk/orta/yuksek) ver - istatistiksel anlamlilik testi YAPMADIGINI acikca belirt, sadece yon gosterir.",
            "Kucuk ornek boyutu/kisa test suresi gibi dikkat edilmesi gereken kisitlari (caveats) listele.",
            "Somut bir sonraki adim (testi uzat/kazanani uygula/yeni varyant dene) oner.",
            "Ciktiyi JSON formatinda, SADECE {\"verdict\": {...}} semasina uygun dondur.",
        ],
    },

    # --- Worker-tier skill (owner_role bir core/executives rolu DEGIL, core/workers
    # departman adi - "development") - core/workers henuz core/skills'i cagirmiyor
    # (bilinen kisit, bkz. ORG_CHART.md), bu skill dogrudan API ile calistirilabilir. ---
    "adversarial-test-case-design": {
        "name": "adversarial-test-case-design",
        "owner_role": "development",
        "source": "gstack (garrytan/gstack: /qa) - gercek tarayici YOK, LLM akil yurutmesine uyarlandi",
        "description": "Bir ozelligi kirmaya calisan bir QA zihniyetiyle edge-case/adversarial test senaryolari uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "feature_description": {"type": "str", "required": True, "description": "Test senaryolari uretilecek ozellik/akis aciklamasi"},
            "known_edge_cases": {"type": "str", "required": False, "description": "Bilinen sinir durumlari (varsa)", "default": ""},
        },
        "outputs": {"test_cases": "list[{scenario: str, expected_behavior: str, category: str}]"},
        "workflow": [
            "Ozelligi 'kirmaya calisan' bir zihniyetle (kirici test - Tester/Burak karakteri) edge-case/adversarial senaryolar uret.",
            "Her senaryo icin dogru/beklenen davranisi acikca belirt.",
            "Senaryolari kategorize et (girdi dogrulama, es zamanlilik/race-condition, sinir degerler, yetkilendirme, hata isleme).",
            "Ciktiyi JSON formatinda, SADECE {\"test_cases\": [...]} semasina uygun dondur.",
        ],
    },
}

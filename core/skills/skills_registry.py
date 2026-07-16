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

    # ================================================================
    # CPO (Selin) skilleri - 2026-07-16 eklendi, 9-Chief genislemesi
    # (bkz. ORG_CHART.md, AGENTIC_ARCHITECTURE_PLAN.md SS16). Fable5
    # arastirma turunde bulunan gercek/yayinlanmis urun yonetimi
    # framework'leri, mevcut CTO/CFO skilleriyle AYNI ilkeyle (deterministic
    # compute yok, LLM narration) uyarlandi.
    # ================================================================
    "rice-prioritization-scoring": {
        "name": "rice-prioritization-scoring",
        "owner_role": "cpo",
        "source": "RICE Prioritization Framework (Intercom, Sean McBride)",
        "description": "Roadmap adaylarini RICE (Reach/Impact/Confidence/Effort) metodolojisiyle puanlayip onceliklendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "candidate_features": {"type": "list[str]", "required": True, "description": "Degerlendirilecek ozellik/proje fikirleri"},
            "reach_estimates": {"type": "str", "required": True, "description": "Her fikir icin tahmini etkilenen kullanici sayisi/orani"},
            "impact_notes": {"type": "str", "required": False, "description": "Her fikrin sirket hedeflerine olasi katkisi", "default": ""},
            "effort_estimates": {"type": "str", "required": True, "description": "Kisi-ay cinsinden tahmini efor notlari"},
        },
        "outputs": {"rice_analysis": "{ranking: list[{feature: str, score_reasoning: str}], confidence_flags: list[str]}"},
        "workflow": [
            "Verilen ozellik listesini ve tahminleri oku, eksik veri varsa acikca belirt.",
            "Her fikir icin Reach, Impact, Confidence, Effort degerlerini yorumla (rakam uydurma, verilenle sinirli kal).",
            "RICE skorunu (Reach x Impact x Confidence / Effort) kavramsal olarak hesapla ve gerekcelendir.",
            "Fikirleri skora gore sirala, en yuksek etkili/dusuk efor gerektirenleri one cikar.",
            "Dusuk confidence'a sahip kalemler icin ek veri toplama onerisi sun.",
            "Ciktiyi JSON formatinda, SADECE {\"rice_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "jtbd-job-story-synthesis": {
        "name": "jtbd-job-story-synthesis",
        "owner_role": "cpo",
        "source": "Jobs to Be Done (Clayton Christensen / Tony Ulwick)",
        "description": "Kullanici arastirma verilerinden Jobs-to-be-Done mantigiyla job story'ler ve urun firsatlari cikarir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "user_research_notes": {"type": "str", "required": True, "description": "Gorusme notlari, anket sonuclari veya destek talepleri ozeti"},
            "product_context": {"type": "str", "required": True, "description": "Urunun mevcut konumu ve hedef kullanici segmenti"},
            "known_pain_points": {"type": "list[str]", "required": False, "description": "Onceden bilinen kullanici sikayetleri", "default": []},
        },
        "outputs": {"jtbd_analysis": "{job_stories: list[str], opportunity_summary: str}"},
        "workflow": [
            "Kullanici arastirma verisini oku, tekrar eden davranis/motivasyon kaliplarini tespit et.",
            "Her kalibi 'kullanici X durumundayken Y'yi basarmak istiyor, cunku Z' job story formatina dok.",
            "Fonksiyonel, duygusal ve sosyal boyutlari ayri ayri degerlendir.",
            "En az karsilanmis ama en yuksek talep goren isleri firsat olarak isaretle.",
            "Ciktiyi JSON formatinda, SADECE {\"jtbd_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "kano-feature-classification": {
        "name": "kano-feature-classification",
        "owner_role": "cpo",
        "source": "Kano Model (Noriaki Kano, 1984)",
        "description": "Ozellik listesini Kano modeline gore must-be/performance/delighter kategorilerine ayirip yatirim onceligi onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "feature_list": {"type": "list[str]", "required": True, "description": "Siniflandirilacak ozellik/iyilestirme fikirleri"},
            "customer_feedback": {"type": "str", "required": False, "description": "Bu ozelliklerle ilgili musteri yorumlari", "default": ""},
        },
        "outputs": {"kano_analysis": "{classification: list[{feature: str, category: str, reasoning: str}], investment_recommendation: str}"},
        "workflow": [
            "Ozellik listesini ve varsa musteri geri bildirimlerini oku.",
            "Her ozelligi pazar standardi, musteri beklentisi ve sasirtma potansiyeli acisindan degerlendir.",
            "Must-be (temel), performance (dogrusal memnuniyet), delighter (fark yaratan) veya indifferent olarak siniflandir.",
            "Must-be eksikliklerini kritik risk, delighter'lari farklilasma firsati olarak vurgula.",
            "Ciktiyi JSON formatinda, SADECE {\"kano_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "north-star-metric-tree": {
        "name": "north-star-metric-tree",
        "owner_role": "cpo",
        "source": "North Star Framework (Amplitude / Sean Ellis)",
        "description": "Urun stratejisi ve mevcut metriklerden North Star Metric ile besleyici girdi metrikleri agaci onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "product_value_proposition": {"type": "str", "required": True, "description": "Urunun musteriye sundugu temel degerin ozeti"},
            "current_metrics": {"type": "str", "required": True, "description": "Su an takip edilen kullanim/gelir/etkilesim metrikleri"},
            "business_goals": {"type": "str", "required": False, "description": "Sirketin bu donem icin ana hedefleri", "default": ""},
        },
        "outputs": {"north_star_analysis": "{metric_proposal: str, input_metrics_tree: list[str]}"},
        "workflow": [
            "Urunun deger onermesini ve mevcut metrikleri oku.",
            "Vanity metric olmayan, olculebilir ve etki edilebilir aday metrikleri belirle.",
            "En guclu adayi North Star Metric olarak oner ve gerekcelendir.",
            "Bu metrigi besleyen 3-5 alt girdi metrigini tanimla.",
            "Ciktiyi JSON formatinda, SADECE {\"north_star_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "opportunity-solution-tree-mapping": {
        "name": "opportunity-solution-tree-mapping",
        "owner_role": "cpo",
        "source": "Continuous Discovery Habits - Opportunity Solution Tree (Teresa Torres)",
        "description": "Istenen is sonucundan baslayarak musteri firsatlari, cozum adaylari ve dogrulama deneylerinden olusan bir agac olusturur.",
        "tools": ["ai-gateway"],
        "inputs": {
            "desired_outcome": {"type": "str", "required": True, "description": "Hedeflenen is sonucu (orn. aktivasyon oranini artirmak)"},
            "customer_insights": {"type": "str", "required": True, "description": "Musteri ihtiyac ve aci noktalari"},
            "existing_solution_ideas": {"type": "list[str]", "required": False, "description": "Zaten dusunulen cozum fikirleri", "default": []},
        },
        "outputs": {"opportunity_tree": "{opportunities: list[{opportunity: str, solutions: list[str]}], experiment_plan: str}"},
        "workflow": [
            "Hedeflenen is sonucunu agacin koku olarak netlestir.",
            "Musteri icgorulerini tekrar eden ihtiyac/aci noktalarina gore 'firsat' dallarina ayir.",
            "Her firsat icin mevcut ve yeni cozum fikirlerini eslestir.",
            "Firsatlari outcome'a etkisi ve musteride sikligi acisindan onceliklendir.",
            "Ciktiyi JSON formatinda, SADECE {\"opportunity_tree\": {...}} semasina uygun dondur.",
        ],
    },

    # ================================================================
    # CRO (Doruk) skilleri - 2026-07-16 eklendi
    # ================================================================
    "meddpicc-deal-qualification-scorer": {
        "name": "meddpicc-deal-qualification-scorer",
        "owner_role": "cro",
        "source": "MEDDIC/MEDDPICC Sales Methodology (Dick Dunkel/PTC, MEDDICC.com/Force Management)",
        "description": "Bir satis firsatini MEDDPICC cercevesine gore niteleyip risk/kazanma olasiligi degerlendirmesi uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "deal_name": {"type": "str", "required": True, "description": "Firsat/hesap adi"},
            "deal_notes": {"type": "str", "required": True, "description": "CRM notlari, gorusme ozetleri, e-posta alintilari"},
            "deal_size": {"type": "str", "required": False, "description": "Tahmini sozlesme degeri (ACV/TCV)", "default": ""},
        },
        "outputs": {"meddpicc_scorecard": "{dimensions: list[{name: str, status: str}], risk_flags: list[str], next_actions: list[str]}"},
        "workflow": [
            "Verilen deal notlarini MEDDPICC'in 8 bilesenine (Metrics, Economic Buyer, Decision Criteria, Decision Process, Paper Process, Implicate the Pain, Champion, Competition) gore ayristir.",
            "Her bileseni 'net kanit var / kismi / hic yok' seklinde etiketle.",
            "Economic Buyer ve Champion netligine ozellikle odaklan - bunlar en kritik risk sinyalleridir.",
            "Genel bir kazanma olasiligi yorumu ve gerekcesini uret.",
            "Bosluklari kapatacak somut sonraki adimlari listele.",
            "Ciktiyi JSON formatinda, SADECE {\"meddpicc_scorecard\": {...}} semasina uygun dondur.",
        ],
    },
    "challenger-sale-insight-brief": {
        "name": "challenger-sale-insight-brief",
        "owner_role": "cro",
        "source": "The Challenger Sale (Dixon & Adamson, CEB/Gartner)",
        "description": "Bir hesap/firsat icin Challenger Sale metodolojisine gore commercial teaching icgorusu ve paydas bazli mesaj tayloru uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "account_name": {"type": "str", "required": True, "description": "Hedef hesap/sirket adi"},
            "account_context": {"type": "str", "required": True, "description": "Sektor, mevcut cozum/rakip, bilinen sorunlar"},
            "stakeholders": {"type": "list[str]", "required": True, "description": "Karar alici/etkileyici paydaslar ve rolleri"},
        },
        "outputs": {"challenger_brief": "{commercial_insight: str, stakeholder_messaging: list[{stakeholder: str, message: str}], next_actions: list[str]}"},
        "workflow": [
            "Hesap baglamini ve mevcut status quo varsayimlarini ozetle.",
            "Musterinin fark etmedigi bir risk/firsati ortaya cikaran 'teaching' icgorusu formule et.",
            "Bu icgoruyu her paydasin roluune gore (finansal, operasyonel, stratejik) farkli acilardan tekrar yaz.",
            "Sureci ileri tasiyacak, iddiali ama saygili sonraki adimlar oner.",
            "Ciktiyi JSON formatinda, SADECE {\"challenger_brief\": {...}} semasina uygun dondur.",
        ],
    },
    "bowtie-revenue-funnel-health-check": {
        "name": "bowtie-revenue-funnel-health-check",
        "owner_role": "cro",
        "source": "The Bowtie Model (Winning by Design, Jacco van der Kooij)",
        "description": "Bowtie modeline gore acquisition ve expansion tarafindaki hunileri analiz edip zayif halkalari tespit eder.",
        "tools": ["ai-gateway"],
        "inputs": {
            "acquisition_metrics": {"type": "str", "required": True, "description": "Awareness/Education/Selection asamasi hacim ve donusum verileri"},
            "post_sale_metrics": {"type": "str", "required": True, "description": "Onboarding/Adoption/Expansion asamasi verileri (churn, NRR, adoption)"},
        },
        "outputs": {"bowtie_analysis": "{diagnosis: str, weakest_stage: str, growth_recommendations: list[str]}"},
        "workflow": [
            "Bowtie modelinin alti asamasini (Awareness, Education, Selection, Onboarding, Adoption, Expansion) verilen verilerle eslestir.",
            "Sol taraf (edinme) ile sag taraf (etki/genisleme) performansini karsilastir.",
            "En zayif halkayi tespit et ve musterinin beklenen etkiye ulasamama riskiyle iliskilendir.",
            "Kisa vadeli (taktiksel) ve uzun vadeli (yapisal) iyilestirme onerilerini ayri listele.",
            "Ciktiyi JSON formatinda, SADECE {\"bowtie_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "spiced-discovery-qualification-review": {
        "name": "spiced-discovery-qualification-review",
        "owner_role": "cro",
        "source": "SPICED Framework (Winning by Design)",
        "description": "Bir kesif gorusmesi transkriptini SPICED cercevesine gore analiz edip bosluklari ve aciliyet sinyallerini ortaya cikarir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "call_notes": {"type": "str", "required": True, "description": "Kesif gorusmesi notlari veya transkript"},
            "account_name": {"type": "str", "required": True, "description": "Hesap/firsat adi"},
        },
        "outputs": {"spiced_analysis": "{breakdown: {situation: str, pain: str, impact: str, critical_event: str, decision: str}, follow_up_questions: list[str]}"},
        "workflow": [
            "Gorusme notlarindan Situation (mevcut durum) bilgisini cikar.",
            "Pain (sorun) ifadelerini yuzeysel/derin ayrimiyla belirle, Impact'i (is etkisi) ozetle.",
            "Critical Event (aciliyeti tetikleyen olay) olup olmadigini tespit et.",
            "Decision (karar sureci ve karar vericiler) netligini degerlendir.",
            "Eksik SPICED bilesenlerini kapatmak icin onerilen sonraki sorulari listele.",
            "Ciktiyi JSON formatinda, SADECE {\"spiced_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "sandler-pain-funnel-coach": {
        "name": "sandler-pain-funnel-coach",
        "owner_role": "cro",
        "source": "Sandler Pain Funnel (David H. Sandler, Sandler Selling System)",
        "description": "Bir prospect gorusmesini Sandler Pain Funnel'in uc seviyesine (surface/impact/emotional pain) gore analiz edip derinlestirme sorulari onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "prospect_notes": {"type": "str", "required": True, "description": "Prospect ile yapilan gorusme notlari"},
            "current_pain_statement": {"type": "str", "required": False, "description": "Prospect'in su ana kadar ifade ettigi sikayet", "default": ""},
        },
        "outputs": {"pain_funnel_analysis": "{depth_analysis: str, quantified_pain_summary: str, next_questions: list[str]}"},
        "workflow": [
            "Mevcut aci ifadesinin hangi seviyede oldugunu (surface/impact/emotional) belirle.",
            "Sorunun is uzerindeki somut/sayisal etkisini cikarsamaya calis.",
            "Duygusal/kisisel etkiyi (kariyer riski, stres, itibar) tespit et.",
            "Bir sonraki seviyeye inmek icin nested acik uclu sorular oner.",
            "Bu asamada 'cozum satmaya' gecilmemesi gerektigini hatirlatan bir not ekle.",
            "Ciktiyi JSON formatinda, SADECE {\"pain_funnel_analysis\": {...}} semasina uygun dondur.",
        ],
    },

    # ================================================================
    # CDO (Aylin) skilleri - 2026-07-16 eklendi
    # ================================================================
    "data-governance-maturity-scan": {
        "name": "data-governance-maturity-scan",
        "owner_role": "cdo",
        "source": "DAMA-DMBOK (DAMA International)",
        "description": "DAMA-DMBOK'un 11 bilgi alanina gore bir veri alaninin/departmanin veri yonetisimi olgunlugunu degerlendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "domain_name": {"type": "str", "required": True, "description": "Degerlendirilecek veri alani/departman"},
            "current_practices": {"type": "str", "required": True, "description": "Mevcut veri yonetim pratiklerinin ozeti"},
            "known_pain_points": {"type": "list[str]", "required": False, "description": "Bilinen sorunlar", "default": []},
        },
        "outputs": {"maturity_analysis": "{summary: str, weak_areas: list[str], action_recommendations: list[str]}"},
        "workflow": [
            "Verilen alan adi, mevcut pratikler ve sorun noktalarini oku.",
            "DAMA-DMBOK'un 11 bilgi alanini (yonetisim, mimari, modelleme, depolama, guvenlik, entegrasyon, referans/master data, veri ambari/BI, meta veri, veri kalitesi, dokumanlar) referans al.",
            "Her alan icin mevcut pratikleri dusuk/orta/yuksek olgunluk seviyesinde yorumla.",
            "En kritik 3 zayif alani belirle ve somut sonraki adim oner.",
            "Ciktiyi JSON formatinda, SADECE {\"maturity_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "pipeline-dataops-readiness-review": {
        "name": "pipeline-dataops-readiness-review",
        "owner_role": "cdo",
        "source": "DataOps Manifesto (DataKitchen, 2017)",
        "description": "DataOps Manifesto ilkelerine gore bir veri pipeline'inin uretim kalitesini ve operasyonel olgunlugunu degerlendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "pipeline_name": {"type": "str", "required": True, "description": "Degerlendirilecek veri pipeline'inin adi"},
            "pipeline_description": {"type": "str", "required": True, "description": "Pipeline'in veri akisi, kaynaklari ve hedefleri"},
            "incident_history": {"type": "list[str]", "required": False, "description": "Son donemde yasanan veri kalitesi/kesinti olaylari", "default": []},
        },
        "outputs": {"dataops_analysis": "{readiness_verdict: str, improvement_plan: list[str]}"},
        "workflow": [
            "Pipeline aciklamasini ve olay gecmisini oku.",
            "DataOps ilkelerini (otomasyon, surekli test, izleme, reproduklenebilirlik) cerceve olarak kullan.",
            "Pipeline'daki manuel/kirilgan adimlari ve test/izleme bosluklarini tespit et.",
            "Otomasyon ve kalite kapilari icin onceliklendirilmis bir yol haritasi oner.",
            "Ciktiyi JSON formatinda, SADECE {\"dataops_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "data-science-project-scoping": {
        "name": "data-science-project-scoping",
        "owner_role": "cdo",
        "source": "CRISP-DM (Cross-Industry Standard Process for Data Mining, 1999)",
        "description": "CRISP-DM metodolojisine gore bir veri bilimi/analitik talebini 6 asamali yapilandirilmis proje planina donusturur.",
        "tools": ["ai-gateway"],
        "inputs": {
            "business_question": {"type": "str", "required": True, "description": "Cevaplanmak istenen is sorusu"},
            "available_data_sources": {"type": "list[str]", "required": True, "description": "Erisilebilir veri kaynaklari"},
            "constraints": {"type": "str", "required": False, "description": "Zaman, butce veya veri kisitlari", "default": ""},
        },
        "outputs": {"project_plan": "{stages: list[{stage: str, expected_output: str}], risk_flags: list[str]}"},
        "workflow": [
            "Is sorusunu ve mevcut veri kaynaklarini oku.",
            "CRISP-DM'in 6 asamasini (is anlayisi, veri anlayisi, veri hazirligi, modelleme, degerlendirme, devreye alma) cerceve olarak kullan.",
            "Is sorusunu olculebilir bir analitik hedefe cevir, veri kaynaklarinin yeterliligini degerlendir.",
            "Her asama icin beklenen cikti ve olasi riskleri listele.",
            "Ciktiyi JSON formatinda, SADECE {\"project_plan\": {...}} semasina uygun dondur.",
        ],
    },
    "data-product-quality-assessment": {
        "name": "data-product-quality-assessment",
        "owner_role": "cdo",
        "source": "Data Mesh (Zhamak Dehghani, Thoughtworks)",
        "description": "Data Mesh'in 4 ilkesine gore bir veri kumesini 'veri urunu' olarak degerlendirir ve sahiplik/kesfedilebilirlik eksiklerini ortaya cikarir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "dataset_name": {"type": "str", "required": True, "description": "Degerlendirilecek veri kumesi/veri urununun adi"},
            "owning_domain": {"type": "str", "required": True, "description": "Bu veriyi ureten is domaini/ekip"},
            "current_documentation": {"type": "str", "required": False, "description": "Mevcut sema/dokumantasyon/SLA bilgisi", "default": ""},
        },
        "outputs": {"data_product_analysis": "{readiness_score: str, gap_list: list[str]}"},
        "workflow": [
            "Veri kumesi, sahip domain, dokumantasyon ve bilinen tuketicileri oku.",
            "Data Mesh'in 4 ilkesini (domain sahipligi, veri-urun olarak ele alma, self-servis, federe yonetisim) cerceve olarak kullan.",
            "Veri kumesinin 'urun' standartlarini (kesfedilebilirlik, anlasilabilirlik, guvenilirlik) karsilayip karsilamadigini yorumla.",
            "Somut, onceliklendirilmis bir iyilestirme listesi sun.",
            "Ciktiyi JSON formatinda, SADECE {\"data_product_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "bi-reporting-request-triage": {
        "name": "bi-reporting-request-triage",
        "owner_role": "cdo",
        "source": "Kimball Enterprise Data Warehouse Bus Matrix (Ralph Kimball)",
        "description": "Kimball Bus Matrix mantigina gore yeni bir BI/raporlama talebini mevcut is surecleri ve conformed dimension'lara karsi konumlandirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "report_request": {"type": "str", "required": True, "description": "Talep edilen rapor/analiz ihtiyacinin aciklamasi"},
            "requesting_department": {"type": "str", "required": True, "description": "Talebi yapan departman/is sureci"},
            "existing_dimensions": {"type": "list[str]", "required": False, "description": "Halihazirda tanimli bilinen dimension'lar", "default": []},
        },
        "outputs": {"triage_analysis": "{placement_recommendation: str, new_vs_reuse_dimensions: str}"},
        "workflow": [
            "Rapor talebini, talep eden departmani ve mevcut dimension'lari oku.",
            "Kimball'in bus matrix mantigini (satir=is sureci, sutun=conformed dimension) cerceve olarak kullan.",
            "Talebin hangi is surecine karsilik geldigini belirle.",
            "Mevcut conformed dimension'larin yeniden kullanilip kullanilamayacagini degerlendir.",
            "Ciktiyi JSON formatinda, SADECE {\"triage_analysis\": {...}} semasina uygun dondur.",
        ],
    },

    # ================================================================
    # CTO (Kai) skill genisletmesi - 2026-07-16 eklendi (Fable5 arastirma
    # turu, mevcut 6 skille EK - kullanicinin "dunya klasi" talebi uzerine)
    # ================================================================
    "architecture-decision-record": {
        "name": "architecture-decision-record",
        "owner_role": "cto",
        "source": "Michael Nygard - 'Documenting Architecture Decisions' (2011, Cognitect); adr.github.io",
        "description": "Onemli bir mimari karari baglam, alternatifler ve sonuclariyla birlikte kalici, versiyonlanabilir bir kayda (ADR) donusturur.",
        "tools": ["ai-gateway"],
        "inputs": {
            "decision_title": {"type": "str", "required": True, "description": "Karar basligi (orn. 'Mesajlasma icin Kafka yerine NATS kullanimi')"},
            "context": {"type": "str", "required": True, "description": "Karari gerektiren teknik/is baglami ve kisitlar"},
            "options_considered": {"type": "list[str]", "required": False, "description": "Degerlendirilen alternatif cozumler", "default": []},
        },
        "outputs": {"adr_document": "{title: str, status: str, decision: str, consequences: list[str], alternatives_rejected: list[str]}"},
        "workflow": [
            "Baglami ve teknik/is kisitlarini netlestir.",
            "Degerlendirilen alternatifleri ve her birinin trade-off'larini listele.",
            "Nihai karari tek cumlede net sekilde ifade et.",
            "Kararin olumlu ve olumsuz sonuclarini acikca belirt.",
            "Nygard formatina uygun status (proposed/accepted/deprecated/superseded) ata.",
            "Ciktiyi JSON formatinda, SADECE {\"adr_document\": {...}} semasina uygun dondur.",
        ],
    },
    "c4-architecture-diagramming": {
        "name": "c4-architecture-diagramming",
        "owner_role": "cto",
        "source": "Simon Brown - 'The C4 Model for Visualising Software Architecture' (c4model.com)",
        "description": "Bir sistemi C4 modelinin seviyelerinde (Context, Container, Component) yapilandirilmis metin tanimina doker.",
        "tools": ["ai-gateway"],
        "inputs": {
            "system_name": {"type": "str", "required": True, "description": "Modellenecek sistemin adi"},
            "system_description": {"type": "str", "required": True, "description": "Sistemin amaci ve kapsami"},
            "known_components": {"type": "list[str]", "required": False, "description": "Bilinen servis/modul/container listesi", "default": []},
        },
        "outputs": {"c4_model": "{context_level: str, container_level: list[str], relationships: list[str]}"},
        "workflow": [
            "System Context seviyesinde sistemi, kullanicilarini ve dis sistem bagimliliklarini tanimla.",
            "Container seviyesinde uygulama/servis/veritabani sinirlarini ve iletisim protokollerini cikar.",
            "Her seviyede iliskileri (kim kime, hangi protokolle) etiketle.",
            "Notasyonun C4 standart sembollerine uygunlugunu doGrula.",
            "Ciktiyi JSON formatinda, SADECE {\"c4_model\": {...}} semasina uygun dondur.",
        ],
    },
    "team-topology-design": {
        "name": "team-topology-design",
        "owner_role": "cto",
        "source": "Matthew Skelton & Manuel Pais - 'Team Topologies' (IT Revolution Press)",
        "description": "Muhendislik organizasyonunu Team Topologies'in 4 takim tipi ve 3 etkilesim moduna gore tasarlar; bilissel yuku optimize eder.",
        "tools": ["ai-gateway"],
        "inputs": {
            "current_teams": {"type": "list[str]", "required": True, "description": "Mevcut ekiplerin adi ve sorumluluklari"},
            "value_streams": {"type": "list[str]", "required": True, "description": "Organizasyonun ana deger akislari/urun hatlari"},
            "known_bottlenecks": {"type": "list[str]", "required": False, "description": "Bilinen handoff/iletisim darbogazlari", "default": []},
        },
        "outputs": {"topology_plan": "{team_classification: list[str], interaction_modes: list[str], cognitive_load_risks: list[str]}"},
        "workflow": [
            "Her ekibi 4 tipten birine siniflandir: stream-aligned, platform, enabling, complicated-subsystem.",
            "Deger akislarina gore stream-aligned takimlarin sinirlarini netlestir.",
            "Takimlar arasi etkilesimleri 3 moda ata: collaboration, X-as-a-Service, facilitating.",
            "Asiri yuklenen takimlari (cognitive load) isaretle.",
            "Ciktiyi JSON formatinda, SADECE {\"topology_plan\": {...}} semasina uygun dondur.",
        ],
    },
    "dora-engineering-metrics-review": {
        "name": "dora-engineering-metrics-review",
        "owner_role": "cto",
        "source": "Forsgren, Humble, Kim - 'Accelerate' (IT Revolution, 2018); DORA Four Keys (dora.dev)",
        "description": "Muhendislik teslimat performansini DORA'nin dort anahtar metrigiyle (deployment frequency, lead time, MTTR, change failure rate) degerlendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "deployment_frequency": {"type": "str", "required": True, "description": "Dagitim sikligi"},
            "lead_time_for_changes": {"type": "str", "required": True, "description": "Commit'ten production'a gecis suresi"},
            "change_failure_rate": {"type": "str", "required": False, "description": "Dagitimlarin yuzde kaci incident'a yol aciyor", "default": ""},
        },
        "outputs": {"performance_assessment": "{performance_tier: str, weakest_metric: str, improvement_recommendations: list[str]}"},
        "workflow": [
            "Her metrigi DORA'nin Elite/High/Medium/Low bantlariyla karsilastir.",
            "Metrikleri birlikte yorumla (orn. yuksek frekans + yuksek hata orani riskli).",
            "En zayif metrigi ve kok nedenini belirle.",
            "Onceliklendirilmis iyilestirme adimlari oner.",
            "Ciktiyi JSON formatinda, SADECE {\"performance_assessment\": {...}} semasina uygun dondur.",
        ],
    },
    "wardley-mapping-tech-strategy": {
        "name": "wardley-mapping-tech-strategy",
        "owner_role": "cto",
        "source": "Simon Wardley - 'Wardley Maps' (CC-BY-SA, wardleymaps.com)",
        "description": "Teknoloji bilesenlerini evrim eksenine (Genesis-Custom-Product-Commodity) gore haritalayarak build-vs-buy stratejisi uretir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "user_need": {"type": "str", "required": True, "description": "Haritanin cikis noktasi olan temel kullanici ihtiyaci"},
            "value_chain_components": {"type": "list[str]", "required": True, "description": "Ihtiyaci karsilamak icin gereken bilesenler/yetenekler"},
        },
        "outputs": {"wardley_map": "{value_chain: list[str], strategic_recommendations: list[str]}"},
        "workflow": [
            "Kullanici ihtiyacindan baslayarak deger zincirini sirala.",
            "Her bileseni evrim eksenine yerlestir: Genesis, Custom-Built, Product/Rental, Commodity/Utility.",
            "Evrim asamasina gore build/buy/outsource/utility karari oner.",
            "Rakip hareketleri/pazar evrimi kaynakli riskleri isaretle.",
            "Ciktiyi JSON formatinda, SADECE {\"wardley_map\": {...}} semasina uygun dondur.",
        ],
    },

    # ================================================================
    # COO (Leo) skill genisletmesi - 2026-07-16 eklendi
    # ================================================================
    "eos-traction-cadence-review": {
        "name": "eos-traction-cadence-review",
        "owner_role": "coo",
        "source": "EOS (Entrepreneurial Operating System) - Gino Wickman, 'Traction: Get a Grip on Your Business'",
        "description": "Ceyrek hedefleri (Rocks), haftalik Scorecard metriklerini ve L10 toplanti IDS sonuclarini inceleyip yurutme momentumunu degerlendirir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "quarter_rocks": {"type": "list[str]", "required": True, "description": "Bu ceyrege ait Rock (oncelikli hedef) listesi ve durumlari"},
            "scorecard_metrics": {"type": "list[str]", "required": True, "description": "Haftalik izlenen sayisal gostergeler ve son degerleri"},
            "open_issues": {"type": "list[str]", "required": False, "description": "IDS listesine giren cozulmemis sorunlar", "default": []},
        },
        "outputs": {"cadence_health": "{on_track_pct: str, at_risk_rocks: list[str], top_issues: list[str], recommended_actions: list[str]}"},
        "workflow": [
            "Her Rock'in ilerleme yuzdesini ve tamamlanma riskini degerlendir.",
            "Scorecard metriklerinden esik disina cikanlari isaretle.",
            "Acik konulari IDS mantigiyla (Identify-Discuss-Solve) onceliklendir.",
            "Sahiplik bosluklarini/cakismalarini tespit et.",
            "Ciktiyi JSON formatinda, SADECE {\"cadence_health\": {...}} semasina uygun dondur.",
        ],
    },
    "theory-of-constraints-bottleneck-analysis": {
        "name": "theory-of-constraints-bottleneck-analysis",
        "owner_role": "coo",
        "source": "Theory of Constraints - Eliyahu M. Goldratt, 'The Goal'/'Critical Chain' (Theory of Constraints Institute)",
        "description": "Bes Odaklanma Adimi ile operasyondaki tek kisitlayici kaynagi (bottleneck) tespit eder ve kapasite/verim onerileri sunar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "process_stages": {"type": "list[str]", "required": True, "description": "Surecteki sirali asamalar/kaynaklar ve kapasiteleri"},
            "throughput_data": {"type": "list[str]", "required": True, "description": "Her asamanin birim zamanda cikti/is hacmi verisi"},
        },
        "outputs": {"constraint_analysis": "{bottleneck_stage: str, exploit_actions: list[str], subordinate_actions: list[str], elevate_options: list[str]}"},
        "workflow": [
            "Surec asamalarini throughput verisiyle karsilastirarak sistemin tek kisitini tespit et (Identify).",
            "Kisiti maksimum verimle kullanmak icin hizli onlemleri belirle (Exploit).",
            "Diger tum asamalari kisitin hizina gore yeniden duzenle (Subordinate).",
            "Kisit hala darbogazsa yatirim/kapasite secenekleri oner (Elevate).",
            "Ciktiyi JSON formatinda, SADECE {\"constraint_analysis\": {...}} semasina uygun dondur.",
        ],
    },
    "rapid-decision-rights-mapping": {
        "name": "rapid-decision-rights-mapping",
        "owner_role": "coo",
        "source": "RAPID Decision-Making Framework - Bain & Company (Paul Rogers & Marcia Blenko)",
        "description": "Karmasik bir operasyonel karar icin Recommend-Agree-Perform-Input-Decide rollerini netlestirip karar tikanikliklarini onler.",
        "tools": ["ai-gateway"],
        "inputs": {
            "decision_description": {"type": "str", "required": True, "description": "Netlestirilmesi gereken karar/inisiyatif"},
            "stakeholders": {"type": "list[str]", "required": True, "description": "Karara dahil olan roller/departmanlar"},
        },
        "outputs": {"rapid_matrix": "{recommend: str, agree: list[str], perform: list[str], input: list[str], decide: str, ambiguous_roles: list[str]}"},
        "workflow": [
            "Karari netlestir ve kapsamini tanimla.",
            "Her paydasi R-A-P-I-D rollerinden birine ata, birden fazla role atananlari isaretle.",
            "Agree (veto) rolunu sadece politika/uyum temelli kisitlarla sinirla.",
            "Tek bir Decide sahibi oldugunu dogrula.",
            "Ciktiyi JSON formatinda, SADECE {\"rapid_matrix\": {...}} semasina uygun dondur.",
        ],
    },
    "dmaic-process-improvement-cycle": {
        "name": "dmaic-process-improvement-cycle",
        "owner_role": "coo",
        "source": "Lean Six Sigma DMAIC - Motorola/GE Six Sigma metodolojisi (Lean Enterprise Institute)",
        "description": "Define-Measure-Analyze-Improve-Control donguSuyle bir operasyonel sureci sistematik olarak analiz edip iyilestirme plani cikarir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "process_name": {"type": "str", "required": True, "description": "Iyilestirilecek surecin adi ve kapsami"},
            "defect_or_waste_data": {"type": "list[str]", "required": True, "description": "Hata orani, gecikme, yeniden isleme gibi olcum verileri"},
        },
        "outputs": {"dmaic_report": "{define: str, measure: str, analyze: str, improve_actions: list[str], monitoring_metrics: list[str]}"},
        "workflow": [
            "Define: sureci ve iyilestirme hedefini net tanimla.",
            "Measure: mevcut performans verisini ozetle, baseline olustur.",
            "Analyze: kok neden analizi (5 Neden) ile ana etkenleri belirle.",
            "Improve: onceliklendirilmis iyilestirme aksiyonlarini oner.",
            "Control: kazanimlarin kalicilastirilmasi icin izleme metrikleri tanimla.",
            "Ciktiyi JSON formatinda, SADECE {\"dmaic_report\": {...}} semasina uygun dondur.",
        ],
    },
    "hoshin-kanri-policy-deployment": {
        "name": "hoshin-kanri-policy-deployment",
        "owner_role": "coo",
        "source": "Hoshin Kanri (Policy Deployment) - Japon TQM gelenegi / Yoji Akao, X-Matrix metodolojisi",
        "description": "Uzun vadeli sirket stratejisini departman duzeyinde yillik hedeflere ve kaynak tahsisine baglayan X-Matrix hizalama analizi yapar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "company_strategic_goals": {"type": "list[str]", "required": True, "description": "3-5 yillik ust duzey stratejik hedefler"},
            "annual_department_objectives": {"type": "list[str]", "required": True, "description": "Departmanlarin bu yilki hedefleri"},
        },
        "outputs": {"alignment_matrix": "{strategy_to_objective_gaps: list[str], unaligned_departments: list[str], reallocation_suggestions: list[str]}"},
        "workflow": [
            "Ust duzey stratejik hedefleri departman yillik hedefleriyle eslestir.",
            "Hedefsiz kalan stratejileri veya bagsiz departman hedeflerini isaretle.",
            "KPI'larin stratejik hedeflerle olculebilir baglantisini dogrula.",
            "Kaynak tahsisinin en yuksek etkili hedeflere gore dagilip dagilmadigini degerlendir.",
            "Ciktiyi JSON formatinda, SADECE {\"alignment_matrix\": {...}} semasina uygun dondur.",
        ],
    },

    # ================================================================
    # CISO (Nora) skill genisletmesi - 2026-07-16 eklendi
    # ================================================================
    "nist-csf-maturity-assessment": {
        "name": "nist-csf-maturity-assessment",
        "owner_role": "ciso",
        "source": "NIST Cybersecurity Framework 2.0 (NIST, Subat 2024)",
        "description": "Kurumun siber guvenlik olgunlugunu NIST CSF 2.0'in 6 fonksiyonuna (Govern dahil) gore degerlendirir, bosluklari raporlar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "org_context": {"type": "str", "required": True, "description": "Degerlendirilecek birim/sistemin kisa tanimi"},
            "current_controls": {"type": "list[str]", "required": True, "description": "Mevcut bilinen guvenlik kontrolleri listesi"},
            "target_tier": {"type": "str", "required": False, "description": "Hedef olgunluk seviyesi", "default": "Repeatable"},
        },
        "outputs": {"maturity_scorecard": "{per_function: list[str], gaps: list[str]}", "priority_roadmap": "{summary: str, actions: list[str]}"},
        "workflow": [
            "org_context ve current_controls'u NIST CSF 2.0'in 6 fonksiyonuna (Govern, Identify, Protect, Detect, Respond, Recover) esle.",
            "Her fonksiyon icin mevcut olgunluk seviyesini tahmin et.",
            "target_tier ile mevcut durum arasindaki bosluklari listele.",
            "Onceliklendirilmis bir aksiyon yol haritasi olustur.",
            "Ciktiyi JSON formatinda, SADECE {\"maturity_scorecard\": {...}, \"priority_roadmap\": {...}} semasina uygun dondur.",
        ],
    },
    "iso27001-gap-analysis": {
        "name": "iso27001-gap-analysis",
        "owner_role": "ciso",
        "source": "ISO/IEC 27001:2022 Bilgi Guvenligi Yonetim Sistemi (ISMS) standardi - Annex A kontrolleri",
        "description": "Kurumun mevcut politika ve kontrollerini ISO/IEC 27001:2022 Annex A kontrol setine karsi denetler, sertifikasyona hazirlik boslugu raporlar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "policy_documents": {"type": "list[str]", "required": True, "description": "Mevcut guvenlik politikalarinin ozet metinleri/basliklari"},
            "annex_a_scope": {"type": "list[str]", "required": False, "description": "Odaklanilacak Annex A kontrol kategorileri", "default": []},
        },
        "outputs": {"gap_report": "list[{control: str, status: str, evidence_needed: str}]", "readiness_summary": "{readiness_pct: str, summary: str}"},
        "workflow": [
            "policy_documents'i ISO/IEC 27001:2022 Annex A kontrol kategorileriyle eslestir.",
            "Her kontrol icin kapsanma durumunu (covered/partial/missing) belirle.",
            "Eksik kontroller icin gereken kanit/dokumantasyon turunu oner.",
            "Genel sertifikasyon hazirlik yuzdesini hesapla.",
            "Ciktiyi JSON formatinda, SADECE {\"gap_report\": [...], \"readiness_summary\": {...}} semasina uygun dondur.",
        ],
    },
    "fair-quantitative-risk-analysis": {
        "name": "fair-quantitative-risk-analysis",
        "owner_role": "ciso",
        "source": "FAIR (Factor Analysis of Information Risk) - The Open Group O-RA / FAIR Institute (Freund & Jones)",
        "description": "Belirli bir siber riski FAIR metodolojisiyle parasal terimlerle (beklenen kayip araligi) nicel olarak modeller.",
        "tools": ["ai-gateway"],
        "inputs": {
            "risk_scenario": {"type": "str", "required": True, "description": "Analiz edilecek risk senaryosu"},
            "existing_controls": {"type": "list[str]", "required": True, "description": "Senaryoya karsi mevcut kontroller"},
            "asset_value_estimate": {"type": "str", "required": False, "description": "Etkilenen varligin tahmini degeri", "default": ""},
        },
        "outputs": {"loss_exceedance_estimate": "{annualized_loss_low: str, annualized_loss_high: str, primary_loss_factors: list[str]}", "board_summary": "{summary: str, recommendation: str}"},
        "workflow": [
            "risk_scenario'yu FAIR taksonomisine gore ayristir: Threat Event Frequency ve Loss Magnitude.",
            "existing_controls'u kullanarak Vulnerability ve Contact Frequency tahminleri yap.",
            "Birincil ve ikincil kayip bilesenlerini hesapla.",
            "Minimum-en olasi-maksimum tahminle yillik kayip araligini modelle.",
            "Sonuclari yonetim kurulu diline cevir.",
            "Ciktiyi JSON formatinda, SADECE {\"loss_exceedance_estimate\": {...}, \"board_summary\": {...}} semasina uygun dondur.",
        ],
    },
    "zero-trust-architecture-review": {
        "name": "zero-trust-architecture-review",
        "owner_role": "ciso",
        "source": "NIST SP 800-207, Zero Trust Architecture (NIST, Agustos 2020)",
        "description": "Bir sistem/ag mimarisini NIST SP 800-207 Zero Trust ilkelerine gore degerlendirir ve gecis plani onerir.",
        "tools": ["ai-gateway"],
        "inputs": {
            "system_architecture": {"type": "str", "required": True, "description": "Mevcut ag/erisim mimarisinin ozeti"},
            "sensitive_resources": {"type": "list[str]", "required": True, "description": "Korunmasi gereken kritik kaynaklar/veri setleri"},
        },
        "outputs": {"zt_gap_assessment": "list[{principle: str, current_state: str, gap: str}]", "migration_plan": "{summary: str, phased_steps: list[str]}"},
        "workflow": [
            "system_architecture'i NIST SP 800-207'deki Zero Trust temel ilkelerine gore haritalya.",
            "Kimlik dogrulama/yetkilendirme yeterliligini degerlendir (MFA, surekli dogrulama).",
            "sensitive_resources icin mikro-segmentasyon/en az ayricalik uygulanabilirligini kontrol et.",
            "Her ilke icin mevcut durum-hedef durum boslugunu belirle.",
            "Asamali bir gecis plani olustur.",
            "Ciktiyi JSON formatinda, SADECE {\"zt_gap_assessment\": [...], \"migration_plan\": {...}} semasina uygun dondur.",
        ],
    },
    "ssdf-secure-supply-chain-review": {
        "name": "ssdf-secure-supply-chain-review",
        "owner_role": "ciso",
        "source": "NIST SP 800-218, Secure Software Development Framework (SSDF) v1.1",
        "description": "Yazilim gelistirme yasam donguSunu NIST SSDF'nin 4 pratik grubuna gore denetler, tedarik zinciri guvenlik aciklarini raporlar.",
        "tools": ["ai-gateway"],
        "inputs": {
            "sdlc_description": {"type": "str", "required": True, "description": "Yazilim gelistirme surecinin ozeti (CI/CD, bagimlilik yonetimi vb.)"},
            "third_party_dependencies": {"type": "list[str]", "required": False, "description": "Kullanilan ucuncu taraf kutuphane/servis listesi", "default": []},
        },
        "outputs": {"ssdf_practice_coverage": "list[{practice_group: str, status: str}]", "supply_chain_risks": "{summary: str, critical_findings: list[str]}"},
        "workflow": [
            "sdlc_description'i SSDF'in 4 pratik grubuna (Prepare, Protect, Produce, Respond) gore ayristir.",
            "third_party_dependencies icin SBOM ve bagimlilik tarama sureclerinin varligini kontrol et.",
            "Her pratik grubu icin kapsanma durumunu belirle.",
            "Kritik tedarik zinciri risklerini onceliklendir.",
            "Ciktiyi JSON formatinda, SADECE {\"ssdf_practice_coverage\": [...], \"supply_chain_risks\": {...}} semasina uygun dondur.",
        ],
    },
}

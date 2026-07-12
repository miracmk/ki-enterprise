"""
KI Enterprise Event Bus - JetStream stream tanimlari.

Subject hiyerarsisi (bkz. Build Order Phase 1):
  company.*      - sirket geneli olaylar
  department.*   - departman olaylari
  project.*      - proje olaylari
  worker.*       - worker olaylari
  task.*         - gorev atama/dagitim (orn: task.research, task.developer, task.marketing)
  report.*       - departmanlardan gelen raporlar (orn: report.research, report.developer)
"""

STREAM_DEFINITIONS = [
    {"name": "COMPANY", "subjects": ["company.>"]},
    {"name": "DEPARTMENT", "subjects": ["department.>"]},
    {"name": "PROJECT", "subjects": ["project.>"]},
    {"name": "WORKER", "subjects": ["worker.>"]},
    {"name": "TASK", "subjects": ["task.>"]},
    {"name": "REPORT", "subjects": ["report.>"]},
]

# Stream'ler icin ortak retention ayarlari
DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 gun
DEFAULT_MAX_MSGS = 1_000_000

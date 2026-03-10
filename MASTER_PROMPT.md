# Master Prompt — dieu-preuves.fr
<!-- Les agents lisent ce fichier EN PREMIER à chaque run. -->
<!-- Format des tâches : "- [ ] TASK-XXX : description" -->
<!-- Une fois faite, la case est cochée automatiquement : "- [x] TASK-XXX : description" -->
<!-- Les tâches complétées sont également loggées dans agents/memory/task_log.json -->

## Instructions générales pour les agents

Tu travailles sur le site **dieu-preuves.fr**, un site apologétique chrétien francophone dont la mission
est de présenter les preuves de l'existence de Dieu de manière rigoureuse, sourcée et accessible.

**Priorités absolues à chaque run :**
1. Lire les tâches ci-dessous et les exécuter dans l'ordre
2. Enrichir le contenu avec des citations réelles issues des transcripts vidéo
3. Améliorer le référencement SEO et l'accessibilité
4. Maintenir la cohérence du design (thème sombre, palette or/bleu)
5. Ne jamais retirer du contenu existant sans le remplacer par mieux

**Contexte des vidéos disponibles :**
- ZWzys1gojtA : Débat Guénolé vs Bonnassies (2h, FR)
- otrqzITuSqE : Prof. John Lennox, Oxford Union (13min, EN)
- fYgRGBczRHk : Lavagna & Frère Paul-Adrien — 3 preuves (40min, FR)
- 7IA4XriGeZY : Abbé Raffray & Lavagna — Aquinas (38min, FR)
- ZiNRN20tEQI : Le Catho de Service — 100 raisons (50min, FR)
- UnaAFhybsDk : Lavagna — Jésus historique (30min, FR)
- TSZXlVF-qVI : Dr. Willie Soon — Mathématiques (8min, EN)

---

## Tâches prioritaires

- [ ] TASK-001 : Extraire les citations clés avec timestamps de tous les transcripts et enrichir _data/videos.yml
- [ ] TASK-002 : Décomposer index.html en includes Jekyll (_includes/section-*.html)
- [ ] TASK-003 : Ajouter les citations de John Lennox (0:02:10 et 0:03:19) dans la section fine-tuning
- [ ] TASK-004 : Ajouter les 5 faits historiques de Lavagna sur la résurrection (0:03:03) dans la section histoire
- [ ] TASK-005 : Ajouter le timestamp 0:12:30 du débat Bonnassies (10^123, Penrose) dans la section science
- [ ] TASK-006 : Ajouter Schema.org FAQPage pour les objections principales
- [ ] TASK-007 : Ajouter un skip link d'accessibilité "Aller au contenu"
- [ ] TASK-008 : Créer _includes/section-videos.html avec timestamps cliquables pour chaque vidéo
- [ ] TASK-009 : Enrichir _data/arguments.yml avec les citations de Willie Soon sur les mathématiques (0:00:58)
- [ ] TASK-010 : Générer CHANGELOG.md avec l'historique des améliorations par les agents

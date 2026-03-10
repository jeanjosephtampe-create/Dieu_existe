# REQUIREMENTS — dieu-preuves.fr
<!-- Fichier lu par l'agent RequirementsChecker ET les agents builders. -->
<!-- Format : chaque exigence est une ligne commençant par "- [ ]" (à faire) ou "- [x]" (fait). -->
<!-- L'agent vérifie automatiquement le statut réel dans le code. -->

## Mission : prouver l'existence de Dieu de manière rigoureuse, sourcée et accessible

> Site apologétique francophone de référence. Chaque argument est sourcé sur des vidéos réelles,
> des transcripts vérifiés et des citations de philosophes/scientifiques identifiés.
> À chaque lancement des agents, le site est amélioré automatiquement.

---

## 1. Mission & Contenu

### 1.1 Arguments couverts
- [x] Argument cosmologique (Kalam) — BGV theorem, principe de raison suffisante
- [x] Argument du réglage fin (Fine-tuning) — constantes universelles, probabilité 10^-123
- [x] Argument ontologique (Anselme, Plantinga)
- [x] Argument de la contingence (Aquinas III)
- [x] Argument moral (C.S. Lewis, W.L. Craig)
- [x] Preuve mathématique (équation de Dirac, géométrie de Calabi-Yau)
- [x] Preuves historiques de la résurrection (5 faits, Lavagna)
- [x] Historicité de Jésus (Tacite, Josèphe, réfutation Onfray)
- [ ] Argument de la conscience (hard problem, David Chalmers)
- [ ] Argument téléologique (design fins naturels, Aquinas V)
- [ ] Miracles documentés (Turin, Fatima, Lourdes) avec sources vérifiables

### 1.2 Citations & Sources
- [x] Chaque argument cite au moins une source académique (Stanford Encyclopedia, Aquinas, etc.)
- [ ] Chaque argument cite au moins un extrait de transcript vidéo avec timestamp précis
- [ ] Citations en français et en anglais (Lennox, Craig, Penrose)
- [ ] Chaque citation identifie clairement l'auteur, la vidéo et le moment (ex: Lennox, 0:03:19)
- [ ] Sources académiques : DOI ou URL stable quand disponible

### 1.3 Vidéos intégrées
- [x] 8 vidéos YouTube intégrées avec thumbnail click-to-play
- [ ] Chaque vidéo a au moins 3 timestamps vers des moments clés (pas seulement le début)
- [ ] Chaque moment clé a une citation transcrite du passage correspondant
- [ ] Descriptions enrichies des vidéos (pas seulement le titre)
- [ ] Vidéos en anglais signalées comme EN

### 1.4 Rigueur intellectuelle
- [ ] Chaque argument présente l'objection principale ET la réponse
- [ ] Distinction claire entre preuve philosophique et acte de foi
- [ ] Les probabilités et chiffres sont sourcés (Penrose 10^123, ADN 44 000 milliards)
- [ ] Aucune affirmation sans source identifiable

---

## 2. Architecture & Code

### 2.1 Jekyll (GitHub Pages)
- [x] Site statique Jekyll hébergé sur GitHub Pages
- [x] `_config.yml` correctement configuré (url, plugins SEO, sitemap)
- [x] `Gemfile` avec plugins GitHub Pages
- [ ] `index.html` décomposé en includes Jekyll (`_includes/section-*.html`)
- [ ] `_data/videos.yml` enrichi avec timestamps précis et citations
- [ ] `_data/arguments.yml` enrichi avec citations de transcripts
- [ ] `_data/sources.yml` complet avec toutes les sources citées
- [x] CNAME configuré pour dieu-preuves.fr

### 2.2 Équipe d'agents IA
- [x] `TranscriptMinerAgent` : extrait citations + timestamps des 9 transcripts
- [x] `ContentBuilderAgent` : génère les includes HTML enrichis
- [x] `CodeReviewerAgent` : vérifie la qualité du code HTML/CSS/JS
- [x] `UIUXAgent` : vérifie l'accessibilité et le responsive
- [x] `SEOExpertAgent` : optimise le référencement
- [x] `RequirementsCheckerAgent` : vérifie la conformité à ce fichier
- [x] Orchestrateur avec git push automatique sur branche `improvements/`
- [x] `MASTER_PROMPT.md` : directives prioritaires lues à chaque run
- [x] `agents/memory/task_log.json` : mémoire persistante des tâches exécutées

### 2.3 One-pager Jekyll structuré
- [x] Navigation fixe avec ancres par section
- [x] Menu hamburger mobile (breakpoint 900px)
- [ ] `_includes/head.html` avec tous les meta tags SEO
- [ ] `_includes/hero.html` — section d'accueil
- [ ] `_includes/section-philosophie.html`
- [ ] `_includes/section-science.html`
- [ ] `_includes/section-histoire.html`
- [ ] `_includes/section-videos.html` avec timestamps enrichis
- [ ] `_includes/section-scientists.html`
- [ ] `_includes/section-sources.html`

---

## 3. SEO & Performance

### 3.1 Meta tags
- [x] `<title>` avec mots-clés (55-60 caractères)
- [x] `<meta name="description">` (150-160 caractères)
- [x] Open Graph (og:title, og:description, og:image, og:url)
- [x] Twitter Card
- [x] `<link rel="canonical">`
- [ ] OG image 1200×630px hébergée sur le domaine

### 3.2 Schema.org
- [x] `WebSite` Schema
- [ ] `FAQPage` Schema pour les questions/objections
- [ ] `VideoObject` Schema pour chaque vidéo intégrée
- [ ] `Person` Schema pour les auteurs cités (Lennox, Craig, Lavagna)

### 3.3 Performance
- [x] Images lazy-loading
- [x] YouTube nocookie embed
- [ ] Lighthouse Performance ≥ 90
- [ ] Lighthouse Accessibility ≥ 90
- [ ] Lighthouse SEO ≥ 95

### 3.4 Mots-clés cibles
- [ ] "preuve existence Dieu" (volume FR élevé)
- [ ] "argument cosmologique Kalam"
- [ ] "fine-tuning univers"
- [ ] "preuve résurrection historique"
- [ ] "Lennox Dieu existe"
- [ ] "apologétique chrétienne francophone"

---

## 4. Accessibilité & UX

### 4.1 WCAG 2.1 AA
- [x] Navigation au clavier
- [x] Labels ARIA sur les éléments interactifs
- [ ] Ratio de contraste ≥ 4.5:1 pour le texte normal
- [ ] Skip link "Aller au contenu"
- [ ] Focus visible sur tous les éléments interactifs (`:focus-visible`)
- [ ] Alternatives textuelles sur toutes les images

### 4.2 Responsive
- [x] Mobile-first (breakpoint 900px)
- [x] Menu hamburger fonctionnel
- [ ] Pas de scroll horizontal sur mobile

### 4.3 Vidéos
- [x] Modal vidéo avec fermeture Escape
- [ ] Timestamps cliquables directement dans le texte
- [ ] Lecteur vidéo responsive
- [ ] Chaque vidéo a un titre descriptif

---

## 5. Sécurité & Déploiement

- [x] Liens externes avec `rel="noopener noreferrer"`
- [x] GitHub Pages deployment depuis branche Jekyll
- [x] `.gitignore` : exclut `_site/`, `__pycache__/`, `agents/reports/`
- [ ] Pas de clé API dans les fichiers commités

---

## 6. Agents — Règles d'amélioration continue

- [x] Agents lisent `MASTER_PROMPT.md` en priorité à chaque run
- [x] Tâches complétées cochées dans `MASTER_PROMPT.md` + loggées dans `agents/memory/task_log.json`
- [x] Agents ne répètent pas une tâche déjà cochée (vérification via task_log)
- [x] Chaque run committé sur une branche `improvements/YYYYMMDD-HHMMSS`
- [ ] Rapport de run accessible dans `agents/reports/`

---

## 7. Maintenabilité

- [x] `README.md` avec instructions de lancement
- [x] Données séparées du HTML (YAML data files)
- [ ] `CHANGELOG.md` auto-généré par les agents à chaque run
- [x] Variables CSS (`--accent`, `--bg`, etc.) pour la cohérence du design

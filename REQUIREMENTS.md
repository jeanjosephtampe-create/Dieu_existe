# Exigences du projet — dieu-preuves.fr
<!-- Fichier lu par l'agent RequirementsChecker. -->
<!-- Format : chaque exigence est une ligne commençant par "- [ ]" (à faire) ou "- [x]" (fait). -->
<!-- L'agent vérifie automatiquement le statut réel dans le code. -->

## 1. Technique & Déploiement

### 1.1 Infrastructure
- [x] Hébergé sur GitHub Pages avec Jekyll
- [x] Compatible Jekyll 3.x (plugins supportés par GitHub Pages)
- [x] Gemfile présent avec jekyll-seo-tag, jekyll-sitemap, jekyll-feed
- [ ] Image OG créée (1200×630px) → `assets/img/og-image.jpg`
- [ ] Soumission sitemap à Google Search Console
- [ ] DNS configuré vers Hostinger pour dieu-preuves.fr

### 1.2 Performance
- [x] Lazy loading des thumbnails YouTube via IntersectionObserver
- [x] Preconnect vers YouTube et dns-prefetch vers Google Fonts
- [ ] Score Lighthouse Performance ≥ 90
- [ ] Score Lighthouse Accessibility ≥ 90
- [ ] Pas de ressources bloquant le rendu (CSS non critique en async)
- [ ] Images compressées (WebP si possible)

### 1.3 Compatibilité navigateurs
- [x] JavaScript sans framework (vanilla JS)
- [x] Fallback pour les navigateurs sans IntersectionObserver
- [ ] Testé sur Chrome, Firefox, Safari, Edge
- [ ] Testé sur iOS Safari et Android Chrome

## 2. SEO & Référencement

### 2.1 Balises méta
- [x] Balise <title> présente et optimisée
- [x] Meta description (150-160 caractères)
- [x] Balises Open Graph (og:title, og:description, og:image, og:url)
- [x] Twitter Card (summary_large_image)
- [x] Langue définie (lang="fr")
- [x] Canonical link dans le layout
- [x] robots.txt présent

### 2.2 Données structurées Schema.org
- [x] Schema.org WebSite avec SearchAction
- [x] Schema.org FAQPage (5 questions minimum)
- [x] Schema.org BreadcrumbList
- [ ] Schema.org Article sur chaque carte d'argument
- [ ] Schema.org Person pour les scientifiques cités
- [ ] Schema.org VideoObject pour les vidéos YouTube

### 2.3 Contenu
- [x] Sitemap XML généré automatiquement
- [x] Mots-clés ciblés dans les titres (Kalam, fine-tuning, etc.)
- [ ] Blog/articles pour le SEO longue traîne
- [ ] Liens internes entre les sections
- [ ] Textes alternatifs optimisés pour le SEO sur toutes les images

## 3. Accessibilité (WCAG 2.1 niveau AA)

- [x] Navigation clavier fonctionnelle
- [x] Attributs aria-label sur les éléments interactifs
- [x] Rôles ARIA définis (role="navigation", etc.)
- [x] Lien "retour en haut" avec aria-label
- [ ] Ratio de contraste ≥ 4.5:1 pour le texte normal
- [ ] Ratio de contraste ≥ 3:1 pour le texte large
- [ ] Focus visible sur tous les éléments interactifs
- [ ] Skip navigation link (lien "passer au contenu")
- [ ] Pas de contenu animé qui clignote > 3 fois/seconde
- [ ] Toutes les images ont un attribut alt

## 4. UI/UX & Design

### 4.1 Design général
- [x] Design sombre (dark mode natif)
- [x] Police lisible et hiérarchie typographique claire
- [x] Barre de progression de lecture
- [x] Animation d'entrée des cartes (IntersectionObserver)
- [ ] Mode clair disponible (respect de prefers-color-scheme)
- [ ] Typographie responsive (clamp() ou vw)

### 4.2 Navigation
- [x] Navigation fixe en haut avec highlight de section active
- [x] Menu mobile avec hamburger
- [ ] Fil d'Ariane visible (breadcrumb)
- [ ] Recherche dans la page
- [ ] Table des matières sticky sur desktop

### 4.3 Composants
- [x] Cartes d'arguments avec collapsible
- [x] Cartes vidéo avec lazy loading
- [x] Modale vidéo (fermeture clavier, backdrop, Escape)
- [x] Section savants/scientifiques
- [ ] Bouton "Partager" par section (native Web Share API)
- [ ] Système de notation/feedback par argument
- [ ] Copier le lien d'une section (permalink)

## 5. Contenu

### 5.1 Arguments présents
- [x] Argument cosmologique de Kalam
- [x] Fine-tuning / réglage fin de l'univers
- [x] Théorème BGV (Borde-Guth-Vilenkin)
- [x] Argument ontologique
- [x] Argument moral (C.S. Lewis / W.L. Craig)
- [x] Argument de la conscience
- [x] Historicité de Jésus
- [x] Résurrection — critères d'historicité
- [ ] Argument de l'information (ADN)
- [ ] Argument de la complexité irréductible (Behe)
- [ ] Argument de l'expérience religieuse

### 5.2 Qualité du contenu
- [x] Sources académiques citées (Tacite, Josèphe, Physical Review Letters, etc.)
- [x] Vidéos de référence intégrées (Lennox, Bonnassies, etc.)
- [x] Section savants croyants (scientifiques contemporains)
- [ ] Références bibliographiques complètes (auteur, titre, éditeur, année)
- [ ] Système de mise à jour du contenu documenté
- [ ] Traduction anglaise disponible

## 6. Sécurité

- [x] rel="noopener noreferrer" sur tous les liens externes
- [x] YouTube Nocookie utilisé (youtube-nocookie.com)
- [x] Pas de données utilisateur collectées
- [ ] Content Security Policy (CSP) header configuré
- [ ] Subresource Integrity (SRI) sur les ressources externes
- [ ] Pas de cookies tiers (vérifier avec les outils développeurs)

## 7. Maintenabilité

- [x] Contenu séparé du code (fichiers _data/)
- [x] Composants réutilisables (_includes/)
- [x] README documenté avec procédures
- [ ] CHANGELOG maintenu à jour
- [ ] Tests automatisés pour les agents IA (✅ créés)
- [ ] CI/CD avec GitHub Actions (lint, build, tests)
- [ ] Variables de configuration centralisées dans _config.yml

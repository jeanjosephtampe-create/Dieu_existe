# Dieu Existe — Les Preuves
## Architecture Jekyll pour GitHub Pages

### Structure du projet

```
dieu-preuves/
├── _config.yml              ← Configuration site + SEO
├── _data/
│   ├── arguments.yml        ← ⭐ MODIFIER LES ARGUMENTS ICI
│   ├── videos.yml           ← ⭐ MODIFIER LES VIDÉOS ICI
│   ├── scientists.yml       ← ⭐ MODIFIER LES SAVANTS ICI
│   └── sources.yml          ← ⭐ MODIFIER LES SOURCES ICI
├── _includes/
│   ├── nav.html             ← Navigation (réutilisable)
│   ├── footer.html          ← Pied de page
│   ├── section-header.html  ← En-tête de section
│   ├── arg-card.html        ← Carte d'argument (composant)
│   ├── video-card.html      ← Carte vidéo (avec lazy loading)
│   └── video-modal.html     ← Modale vidéo
├── _layouts/
│   └── default.html         ← Layout principal (SEO complet)
├── assets/
│   ├── css/main.css         ← Tous les styles
│   └── js/main.js           ← Tout le JavaScript
├── index.html               ← Page principale
├── robots.txt               ← SEO
└── Gemfile                  ← Dépendances Ruby/Jekyll
```

---

### Déploiement sur GitHub Pages

1. **Cloner/Uploader** tous ces fichiers dans ton repo GitHub (à la racine)
2. Aller dans **Settings → Pages**
3. Source : **Deploy from a branch** → `main` → `/ (root)`
4. GitHub Pages compilera Jekyll automatiquement ✅

### Ajouter un argument

Ouvrir `_data/arguments.yml`, trouver la section voulue, ajouter :

```yaml
- icon: "🔭"
  title: "Titre de l'argument"
  body: |
    Corps de l'argument en markdown.
  source_text: "Auteur, Titre, Année."
  source_url: "https://..."
  source_link_label: "Voir la source"
  video_id: YOUTUBE_ID
  video_start: 0
  video_label: "Description de la vidéo (0:00)"
```

### Ajouter une vidéo

Ouvrir `_data/videos.yml`, ajouter dans `featured:` :

```yaml
- id: YOUTUBE_VIDEO_ID
  title: "Titre de la vidéo"
  author: "Auteur · Chaîne"
```

Et dans `titles:` ajouter :
```yaml
YOUTUBE_VIDEO_ID: "Titre pour la modale"
```

### Ajouter un savant

Ouvrir `_data/scientists.yml`, ajouter :
```yaml
- name: Nom Prénom
  field: Domaine scientifique
  faith: Croyance
```

### Ajouter une source

Ouvrir `_data/sources.yml`, trouver la catégorie, ajouter :
```yaml
- num: "31"
  text: "Auteur (Année). <em>Titre</em>. Éditeur."
  url: "https://..."
  link_label: "Lien"
```

---

### Améliorations SEO incluses

| Fonctionnalité | Statut |
|---|---|
| Sitemap.xml automatique | ✅ jekyll-sitemap |
| Balises SEO meta | ✅ jekyll-seo-tag |
| Schema.org FAQPage | ✅ 5 questions/réponses |
| Schema.org WebSite + SearchAction | ✅ |
| Schema.org BreadcrumbList | ✅ |
| Schema.org Article (cartes) | ✅ |
| robots.txt | ✅ |
| Canonical links | ✅ |
| Open Graph complet | ✅ |
| Twitter Card | ✅ |
| Lazy loading images YouTube | ✅ IntersectionObserver |
| Preconnect YouTube | ✅ |
| Attributs aria (accessibilité) | ✅ |
| `rel="noopener"` sur liens externes | ✅ |
| `<blockquote>` + `<cite>` sémantiques | ✅ |
| `<ol>` pour la liste des faits | ✅ |
| `role` et `aria-label` | ✅ |

### À faire manuellement

- [ ] Créer une image OG (1200×630px) et la placer dans `assets/img/og-image.jpg`
- [ ] Vérifier ton site dans Google Search Console
- [ ] Soumettre le sitemap : `https://dieu-preuves.fr/sitemap.xml`
- [ ] Activer le DNS vers Hostinger (pas de changement nécessaire côté code)

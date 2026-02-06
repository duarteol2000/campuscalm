# CampusCalm Home - Arquivo de Mudanças e Código

Este arquivo contém o código completo da Home institucional (HTML + CSS), além dos trechos necessários para ligar a rota e a view no Django.

## 1) Template HTML

```html
{% load static %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CampusCalm | Algorithm Insights Sistemas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'css/home.css' %}">
</head>
<body>
  <div class="page-shell">
    <aside class="side-panel" aria-label="Navegação institucional">
      <div class="side-brand">
        <img src="{% static 'img/logo-campus-calm.png' %}" alt="CampusCalm" class="side-logo">
        <p class="side-title">CampusCalm</p>
        <p class="side-subtitle">Projeto institucional</p>
      </div>
      <nav class="side-nav">
        <a class="active" href="#inicio">Visão geral</a>
        <a href="#sobre">Sobre</a>
        <a href="#solucoes">Soluções</a>
        <a href="#campuscalm">CampusCalm</a>
        <a href="#contato">Contato</a>
      </nav>
      <div class="side-card">
        <p class="side-card-title">Conheça o projeto</p>
        <p>Materiais institucionais e visão geral do CampusCalm.</p>
        <a class="side-button" href="#campuscalm">Ver detalhes</a>
      </div>
    </aside>

    <div class="page-body">
      <!-- Header institucional -->
      <header class="site-header" id="inicio">
        <div class="container header-content">
          <div class="brand">
            <img src="{% static 'img/logoalgorithminsights_empresa.png' %}" alt="Algorithm Insights Sistemas" class="brand-logo">
            <div class="brand-copy">
              <p class="brand-title">Algorithm Insights Sistemas</p>
              <p class="brand-tagline">Transformando dados em decisões inteligentes e ajudando você a alcançar o seu sonho.</p>
            </div>
          </div>
          <nav class="site-nav" aria-label="Menu principal">
            <a href="#inicio">Início</a>
            <a href="#sobre">Sobre</a>
            <a href="#solucoes">Soluções</a>
            <a href="#campuscalm">CampusCalm</a>
            <a href="#contato">Contato</a>
          </nav>
        </div>
      </header>

      <main>
        <!-- Hero -->
        <section class="hero">
          <div class="container hero-grid">
            <div class="hero-copy">
              <p class="eyebrow">Algorithm Insights Sistemas</p>
              <h1>CampusCalm — Tecnologia e bem-estar aplicados à educação</h1>
              <p class="lead">
                Uma iniciativa institucional que combina tecnologia, cuidado e organização
                para apoiar ambientes educacionais mais equilibrados e humanos.
              </p>
              <a class="btn-primary" href="#campuscalm">Conheça o Projeto</a>
            </div>
            <div class="hero-panel" aria-hidden="true">
              <div class="hero-card">
                <span class="hero-tag">Institucional</span>
                <h2>Clareza e serenidade na jornada educacional</h2>
                <p>
                  Estrutura pensada para apoiar pessoas, com foco em processos simples e
                  decisões bem orientadas.
                </p>
                <div class="hero-metrics">
                  <div>
                    <span class="metric-title">Bem-estar</span>
                    <span class="metric-text">Apoio contínuo</span>
                  </div>
                  <div>
                    <span class="metric-title">Tecnologia</span>
                    <span class="metric-text">Base sólida</span>
                  </div>
                  <div>
                    <span class="metric-title">Educação</span>
                    <span class="metric-text">Ambiente integrado</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Sobre o projeto -->
        <section class="section" id="sobre">
          <div class="container">
            <div class="section-header">
              <h2>Sobre o CampusCalm</h2>
              <p>
                O CampusCalm é um projeto institucional voltado a integrar tecnologia e
                bem-estar no contexto educacional. Com linguagem clara e foco em pessoas,
                promove rotinas mais organizadas e uma experiência acadêmica mais tranquila.
              </p>
            </div>
            <div class="feature-grid">
              <div class="feature-card">
                <h3>Bem-estar como prioridade</h3>
                <p>Estruturas que respeitam o ritmo humano e estimulam equilíbrio.</p>
              </div>
              <div class="feature-card">
                <h3>Tecnologia aplicada</h3>
                <p>Recursos digitais que simplificam processos e favorecem decisões claras.</p>
              </div>
              <div class="feature-card">
                <h3>Ambiente educacional</h3>
                <p>Integração cuidadosa entre organização acadêmica e suporte diário.</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Vínculo institucional -->
        <section class="section section-alt" id="campuscalm">
          <div class="container link-grid">
            <div>
              <h2>Vínculo institucional</h2>
              <p>
                O CampusCalm é uma iniciativa da Algorithm Insights Sistemas. A proposta
                nasce da experiência em tecnologia corporativa aplicada à educação, garantindo
                credibilidade, governança e um olhar técnico consistente.
              </p>
            </div>
            <div class="institution-card">
              <p class="institution-title">Algorithm Insights Sistemas</p>
              <p>
                Base tecnológica sólida, visão institucional e compromisso com soluções
                responsáveis para o ambiente educacional.
              </p>
            </div>
          </div>
        </section>

        <!-- Soluções / Pilares -->
        <section class="section" id="solucoes">
          <div class="container">
            <div class="section-header">
              <h2>Soluções e pilares</h2>
              <p>Componentes essenciais do CampusCalm para uma experiência educacional mais consistente.</p>
            </div>
            <div class="pillar-grid">
              <div class="pillar-card pillar-span-6">
                <div class="pillar-icon" aria-hidden="true"></div>
                <h3>Tecnologia Educacional</h3>
                <p>Ferramentas organizadas para apoiar fluxos acadêmicos com clareza.</p>
              </div>
              <div class="pillar-card pillar-span-6">
                <div class="pillar-icon" aria-hidden="true"></div>
                <h3>Bem-estar Digital</h3>
                <p>Práticas e recursos que favorecem equilíbrio e atenção no cotidiano.</p>
              </div>
              <div class="pillar-card pillar-span-5">
                <div class="pillar-icon" aria-hidden="true"></div>
                <h3>Automação Inteligente</h3>
                <p>Processos simplificados com foco em eficiência e tranquilidade operacional.</p>
              </div>
              <div class="pillar-card pillar-span-7">
                <div class="pillar-icon" aria-hidden="true"></div>
                <h3>Análise e Organização</h3>
                <p>Estruturação de informações para decisões mais claras e conscientes.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <!-- Footer -->
      <footer class="site-footer" id="contato">
        <div class="container footer-grid">
          <div class="footer-brand">
            <div class="footer-brand-row">
              <img src="{% static 'img/logoalgorithminsights_empresa.png' %}" alt="Algorithm Insights Sistemas" class="footer-logo">
              <div>
                <p class="footer-title">Algorithm Insights Sistemas</p>
                <p class="footer-tagline">Transformando dados em decisões inteligentes e ajudando você a alcançar o seu sonho.</p>
              </div>
            </div>
            <p class="footer-text">Soluções institucionais com foco em tecnologia e bem-estar educacional.</p>
          </div>
          <div class="footer-info">
            <p class="footer-heading">Contato institucional</p>
            <p class="footer-text">Espaço reservado para canais oficiais de contato.</p>
          </div>
          <div class="footer-info">
            <p class="footer-heading">Redes sociais</p>
            <div class="socials">
              <span class="social-pill">Ícone</span>
              <span class="social-pill">Ícone</span>
              <span class="social-pill">Ícone</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  </div>
</body>
</html>
```

## 2) CSS da Home

```css
:root {
  --brand: #1d3b5f;
  --brand-strong: #0f2a4a;
  --brand-soft: #e4edf7;
  --ink: #1f2a3a;
  --muted: #5d6b82;
  --bg: #f2f5f9;
  --surface: #ffffff;
  --border: #e4e9f1;
  --shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
  --radius: 18px;
  --side-width: 250px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--ink);
  background: linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
  line-height: 1.6;
}

a {
  color: inherit;
  text-decoration: none;
}

.container {
  width: min(1180px, 92vw);
  margin: 0 auto;
}

.page-shell {
  display: flex;
  min-height: 100vh;
}

.side-panel {
  width: var(--side-width);
  background: linear-gradient(180deg, #0f2a46, #091a2b);
  color: #e8eef8;
  padding: 32px 22px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: sticky;
  top: 0;
  height: 100vh;
}

.side-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.side-logo {
  width: 120px;
  height: 120px;
  object-fit: contain;
  margin-bottom: 12px;
}

.side-title {
  font-weight: 600;
  font-size: 1.05rem;
  margin-bottom: 4px;
}

.side-subtitle {
  font-size: 0.95rem;
  color: rgba(232, 238, 248, 0.7);
}

.side-nav {
  display: grid;
  gap: 10px;
}

.side-nav a {
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  color: #d9e4f5;
  font-size: 1rem;
  transition: background 0.2s ease, color 0.2s ease;
}

.side-nav a:hover,
.side-nav a:focus {
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
}

.side-nav a.active {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  font-weight: 600;
}

.side-card {
  margin-top: auto;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  padding: 18px;
  font-size: 0.9rem;
  color: rgba(232, 238, 248, 0.85);
}

.side-card-title {
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.side-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 12px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #ffffff;
  font-weight: 600;
  font-size: 0.85rem;
}

.page-body {
  flex: 1;
  padding-bottom: 32px;
}

/* Header */
.site-header {
  position: sticky;
  top: 0;
  background: rgba(242, 245, 249, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  z-index: 10;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  height: 72px;
  width: auto;
}

.brand-copy {
  max-width: 360px;
}

.brand-title {
  font-weight: 600;
  font-size: 1.25rem;
  margin-bottom: 4px;
}

.brand-tagline {
  font-size: 0.9rem;
  color: var(--muted);
  line-height: 1.4;
  font-weight: 600;
}

.site-nav {
  display: flex;
  gap: 20px;
  font-size: 0.95rem;
  color: var(--muted);
}

.site-nav a {
  padding: 6px 12px;
  border-radius: 999px;
  background: transparent;
  transition: background 0.2s ease, color 0.2s ease;
}

.site-nav a:hover,
.site-nav a:focus {
  background: var(--brand-soft);
  color: var(--brand-strong);
}

/* Hero */
.hero {
  padding: 48px 0 40px;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 32px;
  align-items: stretch;
}

.hero-copy {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px;
  box-shadow: var(--shadow);
}

.eyebrow {
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  color: var(--brand-strong);
  font-weight: 600;
  margin-bottom: 12px;
}

.hero h1 {
  font-size: clamp(2rem, 3vw, 3rem);
  line-height: 1.2;
  margin-bottom: 16px;
}

.lead {
  color: var(--muted);
  margin-bottom: 24px;
  font-size: 1.02rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 22px;
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-weight: 600;
  border: 1px solid transparent;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-primary:hover,
.btn-primary:focus {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(15, 42, 74, 0.2);
}

.hero-panel {
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
}

.hero-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px;
  box-shadow: var(--shadow);
  width: 100%;
  animation: fadeInUp 0.6s ease both;
}

.hero-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 16px;
}

.hero-card h2 {
  font-size: 1.35rem;
  margin-bottom: 12px;
}

.hero-card p {
  color: var(--muted);
  margin-bottom: 20px;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-title {
  display: block;
  font-weight: 600;
  color: var(--brand-strong);
  font-size: 0.9rem;
}

.metric-text {
  font-size: 0.85rem;
  color: var(--muted);
}

/* Sections */
.section {
  padding: 48px 0;
}

.section-alt {
  background: linear-gradient(180deg, #f8fbff, #f1f5f9);
}

.section-header {
  max-width: 720px;
  margin-bottom: 32px;
}

.section-header h2 {
  font-size: 2rem;
  margin-bottom: 12px;
}

.section-header p {
  color: var(--muted);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
}

.feature-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.feature-card h3 {
  margin-bottom: 10px;
  font-size: 1.15rem;
}

.feature-card p {
  color: var(--muted);
}

.link-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 32px;
  align-items: center;
}

.institution-card {
  background: var(--surface);
  border-left: 4px solid var(--brand);
  border-radius: 16px;
  padding: 24px 28px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

.institution-title {
  font-weight: 700;
  margin-bottom: 8px;
}

.pillar-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 20px;
}

.pillar-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
  animation: fadeInUp 0.7s ease both;
}

.pillar-span-6 {
  grid-column: span 6;
}

.pillar-span-5 {
  grid-column: span 5;
}

.pillar-span-7 {
  grid-column: span 7;
}

.pillar-card:nth-child(2) {
  animation-delay: 0.05s;
}

.pillar-card:nth-child(3) {
  animation-delay: 0.1s;
}

.pillar-card:nth-child(4) {
  animation-delay: 0.15s;
}

.pillar-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--brand), #4b6c9c);
  opacity: 0.18;
}

.pillar-card h3 {
  font-size: 1.05rem;
}

.pillar-card p {
  color: var(--muted);
}

/* Footer */
.site-footer {
  padding: 48px 0 56px;
  border-top: 1px solid var(--border);
  background: #f8fafc;
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 28px;
}

.footer-logo {
  height: 60px;
  width: auto;
}

.footer-brand-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.footer-tagline {
  font-size: 0.9rem;
  color: var(--muted);
  line-height: 1.4;
}

.footer-title {
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 6px;
}

.footer-tagline {
  font-weight: 600;
}

.footer-heading {
  font-weight: 600;
  margin-bottom: 8px;
}

.footer-text {
  color: var(--muted);
}

.socials {
  display: flex;
  gap: 12px;
}

.social-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 0.8rem;
  font-weight: 600;
}

/* Motion */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Responsive */
@media (max-width: 1100px) {
  .side-panel {
    display: none;
  }

  .site-nav {
    display: flex;
  }
}

@media (min-width: 1101px) {
  .site-nav {
    display: none;
  }
}

@media (max-width: 960px) {
  .hero-grid,
  .link-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    justify-content: flex-start;
  }

  .feature-grid {
    grid-template-columns: 1fr 1fr;
  }

  .pillar-grid,
  .footer-grid {
    grid-template-columns: 1fr 1fr;
  }

  .pillar-card {
    grid-column: auto;
  }
}

@media (max-width: 720px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
  }

  .brand {
    flex-direction: column;
    align-items: flex-start;
  }

  .footer-brand-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .feature-grid,
  .pillar-grid,
  .footer-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    padding-top: 36px;
  }
}
```

## 3) View (Django)

```python
# apps/ui/views.py

def home_view(request):
    return render(request, "ui/home.html")
```

## 4) URL (Django)

```python
# apps/ui/urls.py

from ui.views import home_view

urlpatterns = [
    path("home/", home_view, name="ui-home"),
]
```

## 5) Assets (imagens)
- `static/img/logo-campus-calm.png` (logo CampusCalm com fundo transparente)
- `static/img/logoalgorithminsights_empresa.png` (logo Algorithm Insights com fundo transparente)

Observação: os arquivos de imagem são binários; não podem ser incluídos aqui no texto.

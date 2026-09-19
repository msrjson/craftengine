{#
    Public landing page.

    Rendered by `app/Http/Controllers/Admin/HomeController.py::index`, mapped to
    `/`, `/home` and `/dashboard` in `routes/web.py`. Open to everyone — no
    middleware.

    Context:
      posts         list[Post]  the six most recent posts. The controller
                                degrades this to an empty list (and logs) if the
                                query fails, because the strip is decorative and
                                the front door should not 500 for it.
      show_sidebar  bool        False here: the landing page is full width.
#}
@extends("layouts.app")

@section("title", "Craft Engine — The Python Framework for Expressive Web Applications")

@section("content")
    <!-- Hero Section -->
    <div class="hero-section">
        <div class="hero-glow"></div>
        <div class="hero-inner">
            <div class="hero-content">
                <div class="hero-badge">
                    <span class="badge-dot"></span>
                    <span>Craft Framework · Open Source MIT</span>
                </div>
                <h1 class="hero-title">
                    Craft Engine <sup class="hero-version">v{{ config('app.version', '3.11.0') }}</sup>
                </h1>
                <p class="hero-subtitle">
                    The Python Framework for Expressive Web Applications
                </p>
                <p class="hero-description">
                    Build elegant, production-grade applications in Python with familiar MVC conventions.
                    Craft ORM with dual-key UUIDs, Forge templates, Active Defense WAF, and visual CRUD builder — batteries included.
                </p>
                <div class="hero-actions">
                    <a href="/docs/installation" class="btn-primary" id="hero-learn-more">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
                        Read Documentation
                    </a>
                    <a href="#quickstart" class="btn-secondary" id="hero-quickstart">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
                        {{ __('learn_more') }}
                    </a>
                </div>
                <div class="hero-stats">
                    <div class="stat-item">
                        <span class="stat-value">880+</span>
                        <span class="stat-label">Tests Passing</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">3</span>
                        <span class="stat-label">DB Engines</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">MIT</span>
                        <span class="stat-label">License</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">Py 3.14+</span>
                        <span class="stat-label">ASGI Runtime</span>
                    </div>
                </div>
            </div>

            <!-- Animated Code Preview -->
            <div class="hero-code-card">
                <div class="code-card-header">
                    <div class="code-dots">
                        <span class="dot dot-red"></span>
                        <span class="dot dot-yellow"></span>
                        <span class="dot dot-green"></span>
                    </div>
                    <span class="code-filename">routes/web.py & app/Models/Task.py</span>
                </div>
                <pre class="code-block"><code><span class="code-keyword">from</span> <span class="code-module">craft.facades</span> <span class="code-keyword">import</span> Route, Auth, DB
<span class="code-keyword">from</span> <span class="code-module">craft.orm.model</span> <span class="code-keyword">import</span> Model

<span class="code-keyword">class</span> <span class="code-class">Task</span>(Model):
    __table__ = <span class="code-string">"tasks"</span>
    fillable = [<span class="code-string">"title"</span>, <span class="code-string">"description"</span>, <span class="code-string">"user_id"</span>]

    <span class="code-keyword">def</span> <span class="code-func">user</span>(self):
        <span class="code-keyword">return</span> self.belongs_to(User)

<span class="code-comment"># Expressive Routing & RBAC Guards</span>
Route.get(<span class="code-string">"/panel"</span>, [PanelController, <span class="code-string">"index"</span>]).middleware(<span class="code-string">"auth"</span>)
Route.get(<span class="code-string">"/admin"</span>, [HomeController, <span class="code-string">"admin"</span>]).middleware(<span class="code-string">"auth"</span>, <span class="code-string">"role:admin"</span>)</code></pre>
            </div>
        </div>
    </div>

    <!-- Quick Start Section -->
    <section class="section-quickstart" id="quickstart">
        <div class="section-container">
            <div class="section-header">
                <span class="section-tag">Rapid Setup</span>
                <h2 class="section-title">Up and Running in Seconds</h2>
                <p class="section-description">
                    From zero to a running application with migrations, seed data, and administrative UI — in four simple commands.
                </p>
            </div>
            <div class="quickstart-grid">
                <div class="quickstart-step">
                    <div class="step-top">
                        <div class="step-number">1</div>
                        <h3 class="step-title">Configure Environment</h3>
                    </div>
                    <div class="step-terminal">
                        <div class="terminal-line"><span class="terminal-prompt">$</span> <code>cp .env.example .env</code></div>
                        <div class="terminal-line"><span class="terminal-prompt">$</span> <code>python dev.py key:generate</code></div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-top">
                        <div class="step-number">2</div>
                        <h3 class="step-title">Migrate & Seed</h3>
                    </div>
                    <div class="step-terminal">
                        <div class="terminal-line"><span class="terminal-prompt">$</span> <code>python dev.py migrate --seed</code></div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-top">
                        <div class="step-number">3</div>
                        <h3 class="step-title">Serve Local App</h3>
                    </div>
                    <div class="step-terminal">
                        <div class="terminal-line"><span class="terminal-prompt">$</span> <code>python dev.py serve</code></div>
                    </div>
                </div>
                <div class="quickstart-step">
                    <div class="step-top">
                        <div class="step-number step-docker">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                        </div>
                        <h3 class="step-title">Run with Docker</h3>
                    </div>
                    <div class="step-terminal">
                        <div class="terminal-line"><span class="terminal-prompt">$</span> <code>docker compose up -d --build</code></div>
                    </div>
                    <p class="step-note">App ready on <a href="http://localhost:9000" target="_blank" class="text-orange-600 font-semibold hover:underline">localhost:9000</a></p>
                </div>
            </div>
        </div>
    </section>


    <!-- Why Craft Feature Grid -->
    <section class="section-features" id="features">
        <div class="section-container">
            <div class="section-header">
                <span class="section-tag">Core Architecture</span>
                <h2 class="section-title">Everything You Need, Nothing You Don't</h2>
                <p class="section-description">
                    A full-featured framework that respects your time. Familiar MVC conventions tailored for Python developers who demand speed, clarity, and security.
                </p>
            </div>
            <div class="features-grid">
                <!-- Feature 1 -->
                <div class="feature-card" id="feature-orm">
                    <div class="feature-icon feature-icon-orange">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                    </div>
                    <h3>Active Record & Dual-Key UUID</h3>
                    <p>High-performance ORM with eager loading, relationships, soft deletes, query builder, and automatic UUID public resolution.</p>
                </div>
                <!-- Feature 2 -->
                <div class="feature-card" id="feature-perf">
                    <div class="feature-icon feature-icon-blue">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                    </div>
                    <h3>Async ASGI Performance</h3>
                    <p>Powered by Starlette's high-throughput ASGI core with sub-millisecond middleware pipelines and asynchronous controller support.</p>
                </div>
                <!-- Feature 3 -->
                <div class="feature-card" id="feature-security">
                    <div class="feature-icon feature-icon-green">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    </div>
                    <h3>Active Defense & WAF Firewall</h3>
                    <p>Built-in Web Application Firewall (SQLi, XSS, SSRF protection), Honeypot attacker trapping, brute-force cooldown, and audit logging.</p>
                </div>
                <!-- Feature 4 -->
                <div class="feature-card" id="feature-crud">
                    <div class="feature-icon feature-icon-purple">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                    </div>
                    <h3>Visual & Terminal CRUD Builder</h3>
                    <p>Generate full vertical slices in one command or via visual web builder: DDL migrations, Models, FormRequests, Resources, and Admin UI.</p>
                </div>
                <!-- Feature 5 -->
                <div class="feature-card" id="feature-views">
                    <div class="feature-icon feature-icon-pink">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                    </div>
                    <h3>Forge Template Engine</h3>
                    <p>Clean Jinja2 template extension with expressive directives: <code>&#64;csrf</code>, <code>&#64;auth</code>, <code>&#64;guest</code>, <code>&#64;can</code>, and component layouts.</p>
                </div>

                <!-- Feature 6 -->
                <div class="feature-card" id="feature-cli">
                    <div class="feature-icon feature-icon-amber">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
                    </div>
                    <h3>Developer Console & CLI</h3>
                    <p>Comprehensive CLI tooling: generators, interactive tinker console, database migrator, queue workers, task scheduler, and firewall management.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Action Cards Section -->
    <section class="section-cards" id="resources">
        <div class="section-container">
            <div class="cards-grid">
                <a href="/docs/installation" class="action-card" id="card-download">
                    <div class="card-icon-wrapper card-icon-orange">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    </div>
                    <h3>Get Started</h3>
                    <p>Install the framework and start building expressive applications.</p>
                </a>
                <a href="/docs" class="action-card" id="card-docs">
                    <div class="card-icon-wrapper card-icon-blue">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
                    </div>
                    <h3>Documentation</h3>
                    <p>Comprehensive architectural and API guides for every component.</p>
                </a>
                <a href="/panel" class="action-card" id="card-panel">
                    <div class="card-icon-wrapper card-icon-green">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                    </div>
                    <h3>Control Panel</h3>
                    <p>Manage users, RBAC permissions, database metrics, and system runtime.</p>
                </a>
                <a href="/docs/testing" class="action-card" id="card-contribute">
                    <div class="card-icon-wrapper card-icon-purple">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <h3>Battle-Tested Codebase</h3>
                    <p>880+ automated tests across SQLite, PostgreSQL, and modern Python runtimes.</p>
                </a>
            </div>
        </div>
    </section>
@endsection



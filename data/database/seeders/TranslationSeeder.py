"""Seeds the `translations` table from the locale catalog.

Locales follow the governance roles: `en` is the source, `pt-BR` the default
runtime locale and `es` the alternative. A separate `pt` locale was drift and
is no longer seeded; rows an earlier run wrote are left in place (records are
never deleted) and are unreachable once `pt` is not an offered locale.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB
from craft.seeding import Seeder

#: Interface strings, keyed by locale. Source of truth for the shipped UI.
#: The richer, semantically-keyed catalog lives in resources/lang/catalog.json.
TRANSLATIONS = {
    "en": {
        "greeting": "Hello",
        "welcome": "Welcome to Craft",
        "discuss": "Discuss",
        "contribute": "Contribute",
        "learn": "Learn",
        "dashboard": "Dashboard",
        "download": "Download",
        "login": "Log In",
        "register": "Register",
        "logout": "Log Out",
        "why_craft": "Why Craft?",
        "small_footprint_title": "Framework with a small footprint",
        "small_footprint_desc": "Craft has zero hot-start footprint and lazy dependency imports, keeping memory usage minimal.",
        "exceptional_perf_title": "Exceptional performance",
        "exceptional_perf_desc": "Built on ASGI pipelines and direct database drivers, Craft handles requests in microseconds.",
        "simple_solutions_title": "Simple solutions over complexity",
        "simple_solutions_desc": "Craft favours a standard MVC layout, an autowired container and Active Record models without forced configuration.",
        "strong_security_title": "Strong security",
        "strong_security_desc": "Ships with CSRF protection, signed sessions, hashed passwords and CAPTCHA support.",
        "recent_posts": "Recent Posts",
        "small_framework_title": "The small framework with powerful features",
        "learn_more": "Learn more",
        "framework_description": "Craft is a Python MVC framework with a very small footprint, built for developers who want a simple, elegant toolkit for full-featured web applications.",
        "msr.entity.tagline": "A web application built on Craft Engine.",
        "msr.entity.summary": "A Python web application built on Craft Engine, the batteries-included MVC framework.",
    },
    # Brazilian Portuguese.
    "pt-BR": {
        "greeting": "Olá",
        "welcome": "Bem-vindo ao Craft",
        "discuss": "Fórum",
        "contribute": "Contribuir",
        "learn": "Aprender",
        "dashboard": "Painel de Controle",
        "download": "Baixar",
        "login": "Entrar",
        "register": "Criar conta",
        "logout": "Sair",
        "why_craft": "Por que o Craft?",
        "small_footprint_title": "Framework com consumo mínimo",
        "small_footprint_desc": "O Craft tem consumo zero de inicialização a quente e importações preguiçosas de dependências, mantendo o uso de memória no mínimo.",
        "exceptional_perf_title": "Desempenho excepcional",
        "exceptional_perf_desc": "Construído sobre pipelines ASGI e drivers de banco diretos, o Craft responde a requisições em microssegundos.",
        "simple_solutions_title": "Simplicidade acima de complexidade",
        "simple_solutions_desc": "O Craft incentiva o layout MVC padrão, container com injeção automática e models Active Record sem configuração forçada.",
        "strong_security_title": "Segurança robusta",
        "strong_security_desc": "Vem com proteção CSRF, sessões assinadas, senhas com hash e suporte a CAPTCHA.",
        "recent_posts": "Postagens recentes",
        "small_framework_title": "O framework pequeno com recursos poderosos",
        "learn_more": "Saiba mais",
        "framework_description": "O Craft é um framework MVC em Python com consumo mínimo de recursos, feito para quem quer um conjunto de ferramentas simples e elegante para aplicações web completas.",
        "msr.entity.tagline": "Uma aplicação web construída com o Craft Engine.",
        "msr.entity.summary": "Uma aplicação web em Python construída com o Craft Engine, o framework MVC completo.",
    },
    "es": {
        "greeting": "Hola",
        "welcome": "Bienvenido a Craft",
        "discuss": "Foro",
        "contribute": "Contribuir",
        "learn": "Aprender",
        "dashboard": "Panel de Control",
        "download": "Descargar",
        "login": "Iniciar sesión",
        "register": "Crear cuenta",
        "logout": "Cerrar sesión",
        "why_craft": "¿Por qué Craft?",
        "small_footprint_title": "Framework con consumo mínimo",
        "small_footprint_desc": "Craft tiene un consumo nulo de arranque en caliente e importaciones perezosas de dependencias, manteniendo el uso de memoria al mínimo.",
        "exceptional_perf_title": "Rendimiento excepcional",
        "exceptional_perf_desc": "Construido sobre canalizaciones ASGI y controladores de base de datos directos, Craft responde a las solicitudes en microsegundos.",
        "simple_solutions_title": "Simplicidad sobre complejidad",
        "simple_solutions_desc": "Craft favorece el diseño MVC estándar, un contenedor con inyección automática y modelos Active Record sin configuración forzada.",
        "strong_security_title": "Seguridad sólida",
        "strong_security_desc": "Incluye protección CSRF, sesiones firmadas, contraseñas con hash y compatibilidad con CAPTCHA.",
        "recent_posts": "Publicaciones recientes",
        "small_framework_title": "El framework pequeño con potentes características",
        "learn_more": "Saber más",
        "framework_description": "Craft es un framework MVC en Python con un consumo mínimo de recursos, pensado para quienes buscan un conjunto de herramientas simple y elegante para aplicaciones web completas.",
        "msr.entity.tagline": "Una aplicación web construida con Craft Engine.",
        "msr.entity.summary": "Una aplicación web en Python construida con Craft Engine, el framework MVC completo.",
    },
}


class TranslationSeeder(Seeder):
    def run(self):
        for locale, entries in TRANSLATIONS.items():
            for key, value in entries.items():
                existing = DB.table("translations").where("key", key).where("locale", locale).first()
                if existing is None:
                    DB.table("translations").insert({"key": key, "locale": locale, "value": value})

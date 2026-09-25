"""Migration: the sign-in, registration and dashboard copy, in every offered locale.

Written by `craft make:auth` next to the views and controllers that use
these keys, so a generated screen never renders a raw key. A row that already
exists is left alone: the copy belongs to the project from here on, and an
edit made in the database must survive a re-run.

Forward-only: there is no `down()`; translations are never deleted.

Category: Generated (translations).
"""

from craft.facades import DB

#: (key, locale, value). `en` is the source, `pt-BR` the default, `es` the alternative.
ROWS = [('auth.field.name', 'en', 'Name'),
 ('auth.field.name', 'pt-BR', 'Nome'),
 ('auth.field.name', 'es', 'Nombre'),
 ('auth.field.email', 'en', 'Email'),
 ('auth.field.email', 'pt-BR', 'E-mail'),
 ('auth.field.email', 'es', 'Correo electrónico'),
 ('auth.field.password', 'en', 'Password'),
 ('auth.field.password', 'pt-BR', 'Senha'),
 ('auth.field.password', 'es', 'Contraseña'),
 ('auth.login.title', 'en', 'Sign in'),
 ('auth.login.title', 'pt-BR', 'Entrar'),
 ('auth.login.title', 'es', 'Iniciar sesión'),
 ('auth.login.action.submit', 'en', 'Sign in'),
 ('auth.login.action.submit', 'pt-BR', 'Entrar'),
 ('auth.login.action.submit', 'es', 'Iniciar sesión'),
 ('auth.login.link.register', 'en', 'Create an account'),
 ('auth.login.link.register', 'pt-BR', 'Criar uma conta'),
 ('auth.login.link.register', 'es', 'Crear una cuenta'),
 ('auth.login.failed', 'en', 'These credentials do not match our records.'),
 ('auth.login.failed', 'pt-BR', 'Essas credenciais não correspondem aos nossos registros.'),
 ('auth.login.failed', 'es', 'Estas credenciales no coinciden con nuestros registros.'),
 ('auth.register.title', 'en', 'Create an account'),
 ('auth.register.title', 'pt-BR', 'Criar uma conta'),
 ('auth.register.title', 'es', 'Crear una cuenta'),
 ('auth.register.action.submit', 'en', 'Create account'),
 ('auth.register.action.submit', 'pt-BR', 'Criar conta'),
 ('auth.register.action.submit', 'es', 'Crear cuenta'),
 ('auth.register.link.login', 'en', 'Already have an account? Sign in'),
 ('auth.register.link.login', 'pt-BR', 'Já tem uma conta? Entrar'),
 ('auth.register.link.login', 'es', '¿Ya tienes una cuenta? Inicia sesión'),
 ('auth.dashboard.title', 'en', 'Dashboard'),
 ('auth.dashboard.title', 'pt-BR', 'Painel'),
 ('auth.dashboard.title', 'es', 'Panel'),
 ('auth.dashboard.signed_in_as', 'en', 'Signed in as {email}.'),
 ('auth.dashboard.signed_in_as', 'pt-BR', 'Conectado como {email}.'),
 ('auth.dashboard.signed_in_as', 'es', 'Sesión iniciada como {email}.'),
 ('auth.dashboard.action.sign_out', 'en', 'Sign out'),
 ('auth.dashboard.action.sign_out', 'pt-BR', 'Sair'),
 ('auth.dashboard.action.sign_out', 'es', 'Cerrar sesión')]


def up():
    for key, locale, value in ROWS:
        exists = DB.table("translations").where("key", key).where("locale", locale).first()
        if exists is None:
            DB.table("translations").insert({"key": key, "locale": locale, "value": value})

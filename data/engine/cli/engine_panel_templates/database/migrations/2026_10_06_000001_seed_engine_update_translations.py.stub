"""Migration: the engine update screen copy, in every offered locale.

Written by `craft make:engine-panel` next to the screen and the alert that use
these keys. A row that already exists is left alone: the copy belongs to the
project from here on, and an edit made in the database must survive a re-run.

Forward-only: there is no `down()`; translations are never deleted.

Category: Generated (translations).
"""

from craft.facades import DB

#: (key, locale, value). `en` is the source, `pt-BR` the default, `es` the alternative.
ROWS = [
    ("engine.update.title", "en", "Engine updates"),
    ("engine.update.title", "pt-BR", "Atualizações do engine"),
    ("engine.update.title", "es", "Actualizaciones del engine"),
    ("engine.update.alert.available", "en", "A new Craft Engine release is available: {version}."),
    ("engine.update.alert.available", "pt-BR", "Há uma nova versão do Craft Engine disponível: {version}."),
    ("engine.update.alert.available", "es", "Hay una nueva versión de Craft Engine disponible: {version}."),
    ("engine.update.alert.action", "en", "Review the update"),
    ("engine.update.alert.action", "pt-BR", "Revisar a atualização"),
    ("engine.update.alert.action", "es", "Revisar la actualización"),
    ("engine.update.field.pinned", "en", "Pinned release"),
    ("engine.update.field.pinned", "pt-BR", "Versão fixada"),
    ("engine.update.field.pinned", "es", "Versión fijada"),
    ("engine.update.field.running", "en", "Running engine"),
    ("engine.update.field.running", "pt-BR", "Engine em execução"),
    ("engine.update.field.running", "es", "Engine en ejecución"),
    ("engine.update.field.mode", "en", "Delivery"),
    ("engine.update.field.mode", "pt-BR", "Forma de entrega"),
    ("engine.update.field.mode", "es", "Forma de entrega"),
    ("engine.update.field.verify_command", "en", "Verification command"),
    ("engine.update.field.verify_command", "pt-BR", "Comando de verificação"),
    ("engine.update.field.verify_command", "es", "Comando de verificación"),
    ("engine.update.field.checked_at", "en", "Last checked"),
    ("engine.update.field.checked_at", "pt-BR", "Última verificação"),
    ("engine.update.field.checked_at", "es", "Última comprobación"),
    ("engine.update.empty.verify_command", "en", "None set: moves are applied without verification."),
    ("engine.update.empty.verify_command", "pt-BR", "Nenhum definido: as atualizações são aplicadas sem verificação."),
    ("engine.update.empty.verify_command", "es", "Ninguno definido: las actualizaciones se aplican sin verificación."),
    ("engine.update.status.never_checked", "en", "Updates have not been checked yet."),
    ("engine.update.status.never_checked", "pt-BR", "As atualizações ainda não foram verificadas."),
    ("engine.update.status.never_checked", "es", "Las actualizaciones aún no se han comprobado."),
    ("engine.update.status.check_failed", "en", "The last check failed ({code})."),
    ("engine.update.status.check_failed", "pt-BR", "A última verificação falhou ({code})."),
    ("engine.update.status.check_failed", "es", "La última comprobación falló ({code})."),
    ("engine.update.status.current", "en", "This project runs the newest release."),
    ("engine.update.status.current", "pt-BR", "Este projeto está na versão mais recente."),
    ("engine.update.status.current", "es", "Este proyecto ejecuta la versión más reciente."),
    ("engine.update.lock_missing", "en", "Engine updates are not set up for this project ({code}). Pin it from the console with dev.py engine adopt."),
    ("engine.update.lock_missing", "pt-BR", "As atualizações do engine não estão configuradas neste projeto ({code}). Fixe a versão pelo console com dev.py engine adopt."),
    ("engine.update.lock_missing", "es", "Las actualizaciones del engine no están configuradas en este proyecto ({code}). Fije la versión desde la consola con dev.py engine adopt."),
    ("engine.update.refused", "en", "The engine refused the action: {code}."),
    ("engine.update.refused", "pt-BR", "O engine recusou a ação: {code}."),
    ("engine.update.refused", "es", "El engine rechazó la acción: {code}."),
    ("engine.update.action.check", "en", "Check for updates"),
    ("engine.update.action.check", "pt-BR", "Verificar atualizações"),
    ("engine.update.action.check", "es", "Buscar actualizaciones"),
    ("engine.update.action.review_update", "en", "Review update to {version}"),
    ("engine.update.action.review_update", "pt-BR", "Revisar atualização para {version}"),
    ("engine.update.action.review_update", "es", "Revisar actualización a {version}"),
    ("engine.update.action.review_upgrade", "en", "Review upgrade to {version}"),
    ("engine.update.action.review_upgrade", "pt-BR", "Revisar upgrade para {version}"),
    ("engine.update.action.review_upgrade", "es", "Revisar upgrade a {version}"),
    ("engine.update.action.apply", "en", "Apply {version}"),
    ("engine.update.action.apply", "pt-BR", "Aplicar {version}"),
    ("engine.update.action.apply", "es", "Aplicar {version}"),
    ("engine.update.action.back", "en", "Back to engine updates"),
    ("engine.update.action.back", "pt-BR", "Voltar para atualizações do engine"),
    ("engine.update.action.back", "es", "Volver a actualizaciones del engine"),
    ("engine.update.patches.heading", "en", "Local patches"),
    ("engine.update.patches.heading", "pt-BR", "Patches locais"),
    ("engine.update.patches.heading", "es", "Parches locales"),
    ("engine.update.patches.empty", "en", "No local patches."),
    ("engine.update.patches.empty", "pt-BR", "Nenhum patch local."),
    ("engine.update.patches.empty", "es", "Ningún parche local."),
    ("engine.update.drift.heading", "en", "Unregistered changes"),
    ("engine.update.drift.heading", "pt-BR", "Alterações não registradas"),
    ("engine.update.drift.heading", "es", "Cambios no registrados"),
    ("engine.update.drift.blocking", "en", "These engine files changed without a registered patch. Register them from the console before updating."),
    ("engine.update.drift.blocking", "pt-BR", "Estes arquivos do engine mudaram sem um patch registrado. Registre-os pelo console antes de atualizar."),
    ("engine.update.drift.blocking", "es", "Estos archivos del engine cambiaron sin un parche registrado. Regístrelos desde la consola antes de actualizar."),
    ("engine.update.review.heading_dry_run", "en", "Review: {current} to {target}"),
    ("engine.update.review.heading_dry_run", "pt-BR", "Revisão: {current} para {target}"),
    ("engine.update.review.heading_dry_run", "es", "Revisión: {current} a {target}"),
    ("engine.update.review.heading_applied", "en", "Updated: {current} to {target}"),
    ("engine.update.review.heading_applied", "pt-BR", "Atualizado: {current} para {target}"),
    ("engine.update.review.heading_applied", "es", "Actualizado: {current} a {target}"),
    ("engine.update.review.carried", "en", "Patches carried over"),
    ("engine.update.review.carried", "pt-BR", "Patches mantidos"),
    ("engine.update.review.carried", "es", "Parches mantenidos"),
    ("engine.update.review.retired", "en", "Patches retired"),
    ("engine.update.review.retired", "pt-BR", "Patches aposentados"),
    ("engine.update.review.retired", "es", "Parches retirados"),
    ("engine.update.review.notes", "en", "Changes that need attention"),
    ("engine.update.review.notes", "pt-BR", "Mudanças que pedem atenção"),
    ("engine.update.review.notes", "es", "Cambios que requieren atención"),
    ("engine.update.review.no_notes", "en", "No removed, deprecated, security or changed entries."),
    ("engine.update.review.no_notes", "pt-BR", "Nenhuma entrada de remoção, depreciação, segurança ou mudança."),
    ("engine.update.review.no_notes", "es", "Ninguna entrada de eliminación, obsolescencia, seguridad o cambio."),
    ("engine.update.review.next_steps", "en", "Next: rebuild or reinstall the engine where it is packaged, restart the application, then run migrate."),
    ("engine.update.review.next_steps", "pt-BR", "Próximo passo: reconstrua ou reinstale o engine onde ele é empacotado, reinicie a aplicação e rode o migrate."),
    ("engine.update.review.next_steps", "es", "Siguiente paso: reconstruya o reinstale el engine donde se empaqueta, reinicie la aplicación y ejecute migrate."),
]


def up():
    for key, locale, value in ROWS:
        exists = DB.table("translations").where("key", key).where("locale", locale).first()
        if exists is None:
            DB.table("translations").insert({"key": key, "locale": locale, "value": value})

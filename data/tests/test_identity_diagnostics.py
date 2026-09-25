"""Identity misconfiguration says what is wrong and how to fix it."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.auth import registry


def test_a_path_that_does_not_import_is_not_called_unset():
    error = registry.IdentityModelNotConfigured(
        "user", registry.REASON_IMPORT_FAILED, path="app.Models.Usr.User", cause="No module named 'app.Models.Usr'"
    )
    message = str(error)
    assert "app.Models.Usr.User" in message and "does not import" in message
    assert "make:auth" not in message


def test_an_unset_model_points_at_the_generator():
    error = registry.IdentityModelNotConfigured("role", registry.REASON_NOT_CONFIGURED, key="auth.models.role")
    assert "craft make:admin" in str(error) and "auth.models.role" in str(error)


def test_the_code_stays_available_for_machines():
    error = registry.IdentityModelNotConfigured("user", registry.REASON_NOT_CONFIGURED, key="auth.models.user")
    assert error.code == "IDENTITY_MODEL_NOT_CONFIGURED"
    assert str(error).startswith("IDENTITY_MODEL_NOT_CONFIGURED")

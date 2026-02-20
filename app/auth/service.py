"""Compatibility layer for gofr-np auth.

Historically gofr-np shipped a local file-backed JWT AuthService.
The project now uses gofr-common AuthService (Vault-backed stores).

This module remains to keep import paths stable for older imports.
"""

from gofr_common.auth import AuthService, TokenInfo

__all__ = ["AuthService", "TokenInfo"]

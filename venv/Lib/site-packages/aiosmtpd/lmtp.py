# Copyright 2014-2021 The aiosmtpd Developers
# SPDX-License-Identifier: Apache-2.0

from public import public

from aiosmtpd.smtp import SMTP, syntax


@public
class LMTP(SMTP):
    show_smtp_greeting: bool = False

    @syntax('LHLO hostname')
    async def smtp_LHLO(self, arg: str) -> None:
        """The LMTP greeting, used instead of HELO/EHLO."""
        await super().smtp_EHLO(arg)

    async def smtp_HELO(self, arg: str) -> None:
        """HELO is not a valid LMTP command."""
        await self.push('500 Error: command "HELO" not recognized')

    async def smtp_EHLO(self, arg: str) -> None:
        """EHLO is not a valid LMTP command."""
        await self.push('500 Error: command "EHLO" not recognized')

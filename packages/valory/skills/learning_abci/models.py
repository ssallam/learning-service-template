# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the shared state for the abci skill of LearningAbciApp."""

from typing import Any

from packages.valory.skills.abstract_round_abci.models import BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.valory.skills.learning_abci.rounds import LearningAbciApp


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = LearningAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool


class Params(BaseParams):
    """Parameters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""
        self.coingecko_price_template = self._ensure(
            "coingecko_price_template", kwargs, str
        )
        self.coingecko_api_key = kwargs.get("coingecko_api_key", None)
        self.token_address = kwargs.get("token_address", None)
        self.uni_router_address = kwargs.get("uni_router_address", None)

        default_tokens = "usdt:0x4ecaba5870353805a9f068101a40e0f32ed605c6,btc:0x8e5bbbb09ed1ebde8674cda39a0c169401db4252,eth:0x6a023ccd1ff6f2045c3309768ead9e68f978f6e1"
        target_tokens_str = kwargs.get("target_tokens", "")
        tokens = []
        if target_tokens_str and target_tokens_str.strip():
            tokens = [t.strip() for t in target_tokens_str.split(",") if t.strip()]
            tokens = [(s.upper(), a) for s, a in tokens]

        if not tokens:
            # [(token_name, token_address), ]
            tokens = [t.strip().split(":") for t in default_tokens.split(",") if t.strip()]

        assert tokens, "target tokens is not set, this is required to run this agent."
        self.target_tokens = tokens

        super().__init__(*args, **kwargs)

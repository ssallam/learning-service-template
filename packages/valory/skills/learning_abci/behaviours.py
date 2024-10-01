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

"""This package contains round behaviours of LearningAbciApp."""
import json
from abc import ABC
from typing import Generator, Set, Type, cast, Optional

from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.contracts.uniswapv2router02.contract import UniswapV2Router02
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.learning_abci.models import Params, SharedState
from packages.valory.skills.learning_abci.payloads import (
    APICheckPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)
from packages.valory.skills.learning_abci.rounds import (
    APICheckRound,
    DecisionMakingRound,
    Event,
    LearningAbciApp,
    SynchronizedData,
    TxPreparationRound,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import hash_payload_to_hex

HTTP_OK = 200
GNOSIS_CHAIN_ID = "gnosis"
TX_DATA = b"0x"
SAFE_GAS = 0
VALUE_KEY = "value"
TO_ADDRESS_KEY = "to_address"
debug_str = "*"*100


class LearningBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the learning_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @property
    def local_state(self) -> SharedState:
        """Return the state."""
        return cast(SharedState, self.context.state)


class APICheckBehaviour(LearningBaseBehaviour):  # pylint: disable=too-many-ancestors
    """APICheckBehaviour"""

    matching_round: Type[AbstractRound] = APICheckRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            self.context.logger.info(f"APICheckBehaviour.async_act    {debug_str} ")
            prices, amounts = yield from self.get_prices()

            prices_dict = json.dumps({i: p for i, p in enumerate(prices)})
            amounts_dict = json.dumps({i: a for i, a in enumerate(amounts)})
            self.context.logger.info(f"APICheckBehaviour saving amounts in payload: amounts_json:{amounts_dict}    {debug_str} ")
            payload = APICheckPayload(sender=sender, prices=prices_dict, amounts=amounts_dict)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_prices(self) -> Generator[None, None, tuple[list[float], list[int]]]:
        target_tokens = self.params.target_tokens
        assert len(target_tokens) == 3, "Invalid target tokens value, expecting 3 items."
        self.context.logger.info(f"get_prices {target_tokens}    {debug_str} ")
        t1, t2, t3 = target_tokens
        amount = 100 * 1000000
        results = yield from self._get_amounts_and_prices(t1[1], t2[1], t3[1], amount)
        self.context.logger.info(f"get_prices results {type(results)}, {results}    {debug_str} ")
        prices, amounts_out = results
        if not amounts_out or len(amounts_out) < 4 or not prices:
            return prices, amounts_out

        t0_amount, t2_amount, t3_amount, t1_amount = amounts_out
        p1, p2, p3 = prices
        return [p1, p2, p3], [amount, t2_amount, t3_amount, t1_amount]

    def _get_amounts_and_prices(self, tok1: str, tok2: str, tok3: str, amount: int):
        self.context.logger.info(f"get_amounts_and_prices    {debug_str} ")
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_id=str(UniswapV2Router02.contract_id),
            contract_callable="get_amounts_out",
            contract_address=self.params.uni_router_address,
            amount_in=amount,
            path=[tok1, tok2, tok3, tok1]
        )
        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"{debug_str} Getting the swap price failed: {response}"
            )
            return [], []

        amounts = response.state.body.get("amounts", None)
        if not amounts:
            self.context.logger.error(
                f"{debug_str} Getting amounts out failed: {response}"
            )
            return [], []

        for i, a in enumerate(amounts):
            if a <= 0:
                self.context.logger.error(
                    f"{debug_str} found zero amount for token {i+1}: {response}"
                )
                return [], []

        self.context.logger.info(f"{debug_str} Amounts out: {amounts}")
        p1 = float(amounts[0] / amount)
        p2 = float(amounts[1] / amounts[0])
        p3 = float(amounts[2] / amounts[1])
        return [p1, p2, p3], amounts


class DecisionMakingBehaviour(
    LearningBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """DecisionMakingBehaviour"""

    matching_round: Type[AbstractRound] = DecisionMakingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            event = self.get_event()
            payload = DecisionMakingPayload(sender=sender, event=event)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_event(self) -> str:
        """Get the next event"""
        amounts_str = self.synchronized_data.amounts
        print(f"amounts_json:{amounts_str}    {debug_str} ")
        amounts = []
        if amounts_str:
            amounts = [a for _, a in sorted(json.loads(amounts_str).items(), key=lambda x: x[0])]

        event = Event.DONE.value
        self.context.logger.info(f"DecisionMakingBehaviour get_event  amounts={amounts}    {debug_str} ")
        if len(amounts) == 4 and amounts[0] and amounts[-1] > amounts[0]:
            a0 = amounts[0] * 1e-18
            a1 = amounts[-1] * 1e-18
            ratio = a1 / a0
            self.context.logger.info(f"DecisionMakingBehaviour get_event  a0={a0}, a1={a1}, ratio={ratio}    {debug_str} ")
            if ratio > 1.05:
                event = Event.TRANSACT.value

        self.context.logger.info(f"Event is {event}")
        return str(event)


class TxPreparationBehaviour(
    LearningBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """TxPreparationBehaviour"""

    matching_round: Type[AbstractRound] = TxPreparationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            tx_hash = yield from self.get_tx_hash()
            payload = TxPreparationPayload(
                sender=sender, tx_submitter=None, tx_hash=tx_hash
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_tx_hash(self) -> Generator[None, None, str]:
        """Get the tx hash"""
        # We need to prepare a 1 wei transfer from the safe to another (configurable) account.

        data = bytes.fromhex("")
        safe_tx_hash = yield from self._get_safe_tx_hash(data)
        if safe_tx_hash is None:
            return "{}"

        # return tx_hash
        tx_hash = hash_payload_to_hex(
            safe_tx_hash=safe_tx_hash,
            ether_value=1000000000000000,  # send 1 WEI
            safe_tx_gas=SAFE_GAS,
            to_address="0x3d4374731BA30d1670493eC3c9bAd6A445bda348",
            data=data,
        )
        self.context.logger.info(f"Transaction hash is {tx_hash}")
        return tx_hash

    def _get_safe_tx_hash(self, data: bytes) -> Generator[None, None, Optional[str]]:
        """
        Prepares and returns the safe tx hash.

        This hash will be signed later by the agents, and submitted to the safe contract.
        Note that this is the transaction that the safe will execute, with the provided data.

        :param data: the safe tx data. This is the data of the function being called, in this case it's empty.
        :return: the tx hash
        """
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.synchronized_data.safe_contract_address,  # the safe contract address
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address="0x3d4374731BA30d1670493eC3c9bAd6A445bda348",  # the contract the safe will invoke
            value=1000000000000000,
            data=data,
            safe_tx_gas=SAFE_GAS,
        )
        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"get safe hash failed: {response.performative.value}"
            )
            return None

        tx_hash = cast(str, response.state.body["tx_hash"])[2:]
        return tx_hash


class LearningRoundBehaviour(AbstractRoundBehaviour):
    """LearningRoundBehaviour"""

    initial_behaviour_cls = APICheckBehaviour
    abci_app_cls = LearningAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        APICheckBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour,
    ]

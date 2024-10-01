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
import time
from abc import ABC
from typing import Generator, Set, Type, cast, Optional,List

from packages.valory.contracts.erc20.contract import ERC20
from packages.valory.contracts.gnosis_safe.contract import (
    GnosisSafeContract,
    SafeOperation,
)
from packages.valory.contracts.uniswapv2pair.contract import UniswapV2Pair
from packages.valory.contracts.uniswapv2router02.contract import UniswapV2Router02
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from hexbytes import HexBytes

from packages.valory.contracts.multisend.contract import (
    MultiSendContract,
    MultiSendOperation,
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
tx_debug_str = "+"*50
token_config = {
    "usdc": {
        "decimals": 6
    },
    "wxrp": {
        "decimals": 18
    },
    "weth": {
        "decimals": 18
    }
}

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
        amount = 10 * 1000000000000000000
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
        amounts = self.synchronized_data.amounts
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
        event = Event.TRANSACT.value
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

            target_tokens = self.params.target_tokens
            assert len(target_tokens) == 3, "Invalid target tokens value, expecting 3 items."
            t1, t2, t3 = target_tokens
            token_addresses = [t1[1], t2[1], t3[1]]
            amounts = self.synchronized_data.amounts
            if not amounts or len(amounts) != 4:
                raise AssertionError(f"invalid `amounts` value {amounts}, expecting list with 4 values.")

            amount_in = amounts[0]
            amount_out_min = amounts[-1]

            txs = []

            # borrow token 1 using flash swap
            swap_tx = yield from self._build_flash_swap_tx(amount_in, self.params.flash_swap_pair)
            txs.append(swap_tx)
            # approve the router for token 1
            approve_tx = yield from self._build_approval_tx(token_addresses[0], amount_in)
            txs.append(approve_tx)
            # prepare the 3-way swap tx
            swaps_tx = yield from self._build_arbitrage_swap_tx(
                token_addresses[0], token_addresses[1], token_addresses[2], amount_in, amount_out_min
            )
            txs.append(swaps_tx)
            # transfer the borrowed tokens back to the pair
            pay_back_tx = yield from self._build_transfer_tx(token_addresses[0], amount_in, self.params.flash_swap_pair)
            txs.append(pay_back_tx)
            self.context.logger.info(f"have {len(txs)} transactions for Multisend {tx_debug_str}")
            multisend_data = yield from self._build_multisend_tx(txs)
            self.context.logger.info(f"multisend data: {multisend_data} {tx_debug_str}")
            safe_tx_hash = yield from self._get_safe_tx_hash(multisend_data)
            self.context.logger.info(f"safe tx hash: {safe_tx_hash} {tx_debug_str}")
            tx_hash = hash_payload_to_hex(
                safe_tx_hash=safe_tx_hash,
                ether_value=0,
                safe_tx_gas=SAFE_GAS,
                to_address=self.params.multisend_contract_address,
                data=bytes.fromhex(multisend_data),
                operation=SafeOperation.DELEGATE_CALL.value,  # type: ignore
            )

            self.context.logger.info(f"tx hash: {tx_hash} {tx_debug_str}")
            payload = TxPreparationPayload(
                sender=sender, tx_submitter=self.auto_behaviour_id(), tx_hash=tx_hash
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _build_approval_tx(self, token: str, amount: int) -> Generator[None, None, dict]:
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=token,
            contract_id=str(ERC20.contract_id),
            contract_callable="build_approval_tx",
            spender=self.params.uni_router_address,
            amount=amount,
        )
        approve_data = cast(bytes, contract_api_msg.raw_transaction.body["data"])
        return {
            "operation": MultiSendOperation.CALL,
            "to": token,
            "value": 0,
            "data": HexBytes(approve_data.hex()),
        }

    def _build_transfer_tx(self, token: str, amount: int, receiver: str) -> Generator[None, None, dict]:
        fee = int(amount * 3 / 1000)
        amount = amount + fee
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=token,
            contract_id=str(ERC20.contract_id),
            contract_callable="build_transfer_tx",
            receiver=receiver,
            amount=amount,
        )
        transfer_data = cast(bytes, contract_api_msg.raw_transaction.body["data"])
        return {
            "operation": MultiSendOperation.CALL,
            "to": token,
            "value": 0,
            "data": HexBytes(transfer_data.hex()),
        }

    def _build_flash_swap_tx(self, borrow_amount: int, pair_address: str) -> Generator[None, None, dict]:
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=pair_address,
            contract_id=str(UniswapV2Pair.contract_id),
            contract_callable="build_swap_transaction",
            amount0_out=0,
            amount1_out=borrow_amount,
            to_address=self.synchronized_data.safe_contract_address,
            data=bytes.fromhex("")
        )
        swap_data = cast(bytes, contract_api_msg.raw_transaction.body["data"])

        return {
            "operation": MultiSendOperation.CALL,
            "to": pair_address,
            "value": 0,
            "data": HexBytes(swap_data.hex()),
        }

    def _build_arbitrage_swap_tx(self, t1, t2, t3, amount_in, amount_out_min) -> Generator[None, None, dict]:
        deadline = int(time.time() + 60 * 2)  # 2 minutes
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=self.params.uni_router_address,
            contract_id=str(UniswapV2Router02.contract_id),
            contract_callable="build_swap_transaction",
            amount_in=amount_in,
            amount_out_min=amount_out_min,
            path=[t1, t2, t3, t1],
            to=self.synchronized_data.safe_contract_address,
            deadline=deadline,
        )
        swap_data = cast(bytes, contract_api_msg.raw_transaction.body["data"])

        return {
            "operation": MultiSendOperation.CALL,
            "to": self.params.uni_router_address,
            "value": 0,
            "data": HexBytes(swap_data.hex()),
        }

    def _build_multisend_tx(self, txs: List[dict]) -> Generator[None, None, str]:
        contract_api_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=self.params.multisend_contract_address,
            contract_id=str(MultiSendContract.contract_id),
            contract_callable="get_tx_data",
            multi_send_txs=txs,
        )

        return cast(str, contract_api_msg.raw_transaction.body["data"])[2:]

    def _get_safe_tx_hash(self, data: str) -> Generator[None, None, Optional[str]]:
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
            to_address=self.params.multisend_contract_address,  # the contract the safe will invoke
            value=0,
            data=data,
            operation=SafeOperation.DELEGATE_CALL.value,
            safe_tx_gas=SAFE_GAS,
        )
        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"get safe hash failed: {response.performative.value}, {response}"
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

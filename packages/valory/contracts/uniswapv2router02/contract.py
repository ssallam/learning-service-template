# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023-2024 Valory AG
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

"""This module contains the class to connect to an UniswapV2Router02 contract."""

from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea_ledger_ethereum import EthereumApi
from typing import Dict

PUBLIC_ID = PublicId.from_str("valory/uniswapv2router02:0.1.0")


class UniswapV2Router02(Contract):
    """
    A wrapper for interacting with the Uniswap V2 Router contract using AEA components.
    """

    contract_id = PUBLIC_ID

    @classmethod
    def get_amounts_out(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        amount_in: int,
        path: list
    ):
        """
        Call the getAmountsOut method of the Uniswap V2 Router contract.

        :param ledger_api: The AEA LedgerApi object (e.g., EthereumApi).
        :param contract_address: The router contract address on the target chain
        :param amount_in: The amount of input tokens.
        :param path: The swap path of token addresses.
        :return: dict with one key `amounts` and the value is the amounts of output tokens including the amount_in
        """
        contract_instance = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        _path = [ledger_api.api.to_checksum_address(a) for a in path]
        print(f"UniswapV2Router02.get_amounts_out: {contract_address}, {contract_instance}, {_path}")
        get_amounts_out = getattr(contract_instance.functions, "getAmountsOut")  # noqa
        return {"amounts": get_amounts_out(amount_in, _path).call()}

    @classmethod
    def build_swap_transaction(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        amount_in: int,
        amount_out_min: int,
        path: list,
        to: str,
        deadline: int,
    ) -> Dict[str, bytes]:
        """
        Build a swap transaction using the Uniswap V2 Router contract.

        :param ledger_api: The AEA LedgerApi object (e.g., EthereumApi).
        :param contract_address: The router contract address on the target chain
        :param amount_in: Amount of input tokens.
        :param amount_out_min: Minimum output tokens to receive.
        :param path: List of token addresses.
        :param to: Recipient address.
        :param deadline: Transaction deadline timestamp.
        :return: The transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        _path = [ledger_api.api.to_checksum_address(a) for a in path]
        data = contract_instance.encodeABI(
            "swapExactTokensForTokens",
            args=(
                amount_in,
                amount_out_min,
                _path,
                ledger_api.api.to_checksum_address(to),
                deadline
            )
        )
        return {"data": bytes.fromhex(data[2:])}

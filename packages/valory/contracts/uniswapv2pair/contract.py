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

"""This module contains the class to connect to an UniswapV2Pair contract."""

from aea.configurations.base import PublicId
from aea.crypto.base import LedgerApi
from aea.contracts.base import Contract
from aea_ledger_ethereum import EthereumApi
from typing import Dict

PUBLIC_ID = PublicId.from_str("valory/uniswapv2pair:0.1.0")


class UniswapV2Pair(Contract):
    """
    A wrapper for interacting with the Uniswap V2 Pair contract using AEA components.
    """

    contract_id = PUBLIC_ID

    @classmethod
    def get_reserves(cls, ledger_api: EthereumApi, contract_address: str):
        """Fetch reserves in this pair."""
        try:
            contract_instance = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
            get_reserves = getattr(contract_instance.functions, "getReserves")  # noqa
            reserves = get_reserves().call()
            return {
                "reserve0": reserves[0],
                "reserve1": reserves[1],
                "blockTimestampLast": reserves[2],
            }
        except Exception as e:
            print(f"Error fetching reserves: {e}")
            return None

    @classmethod
    def get_token0(cls, ledger_api: LedgerApi, contract_address: str) -> str:
        """Get the address of token0."""
        contract = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        return contract.functions.token0().call()

    @classmethod
    def get_token1(cls, ledger_api: LedgerApi, contract_address: str) -> str:
        """Get the address of token1."""
        contract = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        return contract.functions.token1().call()

    @classmethod
    def get_total_supply(cls, ledger_api: LedgerApi, contract_address: str) -> int:
        """Get the total supply of liquidity tokens."""
        contract = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        return contract.functions.totalSupply().call()

    @classmethod
    def get_symbol(cls, ledger_api: LedgerApi, contract_address: str) -> str:
        """Get the symbol of the liquidity token."""
        contract = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        return contract.functions.symbol().call()

    @classmethod
    def build_swap_transaction(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            amount0_out: int,
            amount1_out: int,
            to_address: str,
            data: bytes,
    ) -> Dict[str, bytes]:
        """
        Build a swap transaction on the UniswapV2Pair contract.

        :param ledger_api: The Ledger API (Ethereum).
        :param contract_address: The UniswapV2Pair contract address.
        :param amount0_out: The amount of token0 to swap out.
        :param amount1_out: The amount of token1 to swap out.
        :param to_address: The address that receives the tokens.
        :param data: The additional calldata (typically empty for standard swaps).
        :return: A transaction dictionary ready to be signed and sent.
        """
        contract = cls.get_instance(ledger_api, ledger_api.api.to_checksum_address(contract_address))
        data = contract.encodeABI(
            "swap",
            args=(
                amount0_out,
                amount1_out,
                to_address,
                data
            )
        )
        return {"data": bytes.fromhex(data[2:])}

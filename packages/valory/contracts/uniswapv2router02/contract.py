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

from web3 import Web3


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
            cls, ledger_api: EthereumApi,
            contract_address: str,
            amount_in: int,
            amount_out_min: int,
            path: list,
            to: str,
            deadline: int,
            gas_price: int,
            nonce: int
    ):
        """
        Build a swap transaction using the Uniswap V2 Router contract.

        :param ledger_api: The AEA LedgerApi object (e.g., EthereumApi).
        :param contract_address: The router contract address on the target chain
        :param amount_in: Amount of input tokens.
        :param amount_out_min: Minimum output tokens to receive.
        :param path: List of token addresses.
        :param to: Recipient address.
        :param deadline: Transaction deadline timestamp.
        :param gas_price: Gas price in gwei.
        :param nonce: Transaction nonce.
        :return: The transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        tx = contract_instance.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            path,
            to,
            deadline
        ).buildTransaction({
            'gas': 2000000,
            'gasPrice': Web3.toWei(gas_price, 'gwei'),
            'nonce': nonce,
        })
        return tx

    @classmethod
    def add_liquidity(
            cls,
            ledger_api: EthereumApi,
            contract_address: str,
            token_a: str,
            token_b: str,
            amount_a: int,
            amount_b: int,
            to: str,
            deadline: int,
            gas_price: int,
            nonce: int
    ):
        """
        Add liquidity to the Uniswap V2 pool.

        :param ledger_api: The AEA LedgerApi object (e.g., EthereumApi).
        :param contract_address: The router contract address on the target chain
        :param token_a: Address of token A.
        :param token_b: Address of token B.
        :param amount_a: Amount of token A.
        :param amount_b: Amount of token B.
        :param to: Recipient address.
        :param deadline: Transaction deadline timestamp.
        :param gas_price: Gas price in gwei.
        :param nonce: Transaction nonce.
        :return: The transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        tx = contract_instance.functions.addLiquidity(
            token_a,
            token_b,
            amount_a,
            amount_b,
            0,  # min amount of token A
            0,  # min amount of token B
            to,
            deadline
        ).buildTransaction({
            'gas': 2000000,
            'gasPrice': Web3.toWei(gas_price, 'gwei'),
            'nonce': nonce,
        })
        return tx

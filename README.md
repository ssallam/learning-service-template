## Learning Service

This service performs onchain triangular arbitrage strategy using UniswapV2 router

## System requirements

- Python `>=3.10`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Set Docker permissions so you can run containers as non-root user](https://docs.docker.com/engine/install/linux-postinstall/)


## What was done in this implementation
- Created 2 custom `contract` packages: `uniswapv2Pair` and `uniswapv2router02` to interact with UniswapV2 contracts
- Extended the `contract` ERC20 wrapper to add a transaction builder for the `transfer` method 
- Get a quote of the intended swaps to check for profitability
- Created several transactions for inclusion in a `multisend` transaction. The transactions are:
  - prepare a tx to approve erc20 allowance
  - prepare a multi-tokens swap using the router contract


## What was implemented from the final assignment
- Multisend trasactions
- Custom contract package
- Minting on ethereum fork

## enhancements
- keep track of profit/loss 
- use the token pair contracts directly to check prices and find arbitrage opportunities
- create a solidity contract to execute a single arbitrage trade to:
  - take advantage of the flash-swap/loan feature 
  - optimise the execution of the trade transactions
- target multiple DEX protocols to increase the chance of finding profit opportunities
- target centralised exchanges to exploit price differences between the DEX and CEX pairs



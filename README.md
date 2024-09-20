## Learning Service

A service to learn about [Olas](https://olas.network/) agents and [Open Autonomy](https://github.com/valory-xyz/open-autonomy).


## System requirements

- Python `>=3.10`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Set Docker permissions so you can run containers as non-root user](https://docs.docker.com/engine/install/linux-postinstall/)


## Run you own agent

### Get the code

1. Clone this repo:

    ```
    git clone git@github.com:valory-xyz/academy-learning-service-template.git
    ```

2. Create the virtual environment:

    ```
    cd academy-learning-service
    poetry shell
    poetry install
    ```

3. Sync packages:

    ```
    autonomy packages sync --update-packages
    ```

### Prepare the data

1. Prepare a `keys.json` file containing wallet address and the private key for each of the four agents.

    ```
    autonomy generate-key ethereum -n 4
    ```

2. Prepare a `ethereum_private_key.txt` file containing one of the private keys from `keys.json`. Ensure that there is no newline at the end.

3. Deploy a [Safe on Gnosis](https://app.safe.global/welcome) (it's free) and set your agent addresses as signers. Set the signature threshold to 3 out of 4.

4. Create a [Tenderly](https://tenderly.co/) account and from your dashboard create a fork of Gnosis chain (virtual testnet).

5. From Tenderly, fund your agents and Safe with a small amount of xDAI, i.e. $0.02 each.

6. Make a copy of the env file:

    ```
    cp sample.env .env
    ```

7. Fill in the required environment variables in .env. These variables are: `ALL_PARTICIPANTS`, `GNOSIS_LEDGER_RPC`, `COINGECKO_API_KEY` and `SAFE_CONTRACT_ADDRESS`. You will need to get a [Coingecko](https://www.coingecko.com/). Set `GNOSIS_LEDGER_RPC` to your Tenderly fork Admin RPC.

### Run a single agent

1. Verify that `ALL_PARTICIPANTS` in `.env` contains only 1 address.

2. Run the agent:

    ```
    bash run_agent.sh
    ```

### Run the service (4 agents)

1. Check that Docker is running:

    ```
    docker
    ```

2. Verify that `ALL_PARTICIPANTS` in `.env` contains 4 addresses.

3. Run the service:

    ```
    bash run_service.sh
    ```

4. Look at the service logs for one of the agents (on another terminal):

    ```
    docker logs -f learningservice_abci_0
    ```


## Note on updating skill/agent code
When making changes to any of the skills/agents under development, make sure to update 
the versions in the packages.json file under `dev` (and other references) and run 
      autonomy packages lock
      autonomy push-all
(The first one updates the IPFS hash of each package, the second command uploads the packages to IPFS)
  also don't forget to update the version in the skill __init__ file


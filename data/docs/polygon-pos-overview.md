# Polygon PoS Overview

## What is Polygon PoS?

Polygon PoS (Proof of Stake) is a scalable, EVM-compatible chain secured by a decentralized validator set. It delivers fast, low-cost transactions and periodically commits state to Ethereum for finality. The current production stack is **Heimdall v2** (consensus) + **Bor** (execution) — see [`0xPolygon/heimdall-v2`](https://github.com/0xPolygon/heimdall-v2) and [`0xPolygon/bor`](https://github.com/0xPolygon/bor) for the authoritative source.

The reference toolkit for spinning up PoS devnets end-to-end (L1 + Bor + Heimdall-v2 + bridge + optional observability) is **`kurtosis-pos`** at [github.com/0xPolygon/kurtosis-pos](https://github.com/0xPolygon/kurtosis-pos). It tracks the current client versions, genesis, and contract deployment — always prefer it over older Ansible or raw Docker recipes when setting up a test network.

## Architecture

Polygon PoS uses a three-layer architecture:

1. **Staking contracts on Ethereum** — validator registration, POL staking, slashing, and reward accounting live on L1.
2. **Heimdall v2 (Consensus Layer)** — CometBFT/Cosmos-SDK-based PoS consensus engine; selects block producers, aggregates checkpoints, and submits them to Ethereum. Heimdall v1 is legacy; new deployments use v2.
3. **Bor (Execution Layer)** — geth-derived EVM client that produces blocks driven by Heimdall's span selection.

## Key Features

- **EVM Compatibility** — Ethereum smart contracts, tooling (Hardhat/Foundry/ethers/viem), and wallets work unchanged.
- **Fast Block Times** — ~2 second blocks.
- **Low Gas Fees** — typically fractions of a cent.
- **Checkpointing** — periodic Merkle commitments to Ethereum for L1-verifiable state.
- **Large Validator Set** — 100+ validators.
- **POL Token** — native gas + staking asset (migrated 1:1 from MATIC).

## Consensus Mechanism

### Block Production (Bor)

- Validators are elected as block producers in **spans** (groups of blocks).
- Producers create blocks and gossip them to the network.
- Block time is ~2 seconds.

### Checkpointing (Heimdall v2)

- Heimdall validators periodically submit checkpoints to Ethereum.
- Each checkpoint contains a Merkle root of all Bor blocks since the previous checkpoint.
- Checkpoint cadence is approximately 30 minutes and finalizes L2 state on L1.

## Network Specifications

| Specification | Value |
|---|---|
| Chain ID | 137 (Mainnet), 80002 (Amoy Testnet) |
| Block Time | ~2 seconds |
| Gas Token | POL (formerly MATIC) |
| Consensus | Heimdall v2 (CometBFT) + Bor (EVM) |
| Validators | 100+ |
| Finality | ~2 min L2 finality; Ethereum finality via checkpoints (~30 min) |

## Running a Polygon PoS Node

### Production / mainnet

- Operator docs: [docs.polygon.technology/pos/](https://docs.polygon.technology/pos/)
- Bor source + releases: [`0xPolygon/bor`](https://github.com/0xPolygon/bor/releases)
- Heimdall v2 source + releases: [`0xPolygon/heimdall-v2`](https://github.com/0xPolygon/heimdall-v2/releases)
- Archive node: pass `--gcmode=archive` to Bor; expect multi-TB storage.

### Local devnet (recommended for testing / investigation)

Use `kurtosis-pos`:

```bash
# Prereqs: Kurtosis CLI + Docker
kurtosis install    # if needed

# Spin up a default PoS devnet
kurtosis run github.com/0xPolygon/kurtosis-pos

# Pass custom params via an args file
kurtosis run github.com/0xPolygon/kurtosis-pos --args-file params.yaml

# Tear down
kurtosis clean
```

Deployed components include an L1 chain, PoS contract deployment, multiple validators (Bor + Heimdall-v2), RPC endpoints, and optional Prometheus/Grafana/Panoptichain/Blockscout observability plus a transaction spammer for load testing. Consult the [kurtosis-pos configuration overview](https://github.com/0xPolygon/kurtosis-pos/blob/main/docs/docs/configuration/overview.md) for the current parameter schema (including Heimdall v1 vs v2 selection and mainnet-fork vs fresh-genesis modes).

> `kurtosis-pos` is for **development and testing only** — not production.

## Staking and Validators

### Becoming a Validator

1. Run a full node (Heimdall v2 + Bor) synced to mainnet.
2. Stake POL on the L1 staking contract.
3. Validator slot auction determines the active set; minimum stake for the auction is published on-chain — see the staking dashboard / current docs for the live threshold.
4. Validators earn rewards from block production and checkpoint submission; delegators earn a share of validator rewards.

### Delegating

- Token holders delegate POL to a validator through the Polygon staking portal.
- Delegators share in validator rewards (minus commission).

## Bridging

Polygon PoS has a native bridge for transferring assets between Ethereum and Polygon:

- **PoS Bridge** — ERC-20 / ERC-721 / ERC-1155.
- **Deposit** — lock on L1, receive wrapped on L2 (~7–8 min).
- **Withdraw** — burn on L2, claim on L1 after checkpoint (~30 min to 3 h depending on checkpoint cadence).

See `bridging.md` for the full flow and the `AggLayer` integration path.

## POL Token

- POL is the native gas + staking token on Polygon PoS.
- Used for gas fees, validator staking, and governance.

### MATIC to POL migration

POL replaced MATIC as the native Polygon token in a 1:1 upgrade (the MATIC to POL migration). The MATIC to POL migration is handled automatically by most exchanges and wallets; see the [POL migration docs](https://polygon.technology/pol-token) for edge cases and the timeline for the MATIC to POL transition.

### Liquid staking (sPOL)

Liquid staking is available via **sPOL** — Polygon's native liquid staking token (launched 2026-04-14). Stakers deposit POL on Ethereum and receive sPOL, a composable ERC-20 whose POL-redemption rate grows as rewards accrue. See `staked-pol.md` and [`0xPolygon/sPOL-contracts`](https://github.com/0xPolygon/sPOL-contracts).

## References

- `bor` (execution client): https://github.com/0xPolygon/bor
- `heimdall-v2` (consensus): https://github.com/0xPolygon/heimdall-v2
- `kurtosis-pos` (devnet toolkit, authoritative for current topology): https://github.com/0xPolygon/kurtosis-pos
- `sPOL-contracts` (liquid staking): https://github.com/0xPolygon/sPOL-contracts
- Official Polygon PoS docs: https://docs.polygon.technology/pos/

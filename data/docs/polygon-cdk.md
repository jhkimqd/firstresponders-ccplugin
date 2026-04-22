# Polygon CDK (Chain Development Kit)

## Overview

Polygon CDK is an open-source toolkit for building and launching ZK-powered Layer 2 chains on Ethereum. It lets anyone deploy a sovereign, customizable L2 that uses zero-knowledge proofs for validity and connects to the **AggLayer** for cross-chain interoperability.

The canonical way to stand up a CDK devnet end-to-end — L1, L2, prover, AggLayer, and bridge — is the **`kurtosis-cdk`** package at [github.com/0xPolygon/kurtosis-cdk](https://github.com/0xPolygon/kurtosis-cdk). It is the most up-to-date reference for supported components, parameter names, and tested configurations; prefer it over any older Docker Compose recipes.

## Key Features

- **ZK-Powered Security** — zero-knowledge proofs establish validity of L2 state transitions.
- **Customizable** — gas token, data availability mode, execution client, fork ID.
- **Sovereign** — chain operators keep full control.
- **AggLayer Compatible** — unified bridge and cross-chain messaging via `zkEVM bridge service` + `agglayer` contracts.
- **EVM-Compatible** — standard Ethereum tooling (Hardhat/Foundry/ethers/viem) works unchanged.

## Architecture

A CDK chain deployed via `kurtosis-cdk` includes the following components (see the [`kurtosis-cdk` README](https://github.com/0xPolygon/kurtosis-cdk#readme) for the authoritative list):

### Core Components

1. **L1 blockchain** — local Ethereum client (multi-client supported) that holds settlement and rollup contracts.
2. **Sequencer / L2 execution client** — current default stack is Optimism-based (`op-reth` + `op-node`) with **AggKit** integration; the legacy `cdk-erigon` path is also supported.
3. **Aggregator / Prover** — generates ZK proofs for L2 batches.
4. **AggLayer service + contracts** — enables trustless cross-chain token transfers and message passing, secured by ZK proofs.
5. **zkEVM bridge service** — L1↔L2 bridge backing the AggLayer.
6. **Optional observability** — Prometheus, Grafana, Panoptichain, Blockscout (toggled via args).

### Data Availability Options

- **Rollup** — full L2 data posted to Ethereum (calldata / blobs).
- **Validium** — data attested by a Data Availability Committee (DAC).
- **External DA** — Avail, Celestia, etc. (check the current `kurtosis-cdk` args schema for supported adapters).

## Deploying a CDK Devnet

The supported path is **Kurtosis**. Raw `docker compose` instructions found in older guides are out of date — always consult `kurtosis-cdk` first.

### Prerequisites

- [Kurtosis CLI](https://docs.kurtosis.com/install) installed and running.
- Docker (Kurtosis runs enclaves as Docker containers).
- Enough disk/RAM for the selected stack (L1 + L2 + prover is heavy).

### Quick Start

```bash
# Spin up a default CDK devnet in an enclave named "cdk"
kurtosis run --enclave cdk github.com/0xPolygon/kurtosis-cdk

# Export the L2 RPC for convenience
export ETH_RPC_URL=$(kurtosis port print cdk op-el-1-op-reth-op-node-001 rpc)

# Tear it down
kurtosis enclave rm --force cdk
```

### Custom Parameters

Create a `params.yml` and pass it with `--args-file`:

```bash
kurtosis run --enclave cdk --args-file params.yml github.com/0xPolygon/kurtosis-cdk
```

Inline args work too, but **do not combine an args file with inline args** — Kurtosis does not merge them, it uses only the inline set:

```bash
kurtosis run --enclave cdk github.com/0xPolygon/kurtosis-cdk '{"args": {"verbosity": "debug"}}'
```

Working example `params.yml` files live under [`.github/tests/`](https://github.com/0xPolygon/kurtosis-cdk/tree/main/.github/tests) in the `kurtosis-cdk` repo — use those as your starting template, since they track the current schema (consensus type, DA mode, gas-token address, fork ID, etc.).

## CDK vs PoS

| Feature | Polygon PoS | Polygon CDK |
|---|---|---|
| Consensus | PoS (Heimdall v2 + Bor) | ZK validity proofs |
| Settlement | Ethereum (checkpoints) | Ethereum (ZK proofs) |
| Finality | ~2 min (≈30 min to Ethereum) | Depends on proof cadence |
| Customization | Limited | Gas token, DA, fork ID, execution client |
| Interoperability | Polygon Bridge / AggLayer | AggLayer (native) |
| Use case | General-purpose L2 | Application-specific L2 |

## Use Cases

- **DeFi chains** — custom gas token, high throughput.
- **Gaming chains** — low latency, gasless UX.
- **Enterprise chains** — permissioned with data-availability controls.
- **Social dApps** — high TPS for interaction-heavy workloads.

## References

- `kurtosis-cdk` (authoritative, up-to-date): https://github.com/0xPolygon/kurtosis-cdk
- Getting started: https://github.com/0xPolygon/kurtosis-cdk/blob/main/docs/docs/introduction/getting-started.md
- Configuration overview: https://github.com/0xPolygon/kurtosis-cdk/blob/main/docs/docs/configuration/overview.md
- Example args files: https://github.com/0xPolygon/kurtosis-cdk/tree/main/.github/tests
- Official Polygon docs: https://docs.polygon.technology/

# Polygon PoS Overview

## What is Polygon PoS?

Polygon PoS (Proof of Stake) is a commit chain — a scalable EVM-compatible sidechain secured by a decentralized set of validators who use the PoS consensus mechanism. It provides fast and low-cost transactions while leveraging Ethereum for security through periodic checkpoints.

## Architecture

Polygon PoS uses a three-layer architecture:

1. **Staking contracts on Ethereum** — Validator management and staking on Ethereum mainnet
2. **Heimdall (Consensus Layer)** — A Tendermint-based PoS consensus engine that selects block producers, validates and commits checkpoints to Ethereum
3. **Bor (Block Production Layer)** — A modified Geth client that produces blocks on the Polygon chain

## Key Features

- **EVM Compatibility**: Full compatibility with Ethereum smart contracts, tools, and wallets
- **Fast Block Times**: ~2 second block times
- **Low Gas Fees**: Gas fees are typically fractions of a cent
- **Checkpointing**: Periodic checkpoints to Ethereum for security
- **Large Validator Set**: 100+ validators securing the network
- **POL Token**: Used for staking, gas fees, and governance (formerly MATIC)

## Consensus Mechanism

### Block Production (Bor)

- Validators are selected as block producers in spans (groups of blocks)
- Block producers create blocks and broadcast them to the network
- Block time is approximately 2 seconds

### Checkpointing (Heimdall)

- Heimdall validators periodically submit checkpoints to Ethereum
- Checkpoints contain a Merkle root hash of all blocks since the last checkpoint
- This ensures that Polygon's state can be verified on Ethereum
- Checkpoint interval is approximately 30 minutes

## Network Specifications

| Specification | Value |
|--------------|-------|
| Chain ID | 137 (Mainnet), 80002 (Amoy Testnet) |
| Block Time | ~2 seconds |
| Gas Token | POL (formerly MATIC) |
| Consensus | PoS (Tendermint + Bor) |
| Validators | 100+ |
| TPS | Up to ~65 transactions per second |
| Finality | ~2 minutes (256 blocks), Ethereum finality via checkpoints |

## Running a Polygon PoS Node

### Full Node

A full node syncs and validates all blocks:

```bash
# Using Ansible (recommended)
git clone https://github.com/maticnetwork/node-ansible
cd node-ansible
# Follow the setup guide for your environment
```

### Archive Node

An archive node stores the complete state history:

- Requires more storage (several TB)
- Needed for historical queries and debugging
- Use `--gcmode archive` flag when running Bor

## Staking and Validators

### Becoming a Validator

1. Set up a full node (Heimdall + Bor)
2. Stake POL tokens on the staking contract on Ethereum
3. Minimum stake: 1 POL (but more is recommended for selection)
4. Validators earn rewards from block production and checkpoint submission

### Delegating

- Token holders can delegate their POL to validators
- Delegators earn a share of the validator's rewards
- Delegation is done through the Polygon staking portal

## Bridging

Polygon PoS has a native bridge for transferring assets between Ethereum and Polygon:

- **PoS Bridge**: For most tokens (ERC-20, ERC-721, ERC-1155)
- **Deposit**: Lock tokens on Ethereum, receive wrapped tokens on Polygon (~7-8 minutes)
- **Withdraw**: Burn tokens on Polygon, claim on Ethereum after checkpoint (~30 min to 3 hours)

## POL Token Migration

MATIC has been upgraded to POL as the native gas and staking token:

- POL is a 1:1 upgrade from MATIC
- POL is used for gas fees on Polygon PoS
- POL is used for staking and governance
- The migration is handled automatically on most exchanges and wallets

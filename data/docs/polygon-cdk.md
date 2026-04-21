# Polygon CDK (Chain Development Kit)

## Overview

Polygon CDK is an open-source toolkit for building and launching ZK-powered Layer 2 chains on Ethereum. It enables anyone to deploy their own sovereign, customizable L2 chain that uses zero-knowledge proofs for security and can connect to the AggLayer for interoperability.

## Key Features

- **ZK-Powered Security**: Uses zero-knowledge proofs to ensure transaction validity
- **Customizable**: Configure gas token, data availability, execution environment, and more
- **Sovereign**: Chain operators maintain full control over their chain
- **AggLayer Compatible**: Connect to the AggLayer for cross-chain interoperability
- **EVM-Compatible**: Full support for Ethereum smart contracts and tooling

## Architecture

A Polygon CDK chain consists of several components:

### Core Components

1. **Sequencer**: Orders and batches transactions
2. **Aggregator**: Generates ZK proofs for batches
3. **Synchronizer**: Keeps state in sync across components
4. **JSON-RPC Node**: Provides the EVM-compatible RPC interface
5. **Prover**: Generates zero-knowledge proofs (SP1 or custom)

### Data Availability Options

- **On-chain (Ethereum)**: Full data posted to Ethereum calldata/blobs (rollup mode)
- **DAC (Data Availability Committee)**: Data attested by a committee (validium mode)
- **Avail / Celestia**: Third-party DA layers

## Deploying a CDK Chain

### Prerequisites

- Docker and Docker Compose
- Ethereum RPC endpoint (for L1 settlement)
- Sufficient ETH for L1 transactions

### Quick Start

```bash
# Clone the CDK repository
git clone https://github.com/0xPolygon/cdk
cd cdk

# Configure your chain
cp .env.example .env
# Edit .env with your settings

# Launch the chain
docker compose up -d
```

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `CHAIN_ID` | Your L2 chain ID | — |
| `GAS_TOKEN` | Native gas token address | ETH |
| `DATA_AVAILABILITY` | `rollup` or `validium` | `rollup` |
| `SEQUENCER_TYPE` | `centralized` or `shared` | `centralized` |
| `PROOF_SYSTEM` | ZK proof system to use | `SP1` |

## CDK vs PoS

| Feature | Polygon PoS | Polygon CDK |
|---------|-------------|-------------|
| Consensus | PoS (Tendermint + Bor) | ZK Proofs |
| Settlement | Ethereum (checkpoints) | Ethereum (ZK proofs) |
| Finality | ~2 min (30 min to Ethereum) | Configurable (proof generation time) |
| Customization | Limited | Full (gas token, DA, etc.) |
| Interoperability | Polygon Bridge | AggLayer |
| Use Case | General-purpose L2 | Application-specific L2 |

## Use Cases

- **DeFi Chains**: Custom gas token, high throughput for trading
- **Gaming Chains**: Low latency, gasless transactions
- **Enterprise Chains**: Permissioned with data privacy
- **Social dApps**: High throughput for social interactions

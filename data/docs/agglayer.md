# AggLayer (Aggregation Layer)

## Overview

The AggLayer is Polygon's interoperability protocol that unifies liquidity and state across all connected chains. It aggregates ZK proofs from multiple chains and settles them on Ethereum in a single proof, enabling seamless cross-chain interaction.

## How It Works

1. **Connected chains** (CDK chains, Polygon PoS, etc.) submit their ZK proofs to the AggLayer
2. The AggLayer **aggregates** these proofs into a single unified proof
3. The aggregated proof is **verified on Ethereum** in a single transaction
4. This creates a **shared security model** where all connected chains benefit from Ethereum's security

## Key Benefits

- **Unified Liquidity**: Assets can move between connected chains without traditional bridges
- **Shared Security**: All chains settle on Ethereum through aggregated proofs
- **Near-Instant Cross-Chain Transfers**: No need to wait for bridge confirmations
- **Capital Efficiency**: Liquidity is not fragmented across chains
- **Low Cost**: Proof aggregation reduces per-chain settlement costs on Ethereum

## Architecture

### Components

- **Unified Bridge**: A single bridge contract on Ethereum for all connected chains
- **Pessimistic Proof**: Safety mechanism that ensures no chain can create tokens out of thin air
- **Proof Aggregator**: Combines individual chain proofs into one
- **Certificate Manager**: Manages cross-chain state transitions

### Cross-Chain Flow

```
Chain A → Bridge Tx → AggLayer Certificate → Proof Aggregation → Ethereum Settlement
                                ↓
Chain B ← Bridge Claim ← Verified State
```

## Connecting to the AggLayer

CDK chains can connect to the AggLayer to enable cross-chain interoperability:

1. Deploy your CDK chain with AggLayer configuration
2. Register your chain with the AggLayer
3. Cross-chain transactions are automatically routed through the unified bridge

## Security Model

- **Pessimistic Proof**: Ensures that the total value locked across all chains never exceeds what was deposited
- **ZK Proofs**: Each chain's state transition is proven with zero-knowledge proofs
- **Ethereum Settlement**: Final settlement on Ethereum provides the ultimate security guarantee
- **No Single Point of Failure**: Decentralized proof aggregation

# AggLayer (Aggregation Layer)

> **Authoritative source.** The current AggLayer implementation lives at [`agglayer/agglayer`](https://github.com/agglayer/agglayer). The former `0xPolygon/agglayer` repo is **archived** (last push 2024-08) and should not be used as a reference. For bridging clients, see [`0xPolygon/lxly.js`](https://github.com/0xPolygon/lxly.js) (TypeScript SDK for the unified bridge). For the bridge backend, [`0xPolygon/zkevm-bridge-service`](https://github.com/0xPolygon/zkevm-bridge-service) serves Merkle proofs and deposit claim data.

## Overview

AggLayer is Polygon's interoperability protocol that unifies liquidity and state across all connected chains. It aggregates validity proofs from multiple chains and settles them on Ethereum, enabling near-seamless cross-chain interaction with a single shared security model.

## How the AggLayer bridge differs from the Polygon PoS bridge

The AggLayer bridge and the PoS bridge are two different bridge systems with different trust models, settlement paths, and chain coverage. The AggLayer bridge is Polygon's next-generation unified bridge; the PoS bridge is the original Polygon PoS ↔ Ethereum bridge.

| Dimension | PoS bridge | AggLayer bridge |
|---|---|---|
| Chains covered | Polygon PoS ↔ Ethereum only | Any AggLayer-connected chain (CDK chains and PoS as it integrates) |
| Settlement model | Checkpoint-based (Heimdall submits a Merkle checkpoint of PoS blocks to Ethereum; exits finalize after checkpoint inclusion) | Validity-proof-based (each chain submits ZK proofs + certificates; the AggLayer aggregates them and settles on Ethereum in one proof) |
| Withdrawal latency | ~30 minutes to ~3 hours (checkpoint cadence + L1 exit claim) | Fast: once a chain's certificate settles on L1, claims on other AggLayer chains are near-instant |
| Security primitive | PoS validator set signing checkpoints | ZK validity proofs + **pessimistic proof** (no chain can over-withdraw more than it has deposited, even if its prover misbehaves) |
| Liquidity | Isolated per token bridge contract | Unified — one bridge backs every connected chain, so liquidity is not fragmented |
| Typical SDK | `@maticnetwork/maticjs` (see `0xPolygon/matic.js`) | `lxly.js` (see `0xPolygon/lxly.js`) |

Rule of thumb: **use the PoS bridge** for legacy Polygon PoS ↔ Ethereum ERC-20/721/1155 transfers where an existing token binding already exists on the PoS bridge; **use the AggLayer bridge** for anything cross-CDK-chain, anything new, or anywhere you want the faster validity-proof settlement path.

## How It Works

1. **Connected chains** (CDK chains, and PoS as it integrates) submit **certificates** describing their state transitions to the AggLayer.
2. The AggLayer verifies each certificate and **aggregates** proofs into a single settlement.
3. The aggregated proof is **verified on Ethereum** in a single L1 transaction.
4. Result: a **shared security model** where all connected chains inherit Ethereum's settlement guarantees and can exchange messages + assets via the **unified bridge**.

## Key Benefits

- **Unified liquidity** — assets move between connected chains via the unified bridge without per-pair bridge deployments.
- **Shared security** — all chains settle on Ethereum through aggregated proofs.
- **Near-instant cross-chain transfers** — once a chain's certificate is settled, cross-chain claims are fast.
- **Capital efficiency** — no fragmented liquidity pools per chain pair.
- **Low cost** — proof aggregation amortizes the L1 verification cost across all connected chains.

## Architecture

### Components

- **Unified Bridge** — a single bridge contract set on Ethereum that backs every connected chain.
- **Pessimistic Proof** — a safety mechanism ensuring no chain can withdraw more tokens than it has verifiably deposited, even if its prover is buggy or malicious. The pessimistic proof checks per-chain accounting independently of the zk-execution proofs.
- **Proof Aggregator** — combines individual chain proofs into a single settlement proof posted to L1.
- **Certificate Manager** — manages per-chain state-transition certificates and their submission to AggLayer.
- **AggKit** — operator tooling that integrates chains with the AggLayer (referenced in `kurtosis-cdk` deployments).

### Cross-Chain Flow

```
Chain A → Bridge Tx → AggLayer Certificate → Proof Aggregation → Ethereum Settlement
                                                                       ↓
Chain B ← Bridge Claim ← Merkle Proof via bridge service ← Verified State
```

## Connecting to the AggLayer

A CDK chain connects to AggLayer by:

1. Deploying with AggLayer-aware configuration (see [`kurtosis-cdk`](https://github.com/0xPolygon/kurtosis-cdk) for an end-to-end local reference that stands up the AggLayer services, bridge contracts, and a CDK L2 together).
2. Registering the chain with AggLayer (its prover, rollup manager entry, etc.).
3. Routing bridge transactions through the unified bridge; cross-chain claims become available on other connected chains once the relevant certificate is settled on L1.

For client-side integration (wallets, dApps, bridging UIs), use [`lxly.js`](https://github.com/0xPolygon/lxly.js). See `bridging.md` for end-user flows.

## Security Model

- **Pessimistic proof** — bounds per-chain outgoing value by verified deposits; the core defense against a single chain's zk-stack compromising global solvency.
- **ZK validity proofs** — each connected chain proves its own state transitions.
- **Ethereum settlement** — final settlement on L1 provides the ultimate security guarantee.
- **No single point of failure** — proof aggregation does not require a trusted coordinator for safety (liveness assumptions are separate and documented in `agglayer/agglayer`).

## References

- AggLayer implementation (current, active): https://github.com/agglayer/agglayer
- AggLayer overview in the Polygon docs: https://docs.polygon.technology/agglayer/
- Unified bridge SDK: https://github.com/0xPolygon/lxly.js
- Bridge service backend: https://github.com/0xPolygon/zkevm-bridge-service
- Local AggLayer + CDK devnet: https://github.com/0xPolygon/kurtosis-cdk

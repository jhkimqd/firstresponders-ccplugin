# Bridging Between Ethereum and Polygon

> **Authoritative sources.** Legacy PoS bridge SDK: [`0xPolygon/matic.js`](https://github.com/0xPolygon/matic.js). AggLayer / unified bridge SDK (cross-chain, CDK-aware): [`0xPolygon/lxly.js`](https://github.com/0xPolygon/lxly.js). Bridge service (backend for AggLayer-connected chains): [`0xPolygon/zkevm-bridge-service`](https://github.com/0xPolygon/zkevm-bridge-service). AggLayer itself: [`agglayer/agglayer`](https://github.com/agglayer/agglayer) — note the former `0xPolygon/agglayer` repo is **archived**. Older references to `maticnetwork/maticjs-ethers` and `maticnetwork/pos-portal` are stale and should not be used.

## Overview

There are two bridging families depending on what you're moving and between which chains:

1. **PoS Bridge** — the classic Polygon PoS ↔ Ethereum bridge. Use for ERC-20 / ERC-721 / ERC-1155 movement between L1 Ethereum and Polygon PoS. Current SDK: `0xPolygon/matic.js`.
2. **AggLayer Unified Bridge** — cross-chain messaging + liquidity across AggLayer-connected chains (CDK chains + PoS as they integrate). Current SDK: `0xPolygon/lxly.js` (pronounced "LxLy"). Preferred for anything CDK-facing or multi-chain.

## PoS Bridge

### Deposit (Ethereum → Polygon PoS)

- Lock tokens on L1, mirrored/minted on Polygon.
- Takes ~7–8 minutes end-to-end.

### Withdraw (Polygon PoS → Ethereum)

- Burn on Polygon, then claim on Ethereum **after checkpoint inclusion**.
- End-to-end ~30 min to ~3 h depending on checkpoint cadence and L1 gas.

### Programmatic use with `matic.js`

```javascript
// Use matic.js from the current 0xPolygon/matic.js repo.
// Install: npm i @maticnetwork/maticjs @maticnetwork/maticjs-ethers ethers
const { POSClient, use } = require("@maticnetwork/maticjs");
const { Web3ClientPlugin } = require("@maticnetwork/maticjs-ethers");

use(Web3ClientPlugin);

const posClient = new POSClient();
await posClient.init({
  network: "mainnet",
  version: "v1",
  parent: { provider: ethereumProvider, defaultConfig: { from: userAddress } },
  child:  { provider: polygonProvider,  defaultConfig: { from: userAddress } },
});

// Deposit ERC-20
const erc20 = posClient.erc20(tokenAddress, /* isParent */ true);
await (await erc20.approve(amount)).getReceipt();
const dep = await erc20.deposit(amount, userAddress);
const depReceipt = await dep.getReceipt();
// Arrives on PoS ~7–8 min later
```

### Withdraw (two-step)

```javascript
const erc20Child = posClient.erc20(tokenAddress);           // on Polygon
const burn = await erc20Child.withdrawStart(amount);
const burnReceipt = await burn.getReceipt();

// Wait for checkpoint (~30 min cadence)
const ready = await posClient.isCheckPointed(burnReceipt.transactionHash);
if (ready) {
  const exit = await erc20Child.withdrawExit(burnReceipt.transactionHash);
  await exit.getReceipt();
}
```

Always check the current [`0xPolygon/matic.js`](https://github.com/0xPolygon/matic.js) README — the package names, `version` values, and plugin patterns get bumped with each release.

## AggLayer Unified Bridge (`lxly.js`)

For chains connected to AggLayer (Polygon CDK chains and, over time, PoS), bridging uses the unified bridge + ZK-proof-backed settlement instead of checkpointed PoS exits. `lxly.js` is the current TypeScript client:

```javascript
// npm i @0xpolygon/lxly-client (or consult the current README for the package name)
// See https://github.com/0xPolygon/lxly.js for install + API, which evolves rapidly.
```

Typical use cases:
- Bridging between two CDK chains via the unified bridge.
- Claiming tokens or messages across AggLayer-connected chains.
- Building dApps that abstract "which chain am I on" away from the user.

Backends: [`0xPolygon/zkevm-bridge-service`](https://github.com/0xPolygon/zkevm-bridge-service) exposes the REST/gRPC endpoints that indexers and wallets query for Merkle proofs and deposit claim data.

## End-user UIs

- **Polygon Portal** — https://portal.polygon.technology — official bridge UI for PoS + AggLayer.
- **Third-party bridges** — Hop, Across, Stargate/LayerZero — useful for fast paths that bypass the native exit-delay, with their own security assumptions.

## Bridging Native POL / MATIC

1. Use the Polygon Portal at https://portal.polygon.technology.
2. Connect your wallet.
3. Select amount and direction.
4. Approve + confirm.

POL has replaced MATIC 1:1 as the native staking/gas asset on PoS; most wallets and exchanges handle the migration automatically.

## Bridge Security

- **PoS bridge** — secured by the PoS validator set; withdrawals finalize after Ethereum checkpoint inclusion.
- **AggLayer unified bridge** — secured by ZK validity proofs plus the **pessimistic proof** safety property (no chain can over-withdraw more than it has deposited, even if its prover misbehaves). See `agglayer.md` and [`agglayer/agglayer`](https://github.com/agglayer/agglayer) for internals.

## Common Issues

### Deposit not showing on Polygon
- Wait ≥ 7–8 minutes; check the L1 transaction on Etherscan.
- Track status in Polygon Portal.

### Withdrawal stuck
- Withdrawals require a checkpoint on L1 (~30 min cadence) before the exit claim becomes submittable.
- After checkpoint, submit the exit transaction on L1 (pays L1 gas).
- Monitor checkpoint inclusion in Polygon Portal.

### Gas fees
- Deposits: L1 ETH gas.
- Withdrawals: POL (burn on PoS) + ETH (exit claim on L1). During L1 congestion the exit claim can dominate cost.

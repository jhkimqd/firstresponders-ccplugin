# Running Polygon PoS Nodes and Validators

> **Authoritative sources.** Node software: [`0xPolygon/bor`](https://github.com/0xPolygon/bor) (execution) and [`0xPolygon/heimdall-v2`](https://github.com/0xPolygon/heimdall-v2) (consensus). For local devnets use [`0xPolygon/kurtosis-pos`](https://github.com/0xPolygon/kurtosis-pos). For mainnet operator workflows, the [`0xPolygon/matic-cli`](https://github.com/0xPolygon/matic-cli) tool and the official docs at [docs.polygon.technology/pos/](https://docs.polygon.technology/pos/) are the up-to-date references. Older setups referencing `maticnetwork/node-ansible`, `maticnetwork/polygon-edge`, `maticnetwork/heimdall` (v1), or generic `maticnetwork/*` Docker images are **deprecated** — `polygon-edge` in particular has been removed.

## Node Types

### Full Node

A full node syncs and validates all Polygon PoS blocks:

- Stores current state and recent block history.
- Provides RPC endpoints for querying the chain.
- Required for validators and recommended for dApp developers who want their own endpoint.

### Archive Node

Stores the complete historical state:

- Required for historical queries (`eth_getBalance` at old blocks, trace APIs over history).
- Requires significantly more storage (multi-TB and growing).
- Run Bor with `--gcmode=archive`.

### Sentry Node

A sentry node acts as a gateway between a validator and the public network:

- Protects validators from DDoS.
- Validators should never expose their nodes directly to the public internet — put sentries in front.
- Multiple sentries can front a single validator; pair with firewalling and a separate internal network.

## Hardware Requirements

### Full Node

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 8 cores | 16 cores |
| RAM | 16 GB | 32 GB |
| Storage | 2 TB NVMe SSD | 4 TB NVMe SSD |
| Network | 100 Mbps | 1 Gbps |

### Archive Node

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 16 cores | 32 cores |
| RAM | 32 GB | 64 GB |
| Storage | 8 TB NVMe SSD | 16+ TB NVMe SSD |
| Network | 1 Gbps | 1 Gbps |

Numbers grow over time — cross-check the latest guidance in `0xPolygon/bor` and `0xPolygon/heimdall-v2` release notes before sizing hardware.

## Setting Up a Node

### Option A — Local devnet for testing (recommended for development)

Use `kurtosis-pos`. It stands up a complete L1 + Bor + Heimdall-v2 + bridge stack end-to-end:

```bash
# Prereqs: Kurtosis CLI + Docker
kurtosis install
kurtosis run github.com/0xPolygon/kurtosis-pos

# Custom parameters (Heimdall v1 vs v2, validator count, fork mode, observability, etc.)
kurtosis run github.com/0xPolygon/kurtosis-pos --args-file params.yaml

# Tear down
kurtosis clean
```

See [kurtosis-pos configuration overview](https://github.com/0xPolygon/kurtosis-pos/blob/main/docs/docs/configuration/overview.md) for the current argument schema.

### Option B — Mainnet / production node

Consult the **current operator docs** at https://docs.polygon.technology/pos/ and the release notes in each component repo. High-level shape:

1. Install Bor from [`0xPolygon/bor` releases](https://github.com/0xPolygon/bor/releases).
2. Install Heimdall v2 from [`0xPolygon/heimdall-v2` releases](https://github.com/0xPolygon/heimdall-v2/releases).
3. Configure genesis + seed peers per the docs (values change with upgrades — don't hardcode from older guides).
4. Start Heimdall v2 first, wait for sync, then start Bor.
5. Monitor sync to tip before serving RPC or participating in consensus.

The [`0xPolygon/matic-cli`](https://github.com/0xPolygon/matic-cli) tool wraps common operator tasks (node bootstrap, snapshot handling, validator setup) and tracks current releases.

## Becoming a Validator

### Prerequisites

- A full node (Heimdall v2 + Bor) fully synced to tip.
- A sentry node in front of your validator.
- POL tokens for staking on Ethereum L1.
- ETH for Ethereum gas fees (staking, checkpoint submissions).

### Steps

1. **Stand up full node + sentry** (see above).
2. **Generate validator keys** on the Heimdall node.
3. **Stake POL** via the Polygon staking portal or directly on the L1 staking contract — see [`0xPolygon/pos-contracts`](https://github.com/0xPolygon/pos-contracts) for the contract source.
4. **Register** your Heimdall public key.
5. **Wait for activation** — block production starts in the next span after inclusion.

### Staking Contracts

Live on Ethereum L1:
- `StakeManager` — validator registration, staking/unstaking, slashing accounting.
- Validator commission rates are set on-chain.
- Current minimum stake and the active-set auction mechanics are published on-chain and in the staking portal — always read the live values rather than a stale doc, since parameters change via governance.

## Monitoring Your Node

### Heimdall v2

```bash
# Check status (CometBFT RPC)
curl http://localhost:26657/status

# Latest block height
curl -s http://localhost:26657/status | jq '.result.sync_info.latest_block_height'
```

### Bor

```bash
# Sync status
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}'

# Latest block number
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

For richer observability, compose with [`0xPolygon/panoptichain`](https://github.com/0xPolygon/panoptichain) or plug node metrics into Prometheus + Grafana (both ship as optional services in `kurtosis-pos`).

## Common Node Issues

### Node Not Syncing
- Check peers: `curl localhost:26657/net_info` (Heimdall) / `admin_peers` via Bor IPC.
- Ensure P2P ports are reachable: 26656 (Heimdall), 30303 (Bor).
- Use a recent snapshot for the initial sync — consult the Bor and Heimdall-v2 release notes for current snapshot providers.

### High Memory / Disk Pressure
- Tune Bor cache (`--cache`, `--cache.database`, `--cache.trie`) in line with hardware.
- Use pruning modes appropriate to the node role (full vs archive).
- Watch `heimdalld` and `bor` logs for state-growth warnings after upgrades.

### Checkpoint Failures (Validators)
- Heimdall v2 must be fully synced.
- Keep ETH balance topped up for checkpoint submission gas.
- Monitor Heimdall logs for checkpoint-builder errors and inclusion failures.

## Deprecated / removed tooling (do not use)

- `maticnetwork/polygon-edge` — **repository removed.** It's the defunct "Edge" framework; no relation to current PoS.
- `maticnetwork/node-ansible` — unmaintained; prefer `matic-cli` or the current docs.
- `maticnetwork/heimdall` (v1) — **archived.** v1 consensus is being sunset in favor of Heimdall v2.
- `maticnetwork/bor` — legacy org path; canonical is `0xPolygon/bor`.
- `maticnetwork/maticjs-ethers` — stale since 2024; no current replacement needed (`0xPolygon/matic.js` bundles what you need).

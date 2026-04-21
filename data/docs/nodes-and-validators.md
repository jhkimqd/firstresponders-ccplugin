# Running Polygon PoS Nodes and Validators

## Node Types

### Full Node

A full node syncs and validates all Polygon PoS blocks:

- Stores current state and recent block history
- Provides RPC endpoints for querying the chain
- Required for validators and recommended for dApp developers

### Archive Node

An archive node stores the complete historical state:

- Required for historical queries (e.g., `eth_getBalance` at old blocks)
- Requires significantly more storage (several TB)
- Use `--gcmode archive` flag

### Sentry Node

A sentry node acts as a gateway between a validator and the public network:

- Protects validators from DDoS attacks
- Validators should never expose their nodes directly to the internet
- Multiple sentry nodes can front a single validator

## Hardware Requirements

### Full Node

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 8 cores | 16 cores |
| RAM | 16 GB | 32 GB |
| Storage | 2 TB SSD | 4 TB NVMe SSD |
| Network | 100 Mbps | 1 Gbps |

### Archive Node

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 16 cores | 32 cores |
| RAM | 32 GB | 64 GB |
| Storage | 8 TB NVMe SSD | 16 TB NVMe SSD |
| Network | 1 Gbps | 1 Gbps |

## Setting Up a Full Node

### Using Ansible (Recommended)

```bash
# Clone the node-ansible repository
git clone https://github.com/maticnetwork/node-ansible
cd node-ansible

# Install dependencies
pip install ansible

# Configure the node
# Edit inventory, group_vars, and host_vars as needed

# Run the playbook
ansible-playbook -i inventory playbooks/setup.yml
```

### Using Docker

```bash
# Clone and configure
git clone https://github.com/maticnetwork/polygon-edge
cd polygon-edge

# Start Heimdall
docker run -d --name heimdall \
  -p 26656:26656 -p 26657:26657 \
  -v heimdall-data:/root/.heimdalld \
  maticnetwork/heimdall:latest start

# Start Bor
docker run -d --name bor \
  -p 8545:8545 -p 30303:30303 \
  -v bor-data:/root/.bor \
  maticnetwork/bor:latest server
```

### Manual Installation

1. Install Go 1.21+ and build tools
2. Clone and build Heimdall from source
3. Clone and build Bor from source
4. Configure genesis files and seeds
5. Start Heimdall, wait for sync, then start Bor

## Becoming a Validator

### Prerequisites

- A full node (Heimdall + Bor) fully synced
- A sentry node for network security
- POL tokens for staking (on Ethereum mainnet)
- ETH for Ethereum gas fees

### Steps

1. **Set up your full node and sentry node**
2. **Generate validator keys** on your Heimdall node
3. **Stake POL tokens** through the Polygon staking portal or directly on the staking smart contract on Ethereum
4. **Register as a validator** by submitting your Heimdall public key
5. **Wait for activation** — you'll start producing blocks in the next span

### Staking Contract

The staking contract is on Ethereum mainnet:
- Staking Manager: Manages validator registration and staking
- Validators can set a commission rate for delegators
- Minimum stake: 1 POL (but competitive staking requires significantly more)

## Monitoring Your Node

### Heimdall

```bash
# Check sync status
curl http://localhost:26657/status

# Check current block height
curl http://localhost:26657/status | jq '.result.sync_info.latest_block_height'
```

### Bor

```bash
# Check sync status
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}'

# Get latest block number
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

## Common Node Issues

### Node Not Syncing
- Check if peers are connected: `curl localhost:26657/net_info`
- Ensure ports 26656 (Heimdall) and 30303 (Bor) are open
- Use snapshots for faster initial sync

### High Memory Usage
- Adjust cache settings in Bor configuration
- Consider using pruning modes
- Monitor with tools like Prometheus + Grafana

### Checkpoint Failures (Validators)
- Ensure Heimdall is fully synced
- Check ETH balance for checkpoint transactions
- Monitor Heimdall logs for errors

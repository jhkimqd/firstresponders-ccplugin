# Polygon RPC Endpoints

## Public RPC Endpoints

### Polygon PoS Mainnet

| Provider | URL | Rate Limit |
|----------|-----|-----------|
| Polygon | https://polygon-rpc.com | Moderate |
| Ankr | https://rpc.ankr.com/polygon | Moderate |
| 1RPC | https://1rpc.io/matic | Moderate |

### Polygon Amoy Testnet

| Provider | URL |
|----------|-----|
| Polygon | https://rpc-amoy.polygon.technology |
| Alchemy | https://polygon-amoy.g.alchemy.com/v2/YOUR_KEY |

## Private RPC Providers

For production dApps, use a private RPC provider:

| Provider | Features |
|----------|----------|
| Alchemy | Webhooks, enhanced APIs, archive data |
| Infura | Reliable, MetaMask integration |
| QuickNode | Low latency, global endpoints |
| Chainstack | Dedicated nodes, elastic APIs |
| Moralis | Web3 APIs beyond just RPC |

## Configuring RPC in Your dApp

### MetaMask

Add Polygon PoS manually:
- Network Name: Polygon PoS
- RPC URL: https://polygon-rpc.com
- Chain ID: 137
- Currency Symbol: POL
- Block Explorer: https://polygonscan.com

### ethers.js

```javascript
const { ethers } = require("ethers");

// Public RPC
const provider = new ethers.JsonRpcProvider("https://polygon-rpc.com");

// Private RPC (Alchemy)
const provider = new ethers.JsonRpcProvider(
  "https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY"
);

// Get latest block
const block = await provider.getBlockNumber();
console.log("Latest block:", block);
```

### web3.js

```javascript
const Web3 = require("web3");
const web3 = new Web3("https://polygon-rpc.com");

const blockNumber = await web3.eth.getBlockNumber();
console.log("Latest block:", blockNumber);
```

### viem

```javascript
import { createPublicClient, http } from "viem";
import { polygon } from "viem/chains";

const client = createPublicClient({
  chain: polygon,
  transport: http("https://polygon-rpc.com"),
});

const blockNumber = await client.getBlockNumber();
```

## Common RPC Methods

| Method | Description |
|--------|-------------|
| `eth_blockNumber` | Get latest block number |
| `eth_getBalance` | Get POL balance of an address |
| `eth_getTransactionByHash` | Get transaction details |
| `eth_getTransactionReceipt` | Get transaction receipt |
| `eth_call` | Execute a read-only contract call |
| `eth_sendRawTransaction` | Submit a signed transaction |
| `eth_gasPrice` | Get current gas price |
| `eth_estimateGas` | Estimate gas for a transaction |
| `eth_getLogs` | Get event logs matching a filter |

## WebSocket Endpoints

For real-time event subscriptions:

```javascript
// WebSocket connection for real-time events
const provider = new ethers.WebSocketProvider("wss://polygon-bor-rpc.publicnode.com");

provider.on("block", (blockNumber) => {
  console.log("New block:", blockNumber);
});
```

## Rate Limiting and Best Practices

- **Use private RPC providers** for production — public endpoints have rate limits
- **Implement retry logic** with exponential backoff
- **Cache frequently-requested data** (e.g., block number, gas price)
- **Use batch requests** to reduce the number of HTTP calls
- **Use WebSocket** for real-time data instead of polling
